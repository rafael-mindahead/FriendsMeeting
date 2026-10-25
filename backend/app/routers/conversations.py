from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, ConfigDict
from sqlalchemy import and_, or_, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.Database.database import get_db
from app.dependencies.current_user import get_current_user
from app.models.conversation import Conversation
from app.models.friend_request import FriendRequest
from app.models.user import User
from datetime import datetime

router = APIRouter(
    prefix="/api/v1/conversations",
    tags=["Conversations"],
)
class ConversationCreate(BaseModel):
    friend_id: UUID


class ConversationPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_a_id: UUID
    user_b_id: UUID
    created_at: datetime


def find_conversation_between_users(db: Session, user_a: UUID, user_b: UUID):
    return db.scalar(
        select(Conversation).where(
            or_(
                and_(
                    Conversation.user_a_id == user_a,
                    Conversation.user_b_id == user_b
                ),
                and_(
                    Conversation.user_a_id == user_b,
                    Conversation.user_b_id == user_a
                ),
            )
        )
    )

@router.post(
    "",
    response_model=ConversationPublic,
    status_code=201,
)
def create_conversation(
    data: ConversationCreate,
    response: Response,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if data.friend_id == current_user.id:
        raise HTTPException(
            status_code=400,
            detail="Nao e permetido conversar com voce mesmo",
        )
    friendship =db.scalar(
        select(FriendRequest).where(
            FriendRequest.status == "accepted",
            or_(
                and_(
                    FriendRequest.sender_id == current_user.id,
                    FriendRequest.receiver_id == data.friend_id,
                ),
                and_(
                    FriendRequest.sender_id == data.friend_id,
                    FriendRequest.receiver_id == current_user.id,
                ),
            ),
        )
    )
    if friendship is None:
        raise HTTPException(
            status_code=403,
            detail="apenas amigos podem iniciar conversas",
        )
    existing = find_conversation_between_users(
        db, current_user.id, data.friend_id
    )
    if existing is not None:
        response.status_code = 200
        return existing

    conversation = Conversation(
        user_a_id= current_user.id,
        user_b_id= data.friend_id,
    )
    db.add(conversation)
    try:
        db.commit()
        db.refresh(conversation)
    except IntegrityError:
        db.rollback()

        #outra requisicao pode ter criado a conversa entre o mesmo par de usuarios
        existing = find_conversation_between_users(
            db, current_user.id, data.friend_id
        )
        if existing is not None:
            response.status_code = 200
            return existing

        raise HTTPException(
            status_code=409,
            detail="conflito ao criar conversa",
        ) from exc
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="erro ao criar conversa",
        ) from exc
    return conversation

@router.get(
    "",
    response_model = list[ConversationPublic],
)
def list_conversations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return db.scalars(
        select(Conversation).where(
            or_(
                Conversation.user_a_id == current_user.id,
                Conversation.user_b_id == current_user.id,
            )
        )
        .order_by(Conversation.created_at.desc())
    ).all()
    
