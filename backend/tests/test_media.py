from io import BytesIO
from uuid import uuid4

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from PIL import Image

from app.main import app
from app.dependencies.current_user import get_current_user
from app.models.user import User
from app.routers import media


@pytest.fixture
def media_client(tmp_path, monkeypatch):
    monkeypatch.setattr(media, "UPLOAD_DIR", tmp_path)
    user = User(id=uuid4(), username="media_test",
                email="media@example.test", friend_code="FM-AAAA2222")
    before = app.dependency_overrides.copy()
    app.dependency_overrides[get_current_user] = lambda: user
    try:
        with TestClient(app) as client:
            yield client, tmp_path
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(before)


def test_upload_valid_png(media_client):
    client, directory = media_client
    image = BytesIO()
    Image.new("RGB", (32, 24), "green").save(image, format="PNG")
    response = client.post("/api/v1/media/images",
                           files={"file": ("example.png", image.getvalue(), "image/png")})
    assert response.status_code == 201, response.text
    url = response.json()["url"]
    assert url.startswith("/media/") and url.endswith(".png")
    path = directory / url.rsplit("/", 1)[-1]
    with Image.open(path) as stored:
        assert stored.size == (32, 24)


def test_upload_rejects_invalid_image(media_client):
    client, directory = media_client
    response = client.post("/api/v1/media/images",
                           files={"file": ("bad.png", b"not an image", "image/png")})
    assert response.status_code == 400
    assert not list(directory.iterdir())


def test_upload_rejects_oversize(media_client):
    client, directory = media_client
    response = client.post("/api/v1/media/images",
                           files={"file": ("big.png", b"x" * (media.MAX_BYTES + 1), "image/png")})
    assert response.status_code == 413
    assert not list(directory.iterdir())


def test_upload_requires_authentication(media_client):
    client, directory = media_client

    def deny():
        raise HTTPException(status_code=401)

    app.dependency_overrides[get_current_user] = deny
    response = client.post("/api/v1/media/images",
                           files={"file": ("image.png", b"x", "image/png")})
    assert response.status_code == 401
    assert not list(directory.iterdir())
