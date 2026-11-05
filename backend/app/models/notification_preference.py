from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Integer, func
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.Database.base import Base


class NotificationPreference(Base):
    __tablename__ = "notification_preferences"

    user_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    muted: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )
    volume: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=100,
        server_default="100",
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    __table_args__ = (
        CheckConstraint(
            "volume BETWEEN 0 AND 100",
            name="ck_notification_preferences_volume",
        ),
    )


class NotificationSenderPreference(Base):
    __tablename__ = "notification_sender_preferences"

    user_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    sender_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    muted: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )
    volume_factor: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=100,
        server_default="100",
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    __table_args__ = (
        CheckConstraint(
            "volume_factor BETWEEN 0 AND 100",
            name="ck_notification_sender_preferences_volume_factor",
        ),
        CheckConstraint(
            "user_id <> sender_id",
            name="ck_notification_sender_preferences_distinct_users",
        ),
    )
