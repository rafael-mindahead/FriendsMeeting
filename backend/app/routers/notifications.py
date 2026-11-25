from uuid import UUID

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.Database.database import get_db
from app.dependencies.current_user import get_current_user
from app.models.user import User
from app.schemas.notifications import (
    NotificationPreferenceUpdate,
    NotificationPreferencesPublic,
    NotificationSenderPreferenceUpdate,
)
from app.services.notification_preferences import (
    delete_sender_preferences,
    load_preferences,
    save_global_preferences,
    save_sender_preferences,
)

router = APIRouter(
    prefix="/api/v1/notifications",
    tags=["Notifications"],
)


@router.get("/preferences", response_model=NotificationPreferencesPublic)
def get_notification_preferences(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return load_preferences(db, current_user.id)


@router.put("/preferences", response_model=NotificationPreferencesPublic)
def update_notification_preferences(
    data: NotificationPreferenceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return save_global_preferences(db, current_user.id, data)


@router.put(
    "/preferences/senders/{sender_id}",
    response_model=NotificationPreferencesPublic,
)
def update_sender_notification_preferences(
    sender_id: UUID,
    data: NotificationSenderPreferenceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return save_sender_preferences(
        db,
        current_user.id,
        sender_id,
        data,
    )


@router.delete(
    "/preferences/senders/{sender_id}",
    response_model=NotificationPreferencesPublic,
)
def reset_sender_notification_preferences(
    sender_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return delete_sender_preferences(db, current_user.id, sender_id)
