
import asyncio
from uuid import uuid4

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from app.main import app
from app.routers import websocket_chat
from app.realtime.manager import ConnectionManager, manager


@pytest.fixture
def context(monkeypatch):
    user_id = uuid4()
    conversation_id = uuid4()

    def fake_access(token, requested_conversation):
        assert requested_conversation == conversation_id

        if token == "valid-token":
            return user_id

        if token == "forbidden":
            raise HTTPException(404, "Conversa nao encontrada")

        if token == "service-down":
            raise HTTPException(503, "authService indisponivel")

        raise HTTPException(401, "Token invalido")

    monkeypatch.setattr(
        websocket_chat,
        "check_ws_access",
        fake_access,
    )

    with TestClient(app) as client:
        yield client, conversation_id, user_id


def test_websocket_authentication_and_ping(context):
    client, conversation_id, user_id = context

    path = f"/api/v1/conversations/{conversation_id}/ws"

    with client.websocket_connect(path) as ws:
        ws.send_json({
            "type": "auth",
            "token": "valid-token",
        })

        ready = ws.receive_json()

        assert ready["type"] == "ready"
        assert ready["user_id"] == str(user_id)
        assert manager.active(conversation_id) == 1

        ws.send_json({"type": "ping"})
        assert ws.receive_json() == {"type": "pong"}

    assert manager.active(conversation_id) == 0


def test_websocket_rejects_missing_token(context):
    client, conversation_id, user_id = context

    with client.websocket_connect(
        f"/api/v1/conversations/{conversation_id}/ws"
    ) as ws:
        ws.send_json({"type": "auth"})

        with pytest.raises(WebSocketDisconnect) as error:
            ws.receive_json()

        assert error.value.code == 1008


def test_websocket_rejects_invalid_token(context):
    client, conversation_id, user_id = context

    with client.websocket_connect(
        f"/api/v1/conversations/{conversation_id}/ws"
    ) as ws:
        ws.send_json({
            "type": "auth",
            "token": "invalid",
        })

        with pytest.raises(WebSocketDisconnect) as error:
            ws.receive_json()

        assert error.value.code == 1008


def test_websocket_denies_nonparticipant(context):
    client, conversation_id, user_id = context

    with client.websocket_connect(
        f"/api/v1/conversations/{conversation_id}/ws"
    ) as ws:
        ws.send_json({
            "type": "auth",
            "token": "forbidden",
        })

        with pytest.raises(WebSocketDisconnect) as error:
            ws.receive_json()

        assert error.value.code == 1008

    assert manager.active(conversation_id) == 0


def test_websocket_handles_auth_service_failure(context):
    client, conversation_id, user_id = context

    with client.websocket_connect(
        f"/api/v1/conversations/{conversation_id}/ws"
    ) as ws:
        ws.send_json({
            "type": "auth",
            "token": "service-down",
        })

        with pytest.raises(WebSocketDisconnect) as error:
            ws.receive_json()

        assert error.value.code == 1013


def test_connection_manager_isolates_rooms():
    class FakeSocket:
        def __init__(self):
            self.received = []

        async def send_json(self, event):
            self.received.append(event)

    connections = ConnectionManager()

    room_a = uuid4()
    room_b = uuid4()

    alice = FakeSocket()
    bob = FakeSocket()

    connections.add(room_a, alice)
    connections.add(room_b, bob)

    asyncio.run(
        connections.broadcast(
            room_a,
            {"type": "message", "body": "Privado"},
        )
    )

    assert alice.received == [
        {"type": "message", "body": "Privado"}
    ]
    assert bob.received == []

    connections.remove(room_a, alice)

    assert connections.active(room_a) == 0
    assert connections.active(room_b) == 1
