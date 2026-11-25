from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.notification_preference import (
    NotificationPreference,
    NotificationSenderPreference,
)
from app.models.user import User
from app.schemas.notifications import (
    NotificationPreferenceUpdate,
    NotificationSenderPreferenceUpdate,
)


def load_preferences(db: Session, user_id: UUID) -> dict:
    global_preference = db.get(NotificationPreference, user_id)
    sender_preferences = db.scalars(
        select(NotificationSenderPreference)
        .where(NotificationSenderPreference.user_id == user_id)
        .order_by(NotificationSenderPreference.sender_id)
    ).all()

    return {
        "muted": global_preference.muted if global_preference else False,
        "volume": global_preference.volume if global_preference else 100,
        "senders": [
            {
                "user_id": preference.sender_id,
                "muted": preference.muted,
                "volume_factor": preference.volume_factor,
            }
            for preference in sender_preferences
        ],
    }


def save_global_preferences(
    db: Session,
    user_id: UUID,
    update: NotificationPreferenceUpdate,
) -> dict:
    preference = db.get(NotificationPreference, user_id)
    if preference is None:
        preference = NotificationPreference(user_id=user_id)
        db.add(preference)

    preference.muted = update.muted
    preference.volume = update.volume
    _commit(db, "Não foi possível salvar as preferências de notificação")
    return load_preferences(db, user_id)


def save_sender_preferences(
    db: Session,
    user_id: UUID,
    sender_id: UUID,
    update: NotificationSenderPreferenceUpdate,
) -> dict:
    if sender_id == user_id:
        raise HTTPException(
            status_code=400,
            detail="Não é possível configurar notificações para si mesmo",
        )
    if db.get(User, sender_id) is None:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    preference = db.get(
        NotificationSenderPreference,
        (user_id, sender_id),
    )
    if preference is None:
        preference = NotificationSenderPreference(
            user_id=user_id,
            sender_id=sender_id,
        )
        db.add(preference)

    preference.muted = update.muted
    preference.volume_factor = update.volume_factor
    _commit(db, "Não foi possível salvar a preferência deste remetente")
    return load_preferences(db, user_id)


def delete_sender_preferences(
    db: Session,
    user_id: UUID,
    sender_id: UUID,
) -> dict:
    preference = db.get(
        NotificationSenderPreference,
        (user_id, sender_id),
    )
    if preference is not None:
        db.delete(preference)
        _commit(db, "Não foi possível remover a preferência deste remetente")
    return load_preferences(db, user_id)


def _commit(db: Session, message: str) -> None:
    try:
        db.commit()
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(status_code=503, detail=message) from exc
