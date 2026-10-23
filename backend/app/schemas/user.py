from datetime import datetime
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    field_validator,
)

class UserCreate(BaseModel):
    username: str = Field(
        min_length = 3,
        max_length = 32,
        pattern = r"^[a-zA-Z0-9_]+$"
    )
    email: EmailStr
    password: str = Field(
        min_length = 8,
        max_length = 128
    )
    @field_validator("username")
    @classmethod
    def normalize_username(cls, value: str)->str:
        return value.lower()
    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str)->str:
        return str(value).lower()


class UserPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    username: str
    email: EmailStr
    friend_code: str
    created_at: datetime

    