import httpx
import pytest
from fastapi import HTTPException

from app.clients.auth_service import AuthServiceClient


def test_http_client_forwards_bearer():
    def response(request):
        assert request.headers["authorization"] == "Bearer signed-token"
        return httpx.Response(200, json={"id": 9, "email": "a@example.com"})

    with httpx.Client(
        base_url="http://auth.local", transport=httpx.MockTransport(response),
    ) as transport:
        result = AuthServiceClient(transport).call(
            "GET", "/auth/me", token="signed-token",
        )
    assert result["id"] == 9


def test_http_client_preserves_auth_errors():
    with httpx.Client(
        base_url="http://auth.local",
        transport=httpx.MockTransport(
            lambda request: httpx.Response(401, json={"detail": "Token expirado"})
        ),
    ) as transport:
        with pytest.raises(HTTPException) as exc:
            AuthServiceClient(transport).call("GET", "/auth/me", token="bad")
    assert exc.value.status_code == 401


def test_http_client_handles_disconnect():
    def fail(request):
        raise httpx.ConnectError("unreachable", request=request)

    with httpx.Client(
        base_url="http://auth.local", transport=httpx.MockTransport(fail),
    ) as transport:
        with pytest.raises(HTTPException) as exc:
            AuthServiceClient(transport).call("GET", "/auth/me", token="bad")
    assert exc.value.status_code == 503


def test_http_client_does_not_leak_upstream_500():
    with httpx.Client(
        base_url="http://auth.local",
        transport=httpx.MockTransport(
            lambda request: httpx.Response(500, json={"detail": "internal traceback"})
        ),
    ) as transport:
        with pytest.raises(HTTPException) as exc:
            AuthServiceClient(transport).call("GET", "/auth/me")
    assert exc.value.status_code == 503
    assert "traceback" not in str(exc.value.detail)
