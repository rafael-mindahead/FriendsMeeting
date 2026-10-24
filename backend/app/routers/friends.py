
from datetime import datetime
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import and_, or_, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.Database.database import get_db
from app.dependencies.current_user import get_current_user
from app.models.friend_request import FriendRequest
from app.models.user import User

router = APIRouter(
    prefix="/api/v1/friends",
    tags=["Friends"],
)


class FriendRequestCreate(BaseModel):
    friend_code: str = Field(
        pattern=r"^FM-[A-Z2-9]{8}$",
    )

    @field_validator("friend_code", mode="before")
    @classmethod
    def normalize_code(cls, value):
        if isinstance(value, str):
            return value.strip().upper()
        return value


class FriendRequestPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    sender_id: UUID
    receiver_id: UUID
    status: Literal["pending", "accepted", "rejected"]
    created_at: datetime
    responded_at: datetime | None


@router.post(
    "/requests",
    response_model=FriendRequestPublic,
    status_code=201,
)
def send_friend_request(
    data: FriendRequestCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    receiver = db.scalar(
        select(User).where(
            User.friend_code == data.friend_code
        )
    )

    if receiver is None:
        raise HTTPException(
            status_code=404,
            detail="Codigo de amizade nao encontrado",
        )

    if receiver.id == current_user.id:
        raise HTTPException(
            status_code=400,
            detail="Voce nao pode adicionar a si mesmo",
        )

    existing = db.scalar(
        select(FriendRequest)
        .where(
            or_(
                and_(
                    FriendRequest.sender_id == current_user.id,
                    FriendRequest.receiver_id == receiver.id,
                ),
                and_(
                    FriendRequest.sender_id == receiver.id,
                    FriendRequest.receiver_id == current_user.id,
                ),
            )
        )
        .with_for_update()
    )

    if existing is not None:
        if existing.status == "pending":
            raise HTTPException(
                status_code=409,
                detail="Ja existe uma solicitacao pendente",
            )

        if existing.status == "accepted":
            raise HTTPException(
                status_code=409,
                detail="Usuarios ja sao amigos",
            )

        # Permite reenviar uma solicitacao recusada.
        existing.sender_id = current_user.id
        existing.receiver_id = receiver.id
        existing.status = "pending"
        existing.responded_at = None

        try:
            db.commit()
            db.refresh(existing)
            return existing
        except SQLAlchemyError as exc:
            db.rollback()
            raise HTTPException(
                status_code=503,
                detail="Erro ao reenviar solicitacao",
            ) from exc

    request = FriendRequest(
        sender_id=current_user.id,
        receiver_id=receiver.id,
        status="pending",
    )

    db.add(request)

    try:
        db.commit()
        db.refresh(request)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Ja existe uma relacao entre estes usuarios",
        ) from exc
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=503,
            detail="Erro ao salvar solicitacao",
        ) from exc

    return request
