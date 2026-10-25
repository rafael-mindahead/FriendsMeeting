
from datetime import datetime, timezone
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.main import app
from app.Database.database import get_db
from app.dependencies.current_user import get_current_user
from app.models.user import User
from app.models.conversation import Conversation
from app.models.message import Message


@pytest.fixture
def context():
    user = User(
        id=uuid4(),
        username="rafa",
        email="rafa@example.com",
        friend_code="FM-QWERTY23",
    )

    db = MagicMock(spec=Session)

    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: user

    try:
        with TestClient(app) as client:
            yield client, db, user
    finally:
        app.dependency_overrides.clear()


def make_conversation(user_id, friend_id):
    return Conversation(
        id=uuid4(),
        user_a_id=user_id,
        user_b_id=friend_id,
        created_at=datetime.now(timezone.utc),
    )


def make_message(conversation_id, sender_id):
    return Message(
        id=uuid4(),
        conversation_id=conversation_id,
        sender_id=sender_id,
        body="Ola, amigo!",
        created_at=datetime.now(timezone.utc),
    )


def test_get_conversation(context):
    client, db, user = context
    conversation = make_conversation(user.id, uuid4())
    db.get.return_value = conversation

    response = client.get(
        f"/api/v1/conversations/{conversation.id}"
    )

    assert response.status_code == 200
    assert response.json()["id"] == str(conversation.id)


def test_send_message(context):
    client, db, user = context
    conversation = make_conversation(user.id, uuid4())
    db.get.return_value = conversation

    def simulate_refresh(obj):
        obj.id = uuid4()
        obj.created_at = datetime.now(timezone.utc)

    db.refresh.side_effect = simulate_refresh

    response = client.post(
        f"/api/v1/conversations/{conversation.id}/messages",
        json={"body": "Ola, amigo!"},
    )

    assert response.status_code == 201
    assert response.json()["body"] == "Ola, amigo!"
    assert response.json()["sender_id"] == str(user.id)
    db.add.assert_called_once()
    db.commit.assert_called_once()


def test_list_messages_with_pagination(context):
    client, db, user = context
    conversation = make_conversation(user.id, uuid4())
    message = make_message(conversation.id, user.id)

    db.get.return_value = conversation
    db.scalars.return_value.all.return_value = [message]

    response = client.get(
        f"/api/v1/conversations/{conversation.id}/messages",
        params={"limit": 5, "offset": 10},
    )

    assert response.status_code == 200
    assert len(response.json()) == 1

    query = db.scalars.call_args.args[0]
    sql = str(
        query.compile(
            compile_kwargs={"literal_binds": True}
        )
    ).lower()

    assert "limit 5" in sql
    assert "offset 10" in sql


def test_conversation_not_found(context):
    client, db, user = context
    db.get.return_value = None

    response = client.get(
        f"/api/v1/conversations/{uuid4()}"
    )

    assert response.status_code == 404


def test_third_party_cannot_access_messages(context):
    client, db, user = context

    conversation = make_conversation(
        uuid4(), uuid4()
    )
    db.get.return_value = conversation

    base = f"/api/v1/conversations/{conversation.id}"

    details = client.get(base)
    history = client.get(f"{base}/messages")
    sending = client.post(
        f"{base}/messages",
        json={"body": "Tentativa indevida"},
    )

    assert details.status_code == 404
    assert history.status_code == 404
    assert sending.status_code == 404
    db.add.assert_not_called()


def test_blank_message_is_rejected(context):
    client, db, user = context
    conversation = make_conversation(user.id, uuid4())

    response = client.post(
        f"/api/v1/conversations/{conversation.id}/messages",
        json={"body": "   "},
    )

    assert response.status_code == 422
    db.commit.assert_not_called()


def test_message_limit_2000_characters(context):
    client, db, user = context
    conversation = make_conversation(user.id, uuid4())

    response = client.post(
        f"/api/v1/conversations/{conversation.id}/messages",
        json={"body": "A" * 2001},
    )

    assert response.status_code == 422
    db.commit.assert_not_called()


def test_invalid_pagination(context):
    client, db, user = context
    conversation = make_conversation(user.id, uuid4())

    response = client.get(
        f"/api/v1/conversations/{conversation.id}/messages",
        params={"limit": 101, "offset": -1},
    )

    assert response.status_code == 422


def test_messages_require_authentication(context):
    client, db, user = context

    app.dependency_overrides.pop(
        get_current_user, None
    )

    response = client.get(
        f"/api/v1/conversations/{uuid4()}/messages"
    )

    assert response.status_code == 401


def test_database_failure_rolls_back(context):
    client, db, user = context
    conversation = make_conversation(user.id, uuid4())

    db.get.return_value = conversation
    db.commit.side_effect = SQLAlchemyError("Falha simulada")

    response = client.post(
        f"/api/v1/conversations/{conversation.id}/messages",
        json={"body": "Teste de falha"},
    )

    assert response.status_code == 503
    db.rollback.assert_called_once()



@pytest.mark.parametrize("length", [1001, 2000])
def test_message_within_database_limit_is_accepted(context, length):
    client, db, user = context
    conversation = make_conversation(user.id, uuid4())
    db.get.return_value = conversation

    def simulate_refresh(obj):
        obj.id = uuid4()
        obj.created_at = datetime.now(timezone.utc)

    db.refresh.side_effect = simulate_refresh

    response = client.post(
        f"/api/v1/conversations/{conversation.id}/messages",
        json={"body": "A" * length},
    )

    assert response.status_code == 201, response.text
    assert len(response.json()["body"]) == length
    db.commit.assert_called_once()
