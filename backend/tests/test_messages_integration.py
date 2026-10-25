
import os
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.engine import make_url
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.main import app
from app.Database.database import get_db
from app.dependencies.current_user import get_current_user
from app.models.user import User, generate_friend_code
from app.models.friend_request import FriendRequest
from app.models.message import Message


@pytest.fixture
def pg_chat():
    raw_url = os.getenv("FRIENDSMEETING_TEST_DATABASE_URL")

    if not raw_url:
        pytest.fail("Defina FRIENDSMEETING_TEST_DATABASE_URL")

    url = make_url(raw_url)

    # Protecao: somente o banco local de testes.
    assert url.get_backend_name() == "postgresql"
    assert url.host in ("127.0.0.1", "localhost")
    assert url.port == 5433
    assert url.database == "friendsmeeting_test"
    assert url.username == "test"

    engine = create_engine(raw_url, pool_pre_ping=True)

    try:
        with engine.connect() as connection:
            transaction = connection.begin()

            db = Session(
                bind=connection,
                join_transaction_mode="create_savepoint",
                expire_on_commit=False,
            )

            try:
                suffix = uuid4().hex[:8]

                def make_user(name):
                    return User(
                        username=f"{name}_{suffix}",
                        email=f"{name}_{suffix}@example.test",
                        friend_code=generate_friend_code(),
                    )

                alice = make_user("alice")
                bob = make_user("bob")
                charlie = make_user("charlie")

                db.add_all([alice, bob, charlie])
                db.flush()

                # Alice e Bob ja sao amigos.
                friendship = FriendRequest(
                    sender_id=alice.id,
                    receiver_id=bob.id,
                    status="accepted",
                )

                db.add(friendship)
                db.flush()

                def act_as(user):
                    def current_user_override():
                        return user

                    app.dependency_overrides[
                        get_current_user
                    ] = current_user_override

                app.dependency_overrides[get_db] = lambda: db
                act_as(alice)

                with TestClient(app) as client:
                    yield client, db, alice, bob, charlie, act_as

            finally:
                app.dependency_overrides.clear()
                db.close()
                transaction.rollback()

    finally:
        engine.dispose()


def create_chat(client, friend):
    response = client.post(
        "/api/v1/conversations",
        json={"friend_id": str(friend.id)},
    )

    assert response.status_code == 201, response.text
    return response.json()["id"]


def send(client, conversation_id, body):
    return client.post(
        f"/api/v1/conversations/{conversation_id}/messages",
        json={"body": body},
    )


def history(client, conversation_id, **params):
    return client.get(
        f"/api/v1/conversations/{conversation_id}/messages",
        params=params,
    )


def message_count(db):
    return db.scalar(
        select(func.count()).select_from(Message)
    )


def test_pg_two_users_exchange_messages(pg_chat):
    client, db, alice, bob, charlie, act_as = pg_chat

    conversation_id = create_chat(client, bob)

    first = send(client, conversation_id, "Ola, Bob!")
    assert first.status_code == 201, first.text
    assert first.json()["sender_id"] == str(alice.id)

    act_as(bob)

    second = send(client, conversation_id, "Ola, Alice!")
    assert second.status_code == 201, second.text
    assert second.json()["sender_id"] == str(bob.id)

    # Consulta persistencia real no PostgreSQL.
    db.expire_all()

    saved = db.get(Message, UUID(first.json()["id"]))
    assert saved is not None
    assert saved.body == "Ola, Bob!"

    response = history(client, conversation_id)

    assert response.status_code == 200
    assert len(response.json()) == 2

    bodies = {item["body"] for item in response.json()}
    assert bodies == {"Ola, Bob!", "Ola, Alice!"}

    act_as(alice)
    assert len(history(client, conversation_id).json()) == 2
    assert message_count(db) == 2


def test_pg_outsider_cannot_access(pg_chat):
    client, db, alice, bob, charlie, act_as = pg_chat

    conversation_id = create_chat(client, bob)
    assert send(client, conversation_id, "Privado").status_code == 201

    act_as(charlie)

    details = client.get(
        f"/api/v1/conversations/{conversation_id}"
    )
    received = history(client, conversation_id)
    attempt = send(client, conversation_id, "Espionagem")

    assert details.status_code == 404
    assert received.status_code == 404
    assert attempt.status_code == 404

    assert message_count(db) == 1


def test_pg_reverse_conversation_is_reused(pg_chat):
    client, db, alice, bob, charlie, act_as = pg_chat

    conversation_id = create_chat(client, bob)

    act_as(bob)

    response = client.post(
        "/api/v1/conversations",
        json={"friend_id": str(alice.id)},
    )

    assert response.status_code == 200
    assert response.json()["id"] == conversation_id


def test_pg_history_pagination(pg_chat):
    client, db, alice, bob, charlie, act_as = pg_chat

    conversation_id = create_chat(client, bob)

    for i in range(5):
        result = send(client, conversation_id, f"Mensagem {i}")
        assert result.status_code == 201

    all_messages = history(client, conversation_id)
    first_page = history(
        client, conversation_id, limit=3, offset=0
    )
    second_page = history(
        client, conversation_id, limit=3, offset=3
    )

    assert all_messages.status_code == 200
    assert first_page.status_code == 200
    assert second_page.status_code == 200

    all_ids = [m["id"] for m in all_messages.json()]
    page1_ids = [m["id"] for m in first_page.json()]
    page2_ids = [m["id"] for m in second_page.json()]

    assert len(all_ids) == 5
    assert page1_ids == all_ids[:3]
    assert page2_ids == all_ids[3:]
    assert not set(page1_ids).intersection(page2_ids)


def test_pg_invalid_messages_are_rejected(pg_chat):
    client, db, alice, bob, charlie, act_as = pg_chat

    conversation_id = create_chat(client, bob)

    for body in ("", "   ", "A" * 2001):
        response = send(client, conversation_id, body)
        assert response.status_code == 422

    invalid_page = history(
        client, conversation_id, limit=101
    )

    assert invalid_page.status_code == 422
    assert message_count(db) == 0


def test_pg_database_rejects_blank_message(pg_chat):
    client, db, alice, bob, charlie, act_as = pg_chat

    conversation_id = create_chat(client, bob)

    invalid = Message(
        conversation_id=UUID(conversation_id),
        sender_id=alice.id,
        body="   ",
    )

    # Savepoint: a falha nao compromete a transacao externa.
    with pytest.raises(IntegrityError):
        with db.begin_nested():
            db.add(invalid)
            db.flush()

    assert message_count(db) == 0
