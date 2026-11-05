from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select

from app.Database.database import SessionLocal
from app.models.conversation import Conversation
from app.models.message import Message


def _update_message_status(
    message_id: UUID,
    recipient_id: UUID,
    conversation_id: UUID,
    *,
    mark_read: bool,
) -> dict[str, str | None] | None:
    with SessionLocal() as db:
        message = db.scalar(
            select(Message)
            .where(Message.id == message_id)
            .with_for_update()
        )
        if message is None:
            return None

        conversation = db.get(Conversation, message.conversation_id)
        if (
            conversation is None
            or conversation.id != conversation_id
            or recipient_id == message.sender_id
            or recipient_id not in (
                conversation.user_a_id,
                conversation.user_b_id,
            )
        ):
            return None

        now = datetime.now(timezone.utc)
        if message.delivered_at is None:
            message.delivered_at = now
        if mark_read and message.read_at is None:
            message.read_at = now

        db.commit()

        return {
            "message_id": str(message.id),
            "conversation_id": str(message.conversation_id),
            "sender_id": str(message.sender_id),
            "delivered_at": message.delivered_at.isoformat(),
            "read_at": (
                message.read_at.isoformat()
                if message.read_at is not None
                else None
            ),
        }


def mark_message_delivered(
    message_id: UUID,
    recipient_id: UUID,
    conversation_id: UUID,
) -> dict[str, str | None] | None:
    return _update_message_status(
        message_id,
        recipient_id,
        conversation_id,
        mark_read=False,
    )


def mark_message_read(
    message_id: UUID,
    recipient_id: UUID,
    conversation_id: UUID,
) -> dict[str, str | None] | None:
    return _update_message_status(
        message_id,
        recipient_id,
        conversation_id,
        mark_read=True,
    )