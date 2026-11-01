
import asyncio
from uuid import uuid4

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from app.main import app
from app.routers import websocket_chat
from app.realtime.manager import ConnectionManager, manager
from datetime import datetime, timezone


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








def test_two_users_exchange_messages(context, monkeypatch):
    client, conversation_id, alice_id = context
    bob_id = uuid4()
    persisted = []

    def fake_access(token, requested_conversation):
        assert requested_conversation == conversation_id

        if token == "alice":
            return alice_id
        if token == "bob":
            return bob_id

        raise HTTPException(401, "Token invalido")

    def fake_persist(requested_conversation, sender_id, body):
        persisted.append(body)

        return {
            "id": str(uuid4()),
            "conversation_id": str(requested_conversation),
            "sender_id": str(sender_id),
            "body": body,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

    monkeypatch.setattr(
        websocket_chat, "check_ws_access", fake_access
    )
    monkeypatch.setattr(
        websocket_chat, "persist_ws_message", fake_persist
    )

    url = f"/api/v1/conversations/{conversation_id}/ws"

    with client.websocket_connect(url) as alice:
        alice.send_json({"type": "auth", "token": "alice"})
        assert alice.receive_json()["type"] == "ready"

        with client.websocket_connect(url) as bob:
            bob.send_json({"type": "auth", "token": "bob"})
            assert bob.receive_json()["type"] == "ready"

            assert manager.active(conversation_id) == 2

            alice.send_json({
                "type": "send_message",
                "body": "Ola, Bob!",
                "sender_id": str(bob_id),
            })

            alice_event = alice.receive_json()
            bob_event = bob.receive_json()

            assert alice_event == bob_event
            assert bob_event["type"] == "message"
            assert bob_event["data"]["body"] == "Ola, Bob!"
            assert bob_event["data"]["sender_id"] == str(alice_id)

    assert persisted == ["Ola, Bob!"]
    assert manager.active(conversation_id) == 0


@pytest.mark.parametrize("body", ["   ", "A" * 2001])
def test_ws_rejects_invalid_message(context, monkeypatch, body):
    client, conversation_id, user_id = context

    def unexpected_persist(*args):
        raise AssertionError("Mensagem invalida foi persistida")

    monkeypatch.setattr(
        websocket_chat,
        "persist_ws_message",
        unexpected_persist,
    )

    with client.websocket_connect(
        f"/api/v1/conversations/{conversation_id}/ws"
    ) as ws:
        ws.send_json({"type": "auth", "token": "valid-token"})
        assert ws.receive_json()["type"] == "ready"

        ws.send_json({
            "type": "send_message",
            "body": body,
        })

        response = ws.receive_json()

        assert response["type"] == "error"
        assert response["code"] == "invalid_message"


def test_ws_database_failure(context, monkeypatch):
    client, conversation_id, user_id = context

    def failing_persist(*args):
        raise HTTPException(503, "Banco indisponivel")

    monkeypatch.setattr(
        websocket_chat,
        "persist_ws_message",
        failing_persist,
    )

    with client.websocket_connect(
        f"/api/v1/conversations/{conversation_id}/ws"
    ) as ws:
        ws.send_json({"type": "auth", "token": "valid-token"})
        assert ws.receive_json()["type"] == "ready"

        ws.send_json({
            "type": "send_message",
            "body": "Teste de falha",
        })

        response = ws.receive_json()

        assert response["type"] == "error"
        assert response["code"] == "message_not_saved"
        assert response["status"] == 503

        ws.send_json({"type": "ping"})
        assert ws.receive_json() == {"type": "pong"}






def test_presence_tracks_multiple_tabs():
    connections = ConnectionManager()
    room = uuid4()
    user = uuid4()
    tab1 = object()
    tab2 = object()

    assert connections.add(room, tab1, user) is True
    assert connections.add(room, tab2, user) is False

    assert connections.active(room) == 2
    assert connections.online_users(room) == [str(user)]

    assert connections.remove(room, tab1) == (
        user, False
    )
    assert connections.is_online(room, user)

    assert connections.remove(room, tab2) == (
        user, True
    )
    assert not connections.is_online(room, user)


def test_presence_is_isolated_between_rooms():
    connections = ConnectionManager()
    room_a = uuid4()
    room_b = uuid4()
    alice = uuid4()
    bob = uuid4()

    connections.add(room_a, object(), alice)
    connections.add(room_b, object(), bob)

    assert connections.online_users(room_a) == [
        str(alice)
    ]
    assert connections.online_users(room_b) == [
        str(bob)
    ]
    assert not connections.is_online(room_a, bob)


def test_websocket_presence_snapshot(context):
    client, conversation_id, user_id = context

    path = f"/api/v1/conversations/{conversation_id}/ws"

    with client.websocket_connect(path) as ws:
        ws.send_json({
            "type": "auth",
            "token": "valid-token",
        })
        assert ws.receive_json()["type"] == "ready"

        ws.send_json({
            "type": "subscribe_presence",
        })

        snapshot = ws.receive_json()

        assert snapshot["type"] == "presence_snapshot"
        assert snapshot["online_user_ids"] == [
            str(user_id)
        ]


def test_websocket_notifies_online_and_offline(
    context, monkeypatch
):
    client, conversation_id, alice_id = context
    bob_id = uuid4()

    def access(token, requested_room):
        assert requested_room == conversation_id
        return {
            "valid-token": alice_id,
            "bob-token": bob_id,
        }[token]

    monkeypatch.setattr(
        websocket_chat, "check_ws_access", access
    )

    path = f"/api/v1/conversations/{conversation_id}/ws"

    with client.websocket_connect(path) as alice:
        alice.send_json({
            "type": "auth",
            "token": "valid-token",
        })
        assert alice.receive_json()["type"] == "ready"

        alice.send_json({"type": "subscribe_presence"})
        assert alice.receive_json()["type"] == (
            "presence_snapshot"
        )

        with client.websocket_connect(path) as bob:
            bob.send_json({
                "type": "auth",
                "token": "bob-token",
            })
            assert bob.receive_json()["type"] == "ready"

            assert alice.receive_json() == {
                "type": "presence",
                "user_id": str(bob_id),
                "online": True,
            }

        assert alice.receive_json() == {
            "type": "presence",
            "user_id": str(bob_id),
            "online": False,
        }


def test_multiple_tabs_do_not_send_false_offline(
    context, monkeypatch
):
    client, conversation_id, alice_id = context
    bob_id = uuid4()

    def access(token, requested_room):
        return {
            "valid-token": alice_id,
            "bob-token": bob_id,
        }[token]

    monkeypatch.setattr(
        websocket_chat, "check_ws_access", access
    )

    path = f"/api/v1/conversations/{conversation_id}/ws"

    with client.websocket_connect(path) as alice:
        alice.send_json({
            "type": "auth",
            "token": "valid-token",
        })
        alice.receive_json()

        alice.send_json({"type": "subscribe_presence"})
        alice.receive_json()

        with client.websocket_connect(path) as bob1:
            bob1.send_json({
                "type": "auth",
                "token": "bob-token",
            })
            bob1.receive_json()

            assert alice.receive_json()["online"] is True

            with client.websocket_connect(path) as bob2:
                bob2.send_json({
                    "type": "auth",
                    "token": "bob-token",
                })
                bob2.receive_json()

            # Fechar bob2 nao deixa bob offline.
            assert manager.is_online(
                conversation_id, bob_id
            )

            # Nenhum evento extra deve vir antes do pong.
            alice.send_json({"type": "ping"})
            assert alice.receive_json() == {
                "type": "pong"
            }

        # Somente apos fechar bob1, a ultima aba.
        assert alice.receive_json() == {
            "type": "presence",
            "user_id": str(bob_id),
            "online": False,
        }


def test_late_subscriber_sees_existing_users(
    context, monkeypatch
):
    client, conversation_id, alice_id = context
    bob_id = uuid4()

    def access(token, requested_room):
        return {
            "valid-token": alice_id,
            "bob-token": bob_id,
        }[token]

    monkeypatch.setattr(
        websocket_chat, "check_ws_access", access
    )

    path = f"/api/v1/conversations/{conversation_id}/ws"

    with client.websocket_connect(path) as bob:
        bob.send_json({
            "type": "auth",
            "token": "bob-token",
        })
        assert bob.receive_json()["type"] == "ready"

        with client.websocket_connect(path) as alice:
            alice.send_json({
                "type": "auth",
                "token": "valid-token",
            })
            assert alice.receive_json()["type"] == "ready"

            alice.send_json({
                "type": "subscribe_presence",
            })

            snapshot = alice.receive_json()

            assert snapshot["type"] == "presence_snapshot"
            assert set(snapshot["online_user_ids"]) == {
                str(alice_id),
                str(bob_id),
            }

            # Bob nao assinou presença: segue recebendo
            # apenas os eventos do protocolo que solicitar.
            bob.send_json({"type": "ping"})
            assert bob.receive_json() == {"type": "pong"}

