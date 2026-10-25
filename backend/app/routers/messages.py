from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.Database.database import get_db
from app.dependencies.current_user import get_current_user
from app.models.conversation import Conversation
from app.models.message import Message
from app.models.user import User
from app.routers.conversations import ConversationPublic

router = APIRouter(
    prefix="/api/v1/conversations",
    tags=["Messages"],
)
class MessageCreate(BaseModel):
    body: str = Field(min_length=1, max_length=1000)

    @field_validator("body")
    @classmethod
    def validate_body(cls, value: str):
        if not value.strip():
            raise ValueError("A mensagem nao pode estar vazia")
        return value

class MessagePublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    conversation_id: UUID
    sender_id: UUID
    body: str
    created_at: datetime


def get_authorized_conversation(
        conversation_id: UUID,
        db: Session,
        current_user: User,
)->Conversation:
        conversation = db.get(Conversation, conversation_id)

        if conversation is None:
            raise HTTPException(
                status_code=404,
                detail="conversa nao encontrada"
            )
        if current_user.id not in (conversation.user_a_id, conversation.user_b_id):
            raise HTTPException(
                status_code=404,
                detail="conversa nao encontrada"
            )
        return conversation

@router.get(
    "/{conversation_id}",
    response_model = ConversationPublic,
)
def get_conversation(
    conversation_id: UUID,\
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
 ):
    return get_authorized_conversation(conversation_id, db, current_user)


@router.post(
    "/{conversation_id}/messages",
    response_model= MessagePublic,
    status_code=201,
)
def send_message(
    conversation_id: UUID,
    data: MessageCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    conversation = get_authorized_conversation(
        conversation_id, db, current_user
    )

    message = Message(
        conversation_id=conversation.id,
        sender_id=current_user.id,
        body=data.body,
    )

    db.add(message)

    try:
        db.commit()
        db.refresh(message)
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=503,
            detail="Erro ao salvar mensagem",
        ) from exc

    return message


@router.get(
    "/{conversation_id}/messages",
    response_model=list[MessagePublic],
)
def list_messages(
    conversation_id: UUID,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    conversation = get_authorized_conversation(
        conversation_id, db, current_user
    )

    return db.scalars(
        select(Message)
        .where(Message.conversation_id == conversation.id)
        .order_by(
            Message.created_at.desc(),
            Message.id.desc(),
        )
        .offset(offset)
        .limit(limit)
    ).all()
