
from datetime import datetime, timezone
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.Database.database import get_db
from app.dependencies.current_user import get_current_user
from app.models.user import User
from app.models.friend_request import FriendRequest


@pytest.fixture
def context():
    me = User(
        id=uuid4(),
        username="rafa",
        email="rafa@example.com",
        friend_code="FM-QWERTY23",
    )

    db = MagicMock(spec=Session)

    def override_db():
        yield db

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = lambda: me

    try:
        with TestClient(app) as client:
            yield client, db, me
    finally:
        app.dependency_overrides.clear()


def make_request(sender, receiver, status="pending"):
    return FriendRequest(
        id=uuid4(),
        sender_id=sender,
        receiver_id=receiver,
        status=status,
        created_at=datetime.now(timezone.utc),
    )


def test_send_friend_request_returns_201(context):
    client, db, me = context

    receiver = User(
        id=uuid4(),
        username="amigo",
        email="amigo@example.com",
        friend_code="FM-ASDFGH23",
    )

    db.scalar.side_effect = [receiver, None]

    def simulate_refresh(obj):
        obj.id = uuid4()
        obj.status = "pending"
        obj.created_at = datetime.now(timezone.utc)

    db.refresh.side_effect = simulate_refresh

    response = client.post(
        "/api/v1/friends/requests",
        json={"friend_code": receiver.friend_code},
    )

    assert response.status_code == 201
    assert response.json()["status"] == "pending"
    db.commit.assert_called_once()


def test_duplicate_request_returns_409(context):
    client, db, me = context

    receiver = User(
        id=uuid4(),
        friend_code="FM-ASDFGH23",
    )

    existing = make_request(me.id, receiver.id)

    db.scalar.side_effect = [receiver, existing]

    response = client.post(
        "/api/v1/friends/requests",
        json={"friend_code": receiver.friend_code},
    )

    assert response.status_code == 409
    db.commit.assert_not_called()


def test_accept_friend_request(context):
    client, db, me = context

    request = make_request(uuid4(), me.id)
    db.scalar.return_value = request

    response = client.patch(
        f"/api/v1/friends/requests/{request.id}",
        json={"action": "accept"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "accepted"
    assert response.json()["responded_at"] is not None
    db.commit.assert_called_once()


def test_reject_friend_request(context):
    client, db, me = context

    request = make_request(uuid4(), me.id)
    db.scalar.return_value = request

    response = client.patch(
        f"/api/v1/friends/requests/{request.id}",
        json={"action": "reject"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "rejected"


def test_sender_cannot_accept_own_request(context):
    client, db, me = context

    request = make_request(me.id, uuid4())
    db.scalar.return_value = request

    response = client.patch(
        f"/api/v1/friends/requests/{request.id}",
        json={"action": "accept"},
    )

    assert response.status_code == 403
    db.commit.assert_not_called()


def test_accepted_request_cannot_be_accepted_twice(context):
    client, db, me = context

    request = make_request(
        uuid4(), me.id, status="accepted"
    )
    db.scalar.return_value = request

    response = client.patch(
        f"/api/v1/friends/requests/{request.id}",
        json={"action": "accept"},
    )

    assert response.status_code == 409


def test_received_requests(context):
    client, db, me = context

    request = make_request(uuid4(), me.id)
    db.scalars.return_value.all.return_value = [request]

    response = client.get("/api/v1/friends/requests")

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["status"] == "pending"
