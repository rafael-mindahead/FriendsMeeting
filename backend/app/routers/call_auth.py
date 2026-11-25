
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

import os
import secrets
from fastapi import Header, HTTPException
from app.services.call_auth import consume_credential

from app.Database.database import get_db
from app.dependencies.current_user import get_current_user
from app.models.user import User
from app.services.call_auth import (
    create_credential,
    CREDENTIAL_TTL,
)


router = APIRouter(
    prefix="/api/v1/calls/auth",
    tags=["Call Authentication"],
)


class CredentialResponse(BaseModel):
    credential: str
    expires_in: int


@router.post(
    "/credential",
    response_model=CredentialResponse,
)
def issue_credential(
    current_user: User = Depends(get_current_user),
):
    credential = create_credential(current_user.id)

    return CredentialResponse(
        credential=credential,
        expires_in=CREDENTIAL_TTL,
    )


class ConsumeCredentialRequest(BaseModel):
    credential: str


class ConsumeCredentialResponse(BaseModel):
    user_id: str


def validate_device_key(
    x_device_key: str | None = Header(default=None),
):
    expected_key = os.getenv("ESP32_DEVICE_KEY")

    if not expected_key:
        raise HTTPException(
            status_code=503,
            detail="Autenticacao do dispositivo indisponivel",
        )

    if not x_device_key or not secrets.compare_digest(
        x_device_key,
        expected_key,
    ):
        raise HTTPException(
            status_code=401,
            detail="Dispositivo nao autorizado",
        )


@router.post(
    "/consume",
    response_model=ConsumeCredentialResponse,
    dependencies=[Depends(validate_device_key)],
)
def consume_call_credential(
    data: ConsumeCredentialRequest,
):
    user_id = consume_credential(data.credential)

    if user_id is None:
        raise HTTPException(
            status_code=401,
            detail="Credencial invalida ou expirada",
        )

    return ConsumeCredentialResponse(
        user_id=str(user_id),
    )
