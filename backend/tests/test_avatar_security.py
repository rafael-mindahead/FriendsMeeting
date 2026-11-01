from io import BytesIO
from unittest.mock import MagicMock
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.Database.database import get_db
from app.dependencies.current_user import get_current_user


def test_avatar_upload_requires_auth():
    before = app.dependency_overrides.copy()
    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides[get_db] = lambda: MagicMock(spec=Session)
    try:
        with TestClient(app) as client:
            response = client.put("/api/v1/users/me/avatar", files={
                "file": ("test.png", b"anything", "image/png")
            })
            assert response.status_code == 401
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(before)


def test_avatar_deletion_requires_auth():
    before = app.dependency_overrides.copy()
    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides[get_db] = lambda: MagicMock(spec=Session)
    try:
        with TestClient(app) as client:
            assert client.delete("/api/v1/users/me/avatar").status_code == 401
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(before)
