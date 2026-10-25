import os
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select, func
from sqlalchemy.engine import make_url
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.main import app
from app.Database.database import get_db
from app.dependencies.current_user import get_current_user
from app.models.user import User, generate_friend_code
from app.models.friend_request import FriendRequest


@pytest.fixture
def pg_context():
    raw_url = os.getenv("FRIENDSMEETING_TEST_DATABASE_URL")

    if not raw_url:
        pytest.skip("Banco de integracao nao configurado")

    url = make_url(raw_url)

    # Protecao contra execucao no banco principal.
    assert url.get_backend_name() == "postgresql"
    assert url.host in ("localhost", "127.0.0.1")
    assert url.port == 5433
    assert url.database == "friendsmeeting_test"

    engine = create_engine(raw_url, pool_pre_ping=True)

    with engine.connect() as connection:
        outer_transaction = connection.begin()

        db = Session(
            bind=connection,
            join_transaction_mode="create_savepoint",
            expire_on_commit=False,
        )

        try:
            alice = User(
                username="alice_teste",
                email="alice_integracao@example.com",
                auth_user_id=None,
                password_hash=None,
                friend_code=generate_friend_code(),
            )

            bob = User(
                username="bob_teste",
                email="bob_integracao@example.com",
                auth_user_id=None,
                password_hash=None,
                friend_code=generate_friend_code(),
            )

            db.add_all([alice, bob])
            db.flush()

            def override_db():
                yield db

            def act_as(user):
                app.dependency_overrides[
                    get_current_user
                ] = lambda: user

            app.dependency_overrides[get_db] = override_db
            act_as(alice)

            with TestClient(app) as client:
                yield client, db, alice, bob, act_as

        finally:
            app.dependency_overrides.clear()
            db.close()
            outer_transaction.rollback()

    engine.dispose()


def test_request_is_persisted(pg_context):
    client, db, alice, bob, act_as = pg_context

    response = client.post(
        "/api/v1/friends/requests",
        json={"friend_code": bob.friend_code},
    )

    assert response.status_code == 201

    request_id = UUID(response.json()["id"])

    saved = db.get(FriendRequest, request_id)

    assert saved is not None
    assert saved.sender_id == alice.id
    assert saved.receiver_id == bob.id
    assert saved.status == "pending"

    act_as(bob)

    received = client.get("/api/v1/friends/requests")

    assert received.status_code == 200
    assert len(received.json()) == 1
    assert received.json()[0]["id"] == str(request_id)


def test_reverse_duplicate_is_rejected(pg_context):
    client, db, alice, bob, act_as = pg_context

    first = client.post(
        "/api/v1/friends/requests",
        json={"friend_code": bob.friend_code},
    )

    assert first.status_code == 201

    act_as(bob)

    duplicate = client.post(
        "/api/v1/friends/requests",
        json={"friend_code": alice.friend_code},
    )

    assert duplicate.status_code == 409

    total = db.scalar(
        select(func.count()).select_from(FriendRequest)
    )

    assert total == 1


def test_acceptance_lists_both_friends(pg_context):
    client, db, alice, bob, act_as = pg_context

    created = client.post(
        "/api/v1/friends/requests",
        json={"friend_code": bob.friend_code},
    )

    assert created.status_code == 201

    request_id = created.json()["id"]

    act_as(bob)

    accepted = client.patch(
        f"/api/v1/friends/requests/{request_id}",
        json={"action": "accept"},
    )

    assert accepted.status_code == 200
    assert accepted.json()["status"] == "accepted"

    saved = db.get(FriendRequest, UUID(request_id))
    assert saved.status == "accepted"
    assert saved.responded_at is not None

    bob_friends = client.get("/api/v1/friends")

    assert bob_friends.status_code == 200
    assert bob_friends.json()[0]["username"] == "alice_teste"

    act_as(alice)

    alice_friends = client.get("/api/v1/friends")

    assert alice_friends.status_code == 200
    assert alice_friends.json()[0]["username"] == "bob_teste"


def test_rejected_request_can_be_resent(pg_context):
    client, db, alice, bob, act_as = pg_context

    created = client.post(
        "/api/v1/friends/requests",
        json={"friend_code": bob.friend_code},
    )

    assert created.status_code == 201
    request_id = created.json()["id"]

    act_as(bob)

    rejected = client.patch(
        f"/api/v1/friends/requests/{request_id}",
        json={"action": "reject"},
    )

    assert rejected.status_code == 200
    assert rejected.json()["status"] == "rejected"

    assert client.get("/api/v1/friends").json() == []

    act_as(alice)

    resent = client.post(
        "/api/v1/friends/requests",
        json={"friend_code": bob.friend_code},
    )

    assert resent.status_code == 201
    assert resent.json()["id"] == request_id
    assert resent.json()["status"] == "pending"


def test_database_blocks_self_friendship(pg_context):
    client, db, alice, bob, act_as = pg_context

    invalid = FriendRequest(
        sender_id=alice.id,
        receiver_id=alice.id,
        status="pending",
    )

    db.add(invalid)

    with pytest.raises(IntegrityError):
        db.flush()

    db.rollback()


def test_database_blocks_reverse_pair(pg_context):
    client, db, alice, bob, act_as = pg_context

    first = FriendRequest(
        sender_id=alice.id,
        receiver_id=bob.id,
        status="pending",
    )

    db.add(first)
    db.flush()

    reverse = FriendRequest(
        sender_id=bob.id,
        receiver_id=alice.id,
        status="pending",
    )

    db.add(reverse)

    with pytest.raises(IntegrityError):
        db.flush()

    db.rollback()
