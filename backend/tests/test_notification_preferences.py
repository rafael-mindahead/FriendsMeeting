from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.Database.database import get_db
from app.dependencies.current_user import get_current_user
from app.main import app
from app.models.notification_preference import (
    NotificationPreference,
    NotificationSenderPreference,
)
from app.models.user import User


@pytest.fixture
def context():
    current_user = User(
        id=uuid4(),
        username="rafa",
        email="rafa@example.com",
        friend_code="FM-QWERTY23",
    )
    sender = User(
        id=uuid4(),
        username="amigo",
        email="amigo@example.com",
        friend_code="FM-ASDFGH23",
    )
    db = MagicMock()
    global_preferences = {}
    sender_preferences = []

    def find(model, key):
        if model is NotificationPreference:
            return global_preferences.get(key)
        if model is NotificationSenderPreference:
            return next(
                (
                    item
                    for item in sender_preferences
                    if (item.user_id, item.sender_id) == key
                ),
                None,
            )
        if model is User:
            return sender if key == sender.id else None
        return None

    def add(item):
        if isinstance(item, NotificationPreference):
            global_preferences[item.user_id] = item
        elif isinstance(item, NotificationSenderPreference):
            sender_preferences.append(item)

    def delete(item):
        sender_preferences.remove(item)

    db.get.side_effect = find
    db.add.side_effect = add
    db.delete.side_effect = delete
    db.scalars.return_value.all.side_effect = lambda: sender_preferences.copy()
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: current_user

    try:
        with TestClient(app) as client:
            yield client, db, current_user, sender, sender_preferences
    finally:
        app.dependency_overrides.clear()


def test_preferences_default_to_full_volume_and_no_mute(context):
    client, db, _, _, _ = context

    response = client.get("/api/v1/notifications/preferences")

    assert response.status_code == 200
    assert response.json() == {
        "muted": False,
        "volume": 100,
        "senders": [],
    }
    db.commit.assert_not_called()


def test_global_preferences_are_saved_for_the_account(context):
    client, db, _, _, _ = context

    response = client.put(
        "/api/v1/notifications/preferences",
        json={"muted": True, "volume": 65},
    )

    assert response.status_code == 200
    assert response.json()["muted"] is True
    assert response.json()["volume"] == 65
    db.commit.assert_called_once()


@pytest.mark.parametrize("volume", [-1, 101])
def test_global_volume_is_limited_to_zero_through_one_hundred(context, volume):
    client, db, _, _, _ = context

    response = client.put(
        "/api/v1/notifications/preferences",
        json={"muted": False, "volume": volume},
    )

    assert response.status_code == 422
    db.commit.assert_not_called()


def test_sender_volume_factor_and_mute_are_saved(context):
    client, db, _, sender, sender_preferences = context

    response = client.put(
        f"/api/v1/notifications/preferences/senders/{sender.id}",
        json={"muted": True, "volume_factor": 35},
    )

    assert response.status_code == 200
    assert response.json()["senders"] == [{
        "user_id": str(sender.id),
        "muted": True,
        "volume_factor": 35,
    }]
    assert len(sender_preferences) == 1
    db.commit.assert_called_once()


def test_users_cannot_configure_themselves_as_a_sender(context):
    client, db, user, _, _ = context

    response = client.put(
        f"/api/v1/notifications/preferences/senders/{user.id}",
        json={"muted": True, "volume_factor": 0},
    )

    assert response.status_code == 400
    db.commit.assert_not_called()


def test_unknown_sender_is_rejected(context):
    client, db, _, _, _ = context

    response = client.put(
        f"/api/v1/notifications/preferences/senders/{uuid4()}",
        json={"muted": True, "volume_factor": 0},
    )

    assert response.status_code == 404
    db.commit.assert_not_called()


def test_sender_override_can_be_reset(context):
    client, db, user, sender, sender_preferences = context
    preference = NotificationSenderPreference(
        user_id=user.id,
        sender_id=sender.id,
        muted=True,
        volume_factor=20,
    )
    sender_preferences.append(preference)

    response = client.delete(
        f"/api/v1/notifications/preferences/senders/{sender.id}"
    )

    assert response.status_code == 200
    assert response.json()["senders"] == []
    db.delete.assert_called_once_with(preference)


def test_notification_preferences_require_authentication(context):
    client, _, _, _, _ = context
    app.dependency_overrides.pop(get_current_user, None)

    response = client.get("/api/v1/notifications/preferences")

    assert response.status_code == 401
