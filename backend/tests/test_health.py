from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import SQLAlchemyError

from app.main import app, get_db

@pytest.fixture(autouse=True)
def clean_dependencies():
    yield
    app.dependency_overrides.clear()


def test_api_health():
    with TestClient(app) as client:
        response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_database_healthy():
    fake_db = MagicMock()
    fake_db.execute.return_value.scalar_one.return_value = 1

    def override_db():
        yield fake_db

    app.dependency_overrides[get_db] = override_db

    with TestClient(app) as client:
        response = client.get("/api/v1/health/database")

    print("RESPOSTA:", response.status_code, response.json())
    print("MOCK CHAMADO:", fake_db.execute.called)

    assert response.status_code == 200
    assert response.json()["connection"] == "healthy"
    fake_db.execute.assert_called_once()


def test_database_unavailable():
    fake_db = MagicMock()
    fake_db.execute.side_effect = SQLAlchemyError(
        "Falha de conexao simulada"
    )

    def override_db():
        yield fake_db

    app.dependency_overrides[get_db] = override_db

    with TestClient(app) as client:
        response = client.get("/api/v1/health/database")

    assert response.status_code == 503
    assert response.json()["detail"] == (
        "Banco de dados indisponivel"
    )


def test_database_invalid_response():
    fake_db = MagicMock()
    fake_db.execute.return_value.scalar_one.return_value = 0

    def override_db():
        yield fake_db

    app.dependency_overrides[get_db] = override_db

    with TestClient(app) as client:
        response = client.get("/api/v1/health/database")

    assert response.status_code == 503
