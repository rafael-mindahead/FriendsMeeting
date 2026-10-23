import secrets
import uuid
from datetime import datetime

from sqlalchemy import String, DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.Database.base import Base

def generate_friend_code()-> str:
    alphabet = "QWERTYUIOPASDFGHJKLZXCVBNM23456789"

    code = ''.join(secrets.choice(alphabet) for _ in range(8))
    return f"FM-{code}"

class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key= True,
        default=uuid.uuid4
    )
    username: Mapped[str] = mapped_column(
        String(32),
        unique=True,
        nullable=False,
        index=True
    )
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True
    )
    password_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )
    friend_code: Mapped[str] = mapped_column(
        String(11),
        unique=True,
        nullable=False,
        index=True,
        default=generate_friend_code
    )
    created_at: Mapped[datetime]= mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
