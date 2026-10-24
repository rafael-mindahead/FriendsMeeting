"""HTTP boundary to the independent authService. Do not decode JWTs locally."""
import os
from collections.abc import Generator

import httpx
from fastapi import HTTPException, status


class AuthServiceClient:
    def __init__(self, client: httpx.Client):
        self.client = client

    def call(self, method: str, path: str, *, payload: dict | None = None,
             token: str | None = None) -> dict:
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        try:
            response = self.client.request(method, path, json=payload, headers=headers)
        except httpx.RequestError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Servico de autenticacao indisponivel",
            ) from exc

        if response.status_code == 204:
            return {}

        try:
            data = response.json()
        except ValueError as exc:
            raise HTTPException(503, "Resposta invalida do servico de autenticacao") from exc

        if not isinstance(data, dict):
            raise HTTPException(503, "Resposta invalida do servico de autenticacao")

        if response.status_code >= 400:
            if response.status_code in (400, 401, 403, 404, 409, 422, 429):
                raise HTTPException(
                    status_code=response.status_code,
                    detail=data.get("detail", "Solicitacao recusada"),
                )
            raise HTTPException(503, "Servico de autenticacao indisponivel")

        if not 200 <= response.status_code < 300:
            raise HTTPException(503, "Resposta inesperada do servico de autenticacao")
        return data


def get_auth_service() -> Generator[AuthServiceClient, None, None]:
    base_url = os.environ.get(
        "AUTH_SERVICE_URL", "http://host.docker.internal:8001"
    )
    with httpx.Client(base_url=base_url, timeout=5.0, trust_env=False) as client:
        yield AuthServiceClient(client)
