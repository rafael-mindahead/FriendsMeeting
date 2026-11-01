from io import BytesIO
from uuid import uuid4
from unittest.mock import MagicMock

import pytest
from PIL import Image
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.Database.database import get_db
from app.dependencies.current_user import get_current_user
from app.models.user import User
from app.models.user_avatar import UserAvatar


def sample_image():
    out = BytesIO()
    Image.new("RGB", (64, 48), "#68d6a5").save(out, format="PNG")
    return out.getvalue()


@pytest.fixture
def avatar_client():
    user = User(id=uuid4(), username="avatar_test", email="avatar@example.test", friend_code="FM-AAAA2222")
    db = MagicMock(spec=Session)
    before = app.dependency_overrides.copy()
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: user
    try:
        with TestClient(app) as client:
            yield client, db, user
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(before)


def test_upload_sanitizes_and_commits(avatar_client):
    client, db, user = avatar_client
    db.get.return_value = None
    response = client.put("/api/v1/users/me/avatar", files={"file": ("photo.png", sample_image(), "image/png")})
    assert response.status_code == 200, response.text
    assert response.json()["avatar_url"].startswith(f"/api/v1/users/{user.id}/avatar?v=")
    db.add.assert_called_once()
    assert db.add.call_args.args[0].media_type == "image/webp"
    assert db.add.call_args.args[0].image[:4] == b"RIFF"
    db.commit.assert_called_once()


def test_public_avatar_is_safe_webp(avatar_client):
    client, db, user = avatar_client
    avatar = UserAvatar(user_id=user.id, image=b"RIFFmock", media_type="image/webp", revision=uuid4())
    db.get.return_value = avatar
    response = client.get(f"/api/v1/users/{user.id}/avatar")
    assert response.status_code == 200
    assert response.content == b"RIFFmock"
    assert response.headers["content-type"] == "image/webp"
    assert response.headers["x-content-type-options"] == "nosniff"


def test_unknown_avatar_returns_404(avatar_client):
    client, db, user = avatar_client
    db.get.return_value = None
    assert client.get(f"/api/v1/users/{uuid4()}/avatar").status_code == 404


def test_delete_photo_is_idempotent(avatar_client):
    client, db, user = avatar_client
    db.get.return_value = None
    assert client.delete("/api/v1/users/me/avatar").status_code == 204
    db.delete.assert_not_called()


def test_delete_existing_photo(avatar_client):
    client, db, user = avatar_client
    db.get.return_value = UserAvatar(user_id=user.id, image=b"x", media_type="image/webp", revision=uuid4())
    assert client.delete("/api/v1/users/me/avatar").status_code == 204
    db.delete.assert_called_once()
    db.commit.assert_called_once()
