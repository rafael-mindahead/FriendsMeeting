import os
import secrets
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, delete
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker
from starlette.websockets import WebSocketDisconnect

from app.main import app
from app.Database.database import get_db
from app.dependencies.current_user import get_current_user
from app.clients.auth_service import AuthServiceClient
from app.models.user import User, generate_friend_code
from app.models.friend_request import FriendRequest
from app.models.conversation import Conversation
from app.models.message import Message
from app.routers import websocket_chat


@pytest.fixture
def pg_websocket(monkeypatch):
    raw_url = os.getenv("FRIENDSMEETING_TEST_DATABASE_URL")

    if not raw_url:
        pytest.fail("Banco de integracao nao configurado")

    url = make_url(raw_url)

    # Impede uso acidental do banco principal.
    assert url.get_backend_name() == "postgresql"
    assert url.host in ("127.0.0.1", "localhost")
    assert url.port == 5433
    assert url.database == "friendsmeeting_test"
    assert url.username == "test"

    engine = create_engine(raw_url, pool_pre_ping=True)
    SessionFactory = sessionmaker(
        bind=engine,
        expire_on_commit=False,
    )

    suffix = uuid4().hex[:8]
    auth_id = 100000 + secrets.randbelow(1500000000)

    alice = User(
        id=uuid4(),
        username=f"alice_{suffix}",
        email=f"alice_{suffix}@example.test",
        friend_code=generate_friend_code(),
        auth_user_id=auth_id,
    )

    bob = User(
        id=uuid4(),
        username=f"bob_{suffix}",
        email=f"bob_{suffix}@example.test",
        friend_code=generate_friend_code(),
        auth_user_id=auth_id + 1,
    )

    charlie = User(
        id=uuid4(),
        username=f"charlie_{suffix}",
        email=f"charlie_{suffix}@example.test",
        friend_code=generate_friend_code(),
        auth_user_id=auth_id + 2,
    )

    user_ids = [alice.id, bob.id, charlie.id]
    previous_overrides = app.dependency_overrides.copy()

    try:
        with SessionFactory() as db:
            db.add_all([alice, bob, charlie])
            db.flush()

            db.add(FriendRequest(
                sender_id=alice.id,
                receiver_id=bob.id,
                status="accepted",
            ))

            conversation = Conversation(
                id=uuid4(),
                user_a_id=alice.id,
                user_b_id=bob.id,
            )

            db.add(conversation)
            db.commit()

        identities = {
            "alice-token": {
                "id": alice.auth_user_id,
                "email": alice.email,
            },
            "bob-token": {
                "id": bob.auth_user_id,
                "email": bob.email,
            },
            "charlie-token": {
                "id": charlie.auth_user_id,
                "email": charlie.email,
            },
        }

        def fake_auth_call(
            self, method, path, *,
            payload=None, token=None
        ):
            assert method == "GET"
            assert path == "/auth/me"

            if token not in identities:
                raise HTTPException(401, "Token invalido")

            return identities[token]

        monkeypatch.setattr(
            AuthServiceClient,
            "call",
            fake_auth_call,
        )

        # As sessoes WebSocket agora usam o banco de testes.
        monkeypatch.setattr(
            websocket_chat,
            "SessionLocal",
            SessionFactory,
        )

        def override_db():
            with SessionFactory() as db:
                yield db

        app.dependency_overrides[get_db] = override_db
        app.dependency_overrides[get_current_user] = (
            lambda: alice
        )

        with TestClient(app) as client:
            yield (
                client,
                SessionFactory,
                conversation.id,
                alice,
                bob,
                charlie,
            )

    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous_overrides)

        # Remove dados criados pelos testes.
        # As FKs CASCADE removem conversas e mensagens.
        try:
            with SessionFactory() as db:
                db.execute(
                    delete(User).where(User.id.in_(user_ids))
                )
                db.commit()
        finally:
            engine.dispose()


def test_real_websocket_message_persistence(pg_websocket):
    client, factory, conversation_id, alice, bob, charlie = (
        pg_websocket
    )

    path = f"/api/v1/conversations/{conversation_id}/ws"

    with client.websocket_connect(path) as alice_ws:
        alice_ws.send_json({
            "type": "auth",
            "token": "alice-token",
        })
        assert alice_ws.receive_json()["type"] == "ready"

        with client.websocket_connect(path) as bob_ws:
            bob_ws.send_json({
                "type": "auth",
                "token": "bob-token",
            })
            assert bob_ws.receive_json()["type"] == "ready"

            alice_ws.send_json({
                "type": "send_message",
                "body": "Ola, Bob! Mensagem real.",
            })

            received_a = alice_ws.receive_json()
            received_b = bob_ws.receive_json()

            assert received_a == received_b
            assert received_b["type"] == "message"

            data = received_b["data"]

            assert data["body"] == "Ola, Bob! Mensagem real."
            assert data["sender_id"] == str(alice.id)

    # Outra sessao confirma que a transacao foi commitada.
    with factory() as db:
        saved = db.get(Message, UUID(data["id"]))

        assert saved is not None
        assert saved.conversation_id == conversation_id
        assert saved.sender_id == alice.id
        assert saved.body == data["body"]

    # Bob tambem deve conseguir recuperar pelo endpoint HTTP.
    app.dependency_overrides[get_current_user] = lambda: bob

    response = client.get(
        f"/api/v1/conversations/{conversation_id}/messages"
    )

    assert response.status_code == 200
    assert any(
        item["id"] == data["id"]
        for item in response.json()
    )


def test_real_websocket_denies_outsider(pg_websocket):
    client, factory, conversation_id, alice, bob, charlie = (
        pg_websocket
    )

    path = f"/api/v1/conversations/{conversation_id}/ws"

    with client.websocket_connect(path) as ws:
        ws.send_json({
            "type": "auth",
            "token": "charlie-token",
        })

        with pytest.raises(WebSocketDisconnect) as error:
            ws.receive_json()

        assert error.value.code == 1008


def test_real_database_rejects_forged_sender(pg_websocket):
    client, factory, conversation_id, alice, bob, charlie = (
        pg_websocket
    )

    with pytest.raises(HTTPException) as error:
        websocket_chat.persist_ws_message(
            conversation_id,
            charlie.id,
            "Mensagem nao autorizada",
        )

    assert error.value.status_code == 404

    with factory() as db:
        messages = db.query(Message).filter(
            Message.conversation_id == conversation_id
        ).all()

        assert messages == []
