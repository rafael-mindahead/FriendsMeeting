from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError

from app.main import app
from app.Database.database import get_db
from app.security.password import verify_password


PAYLOAD = {
    "username": "usuario_teste",
    "email": "teste@example.com",
    "password": "SenhaSegura2026!"
}


@pytest.fixture
def fake_db():
    db = MagicMock()
    db.scalar.return_value = None

    def simulate_refresh(user):
        user.id = uuid4()
        user.created_at = datetime.now(timezone.utc)

    db.refresh.side_effect = simulate_refresh
    app.dependency_overrides[get_db] = lambda: db

    try:
        yield db
    finally:
        app.dependency_overrides.clear()


def constraint_error(name):
    original = Exception("Violacao de unicidade")
    original.diag = SimpleNamespace(
        constraint_name=name
    )

    return IntegrityError(
        "INSERT INTO users",
        {},
        original
    )


def test_register_success(fake_db):
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/auth/register",
            json=PAYLOAD
        )

    assert response.status_code == 201

    data = response.json()

    assert data["username"] == "usuario_teste"
    assert data["email"] == "teste@example.com"
    assert data["friend_code"].startswith("FM-")
    assert len(data["friend_code"]) == 11
    assert "password_hash" not in data
    assert "password" not in data

    saved_user = fake_db.add.call_args.args[0]

    assert saved_user.password_hash != PAYLOAD["password"]
    assert verify_password(
        PAYLOAD["password"],
        saved_user.password_hash
    )

    fake_db.commit.assert_called_once()


def test_register_duplicate_email(fake_db):
    fake_db.scalar.return_value = uuid4()

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/auth/register",
            json=PAYLOAD
        )

    assert response.status_code == 409
    assert response.json()["detail"] == "E-mail ja cadastrado"

    fake_db.commit.assert_not_called()


def test_register_duplicate_username(fake_db):
    fake_db.scalar.side_effect = [None, uuid4()]

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/auth/register",
            json=PAYLOAD
        )

    assert response.status_code == 409
    assert response.json()["detail"] == (
        "Nome de usuario ja cadastrado"
    )


@pytest.mark.parametrize(
    "field,value",
    [
        ("email", "email-invalido"),
        ("password", "123"),
        ("username", "ab"),
        ("username", "nome com espaco"),
    ]
)
def test_register_invalid_data(fake_db, field, value):
    payload = PAYLOAD.copy()
    payload[field] = value

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/auth/register",
            json=payload
        )

    assert response.status_code == 422
    fake_db.commit.assert_not_called()


def test_friend_code_collision_retry(fake_db, monkeypatch):
    fake_db.commit.side_effect = [
        constraint_error("ix_users_friend_code"),
        None
    ]

    codes = iter([
        "FM-ABCDEFGH",
        "FM-JKLMNPQR"
    ])

    monkeypatch.setattr(
        "app.routers.auth.generate_friend_code",
        lambda: next(codes)
    )

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/auth/register",
            json=PAYLOAD
        )

    assert response.status_code == 201
    assert response.json()["friend_code"] == "FM-JKLMNPQR"
    assert fake_db.commit.call_count == 2

    fake_db.rollback.assert_called_once()


def test_duplicate_during_insert(fake_db):
    fake_db.commit.side_effect = constraint_error(
        "ix_users_email"
    )

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/auth/register",
            json=PAYLOAD
        )

    assert response.status_code == 409
    fake_db.rollback.assert_called_once()
