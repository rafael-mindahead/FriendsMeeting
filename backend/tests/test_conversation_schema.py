
import os

import pytest
from sqlalchemy import create_engine, inspect
from sqlalchemy.engine import make_url


@pytest.fixture(scope="module")
def database():
    raw_url = os.getenv("FRIENDSMEETING_TEST_DATABASE_URL")

    if not raw_url:
        pytest.skip("Banco de testes nao configurado")

    url = make_url(raw_url)

    assert url.get_backend_name() == "postgresql"
    assert url.host in ("127.0.0.1", "localhost")
    assert url.port == 5433
    assert url.database == "friendsmeeting_test"

    engine = create_engine(raw_url)

    try:
        yield engine
    finally:
        engine.dispose()


def test_conversation_schema(database):
    inspector = inspect(database)

    assert inspector.has_table("conversations")

    columns = {
        col["name"]
        for col in inspector.get_columns("conversations")
    }

    assert {
        "id",
        "user_a_id",
        "user_b_id",
        "created_at",
    } <= columns

    indexes = {
        index["name"]
        for index in inspector.get_indexes("conversations")
    }

    assert "uq_conversations_pair" in indexes


def test_message_schema(database):
    inspector = inspect(database)

    assert inspector.has_table("messages")

    columns = {
        col["name"]
        for col in inspector.get_columns("messages")
    }

    assert {
        "id",
        "conversation_id",
        "sender_id",
        "body",
        "created_at",
    } <= columns

    constraints = {
        check["name"]
        for check in inspector.get_check_constraints("messages")
    }

    assert "ck_messages_body_length" in constraints
