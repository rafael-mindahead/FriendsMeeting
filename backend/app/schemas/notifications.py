from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class NotificationPreferenceUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    muted: bool
    volume: int = Field(ge=0, le=100)


class NotificationSenderPreferenceUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    muted: bool
    volume_factor: int = Field(ge=0, le=100)


class NotificationSenderPreferencePublic(
    NotificationSenderPreferenceUpdate
):
    user_id: UUID


class NotificationPreferencesPublic(BaseModel):
    muted: bool
    volume: int
    senders: list[NotificationSenderPreferencePublic]
