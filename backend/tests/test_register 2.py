"""Contract tests for FriendsMeeting's authService integration (no external I/O)."""
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError

from app.main import app
from app.Database.database import get_db
from app.clients.auth_service import get_auth_service

PAYLOAD = {
    "username": "usuario_teste",
    "email": "teste@example.com",
    "password": "SenhaSegura2026!",
}
IDENTITY = {"id": 51, "name": "usuario_teste", "email": "teste@example.com"}


@pytest.fixture
def context():
    db = MagicMock()
    db.scalar.return_value = None

    def refresh(user):
        user.id = uuid4()
        user.created_at = datetime.now(timezone.utc)

    db.refresh.side_effect = refresh
    auth = MagicMock()
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_auth_service] = lambda: auth
    try:
        yield db, auth
    finally:
        app.dependency_overrides.clear()


def uniqueness_error(name: str):
    original = Exception("duplicate")
    original.diag = SimpleNamespace(constraint_name=name)
    return IntegrityError("INSERT INTO users", {}, original)


def test_registration_delegates_and_creates_local_profile(context):
    db, auth = context
    auth.call.return_value = IDENTITY
    with TestClient(app) as client:
        response = client.post("/api/v1/auth/register", json=PAYLOAD)

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["username"] == PAYLOAD["username"]
    assert body["friend_code"].startswith("FM-")
    assert len(body["friend_code"]) == 11
    assert "password_hash" not in body
    saved = db.add.call_args.args[0]
    assert saved.auth_user_id == 51
    assert saved.password_hash is None
    assert auth.call.call_args.args == ("POST", "/auth/register")
    assert auth.call.call_args.kwargs["payload"]["name"] == PAYLOAD["username"]


def test_registration_conflict_before_remote_call(context):
    db, auth = context
    db.scalar.return_value = uuid4()
    with TestClient(app) as client:
        response = client.post("/api/v1/auth/register", json=PAYLOAD)
    assert response.status_code == 409
    auth.call.assert_not_called()


def test_registration_remote_conflict(context):
    _, auth = context
    auth.call.side_effect = HTTPException(409, "email ja foi registrado")
    with TestClient(app) as client:
        response = client.post("/api/v1/auth/register", json=PAYLOAD)
    assert response.status_code == 409


@pytest.mark.parametrize(
    "field,value",
    [
        ("email", "invalido"),
        ("username", "ab"),
        ("username", "nome com espaco"),
        ("password", "abc"),
    ],
)
def test_registration_invalid_input(context, field, value):
    _, auth = context
    payload = dict(PAYLOAD)
    payload[field] = value
    with TestClient(app) as client:
        response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 422
    auth.call.assert_not_called()


def test_friend_code_collision_retries(context):
    db, auth = context
    auth.call.return_value = IDENTITY
    db.commit.side_effect = [uniqueness_error("ix_users_friend_code"), None]
    with TestClient(app) as client:
        response = client.post("/api/v1/auth/register", json=PAYLOAD)
    assert response.status_code == 201
    assert db.commit.call_count == 2
    db.rollback.assert_called_once()


def test_login_proxies_and_provisions_profile(context):
    db, auth = context
    auth.call.side_effect = [
        {"access_token": "token", "refresh_token": "refresh", "token_type": "bearer"},
        IDENTITY,
    ]
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/auth/login",
            json={"email": PAYLOAD["email"], "password": PAYLOAD["password"]},
        )
    assert response.status_code == 200
    assert response.json()["access_token"] == "token"
    assert auth.call.call_count == 2
    assert auth.call.call_args.kwargs["token"] == "token"
    assert db.add.called


def test_login_bad_credentials(context):
    _, auth = context
    auth.call.side_effect = HTTPException(401, "Credenciais invalidas")
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/auth/login",
            json={"email": PAYLOAD["email"], "password": "errada"},
        )
    assert response.status_code == 401


def test_my_profile_requires_bearer(context):
    with TestClient(app) as client:
        response = client.get("/api/v1/users/me")
    assert response.status_code == 401


def test_my_profile_uses_remote_identity(context):
    _, auth = context
    auth.call.return_value = IDENTITY
    with TestClient(app) as client:
        response = client.get(
            "/api/v1/users/me", headers={"Authorization": "Bearer valid-token"},
        )
    assert response.status_code == 200
    assert response.json()["friend_code"].startswith("FM-")
    assert auth.call.call_args.kwargs["token"] == "valid-token"


def test_existing_legacy_account_never_silently_linked(context):
    db, auth = context
    auth.call.return_value = IDENTITY
    db.scalar.side_effect = [None, uuid4()]
    with TestClient(app) as client:
        response = client.get(
            "/api/v1/users/me", headers={"Authorization": "Bearer valid-token"},
        )
    assert response.status_code == 409
    db.commit.assert_not_called()


def test_invalid_remote_identity(context):
    _, auth = context
    auth.call.return_value = {"id": "not-an-int", "email": PAYLOAD["email"]}
    with TestClient(app) as client:
        response = client.get(
            "/api/v1/users/me", headers={"Authorization": "Bearer valid-token"},
        )
    assert response.status_code == 502


def test_refresh_is_delegated(context):
    _, auth = context
    auth.call.return_value = {
        "access_token": "new", "refresh_token": "rotated", "token_type": "bearer",
    }
    with TestClient(app) as client:
        response = client.post("/api/v1/auth/refresh", json={"refresh_token": "old"})
    assert response.status_code == 200
    assert response.json()["refresh_token"] == "rotated"


def test_logout_is_delegated(context):
    _, auth = context
    auth.call.return_value = {}
    with TestClient(app) as client:
        response = client.post("/api/v1/auth/logout", json={"refresh_token": "old"})
    assert response.status_code == 204
    auth.call.assert_called_once()


def test_auth_service_unavailable(context):
    _, auth = context
    auth.call.side_effect = HTTPException(503, "Servico indisponivel")
    with TestClient(app) as client:
        response = client.post("/api/v1/auth/register", json=PAYLOAD)
    assert response.status_code == 503
