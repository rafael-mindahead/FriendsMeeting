import hashlib
import os
import secrets
from uuid import UUID

from redis import Redis
from redis.exceptions import RedisError
from fastapi import HTTPException

REDIS_URL = os.getenv(
    "CALL_AUTH_REDIS_URL",
    "redis://auth-redis:6379/1",
)

CREDENTIAL_TTL = 30
KEY_PREFIX = "friendsmeeting:call_auth:"

def get_redis() -> Redis:
    return Redis.from_url(
        REDIS_URL,
        decode_responses=True,
        socket_connect_timeout=3,
        socket_timeout=3,
    )

def credential_key(credential: str) -> str:
    digest = hashlib.sha256(
        credential.encode("utf-8")
    ).hexdigest()
    return f"{KEY_PREFIX}{digest}"

def create_credential(user_id:UUID) -> str:
    credential = secrets.token_urlsafe(32)
    key = credential_key(credential)

    try:
        with get_redis() as redis:
            redis.set(
                key,
                str(user_id),
                ex=CREDENTIAL_TTL,
                nx=True,
            )

    except RedisError as exc:
        raise HTTPException(
            status_code=503,
            detail="Serviço de Credenciais Indisponível",
        ) from exc

    return credential

def consume_credential(credential: str) -> UUID | None:
    if not isinstance(credential, str):
        return None

    if not 1 <= len(credential) <= 128:
        return None

    key = credential_key(credential)

    try:
        with get_redis() as redis:
            user_id = redis.getdel(key)

    except RedisError as exc:
        raise HTTPException(
            status_code=503,
            detail="Serviço de Credenciais Indisponível",
        ) from exc

    if user_id is None:
        return None

    return UUID(user_id)
