
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

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
