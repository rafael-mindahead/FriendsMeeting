
from datetime import datetime, timezone
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.Database.database import get_db
from app.dependencies.current_user import get_current_user
from app.models.conversation import Conversation
from app.models.user import User


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


def make_conversation(user_a, user_b):
    return Conversation(
        id=uuid4(),
        user_a_id=user_a,
        user_b_id=user_b,
        created_at=datetime.now(timezone.utc),
    )


def test_create_conversation(context):
    client, db, user = context
    friend_id = uuid4()

    # Amizade aceita e conversa ainda inexistente.
    db.scalar.side_effect = [uuid4(), None]

    def simulate_refresh(obj):
        obj.id = uuid4()
        obj.created_at = datetime.now(timezone.utc)

    db.refresh.side_effect = simulate_refresh

    response = client.post(
        "/api/v1/conversations",
        json={"friend_id": str(friend_id)},
    )

    assert response.status_code == 201
    assert response.json()["user_a_id"] == str(user.id)
    assert response.json()["user_b_id"] == str(friend_id)
    db.commit.assert_called_once()


def test_existing_conversation_is_reused(context):
    client, db, user = context
    friend_id = uuid4()

    existing = make_conversation(user.id, friend_id)

    db.scalar.side_effect = [uuid4(), existing]

    response = client.post(
        "/api/v1/conversations",
        json={"friend_id": str(friend_id)},
    )

    assert response.status_code == 200
    assert response.json()["id"] == str(existing.id)
    db.commit.assert_not_called()


def test_non_friend_cannot_start_conversation(context):
    client, db, user = context

    db.scalar.return_value = None

    response = client.post(
        "/api/v1/conversations",
        json={"friend_id": str(uuid4())},
    )

    assert response.status_code == 403
    db.commit.assert_not_called()


def test_cannot_start_conversation_with_self(context):
    client, db, user = context

    response = client.post(
        "/api/v1/conversations",
        json={"friend_id": str(user.id)},
    )

    assert response.status_code == 400
    db.scalar.assert_not_called()


def test_list_conversations(context):
    client, db, user = context

    conversation = make_conversation(
        user.id,
        uuid4(),
    )

    db.scalars.return_value.all.return_value = [
        conversation
    ]

    response = client.get("/api/v1/conversations")

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["id"] == str(conversation.id)


def test_invalid_friend_id(context):
    client, db, user = context

    response = client.post(
        "/api/v1/conversations",
        json={"friend_id": "invalido"},
    )

    assert response.status_code == 422
    db.commit.assert_not_called()


def test_conversations_require_auth(context):
    client, db, user = context

    app.dependency_overrides.pop(get_current_user, None)

    response = client.get("/api/v1/conversations")

    assert response.status_code == 401
