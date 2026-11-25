from uuid import uuid4

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from app.main import app
from app.realtime.manager import ConnectionManager, manager
from app.routers import user_events


@pytest.fixture
def context(monkeypatch):
    user_id = uuid4()

    def fake_access(token):
        if token == "valid-token":
            return user_id
        if token == "service-down":
            raise HTTPException(503, "authService indisponível")
        raise HTTPException(401, "Token inválido")

    monkeypatch.setattr(user_events, "check_user_event_access", fake_access)
    with TestClient(app) as client:
        yield client, user_id


def test_user_event_websocket_authenticates_and_responds_to_ping(context):
    client, user_id = context

    with client.websocket_connect("/api/v1/events/ws") as websocket:
        websocket.send_json({"type": "auth", "token": "valid-token"})
        assert websocket.receive_json() == {
            "type": "ready",
            "user_id": str(user_id),
        }
        websocket.send_json({"type": "ping"})
        assert websocket.receive_json() == {"type": "pong"}
        assert len(manager.user_connections[user_id]) == 1

    assert user_id not in manager.user_connections


def test_user_event_websocket_rejects_invalid_authentication(context):
    client, _ = context

    with client.websocket_connect("/api/v1/events/ws") as websocket:
        websocket.send_json({"type": "auth", "token": "invalid"})
        with pytest.raises(WebSocketDisconnect) as error:
            websocket.receive_json()
        assert error.value.code == 1008


def test_user_event_websocket_reports_auth_service_failure(context):
    client, _ = context

    with client.websocket_connect("/api/v1/events/ws") as websocket:
        websocket.send_json({"type": "auth", "token": "service-down"})
        with pytest.raises(WebSocketDisconnect) as error:
            websocket.receive_json()
        assert error.value.code == 1013


def test_manager_delivers_events_only_to_the_target_user():
    class FakeSocket:
        def __init__(self):
            self.received = []

        async def send_json(self, event):
            self.received.append(event)

    connections = ConnectionManager()
    alice_id = uuid4()
    bob_id = uuid4()
    alice_socket = FakeSocket()
    bob_socket = FakeSocket()
    connections.add_user(alice_id, alice_socket)
    connections.add_user(bob_id, bob_socket)
    event = {"type": "notification", "event_id": "message-1"}

    import asyncio
    asyncio.run(connections.notify_user(bob_id, event))

    assert alice_socket.received == []
    assert bob_socket.received == [event]
