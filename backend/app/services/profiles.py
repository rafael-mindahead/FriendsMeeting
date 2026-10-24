"""Keep FriendsMeeting domain profiles linked to external authentication."""
import re
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.models.user import User, generate_friend_code


def _username_for(identity: dict, auth_id: int) -> str:
    raw = str(identity.get("name", "user")).lower()
    safe = re.sub(r"[^a-z0-9_]", "_", raw).strip("_") or "user"
    suffix = f"_{auth_id}"
    return (safe[:32 - len(suffix)] + suffix)[:32]


def ensure_profile(
    db: Session, identity: dict, *, requested_username: str | None = None,
) -> User:
    """Reconcile authService identity with FriendsMeeting's UUID profile.

    Never silently link a legacy local account solely by matching email.
    """
    external_id = identity.get("id")
    email = identity.get("email")
    if type(external_id) is not int or external_id <= 0 or not isinstance(email, str):
        raise HTTPException(502, "Identidade invalida recebida do authService")
    email = email.lower().strip()

    existing = db.scalar(select(User).where(User.auth_user_id == external_id))
    if existing is not None:
        return existing

    username = requested_username or _username_for(identity, external_id)

    if db.scalar(select(User.id).where(User.email == email)) is not None:
        raise HTTPException(409, "Email ja associado a um perfil local; migracao necessaria")
    if db.scalar(select(User.id).where(User.username == username)) is not None:
        raise HTTPException(409, "Nome de usuario ja utilizado")

    for _ in range(5):
        profile = User(
            auth_user_id=external_id,
            username=username,
            email=email,
            password_hash=None,
            friend_code=generate_friend_code(),
        )
        db.add(profile)
        try:
            db.commit()
            db.refresh(profile)
            return profile
        except IntegrityError as exc:
            db.rollback()
            constraint = getattr(getattr(exc.orig, "diag", None), "constraint_name", None)
            if constraint == "ix_users_friend_code":
                continue
            if constraint == "ix_users_auth_user_id":
                same = db.scalar(select(User).where(User.auth_user_id == external_id))
                if same is not None:
                    return same
            raise HTTPException(409, "Perfil ja cadastrado ou em conflito") from exc
        except SQLAlchemyError as exc:
            db.rollback()
            raise HTTPException(503, "Nao foi possivel persistir o perfil") from exc

    raise HTTPException(503, "Nao foi possivel gerar um codigo de amizade")
