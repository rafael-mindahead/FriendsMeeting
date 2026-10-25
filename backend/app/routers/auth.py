"""Public auth-facing routes delegating credential handling to authService."""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.Database.database import get_db
from app.clients.auth_service import AuthServiceClient, get_auth_service
from app.models.user import User
from app.schemas.user import UserCreate, UserPublic
from app.services.profiles import ensure_profile

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(min_length=8, max_length=128)


@router.post("/register", response_model=UserPublic, status_code=201)
def register_user(
    data: UserCreate,
    db: Session = Depends(get_db),
    auth: AuthServiceClient = Depends(get_auth_service),
):
    # Preflight local username/email conflicts before the remote registration.
    # Unique indexes in both databases remain the final arbiters.
    if db.scalar(select(User.id).where(User.email == str(data.email))) is not None:
        raise HTTPException(409, "E-mail ja cadastrado no FriendsMeeting")
    if db.scalar(select(User.id).where(User.username == data.username)) is not None:
        raise HTTPException(409, "Nome de usuario ja cadastrado")

    identity = auth.call(
        "POST", "/auth/register",
        payload={"name": data.username, "email": str(data.email), "password": data.password},
    )
    # If local persistence fails, the auth account can still be recovered
    # on the next login; we never try to delete remote accounts implicitly.
    return ensure_profile(db, identity, requested_username=data.username)


@router.post("/login", response_model=TokenResponse)
def login_user(
    data: LoginRequest,
    db: Session = Depends(get_db),
    auth: AuthServiceClient = Depends(get_auth_service),
):
    tokens = auth.call(
        "POST", "/auth/login",
        payload={"email": str(data.email), "password": data.password},
    )
    if not isinstance(tokens.get("access_token"), str):
        raise HTTPException(502, "Token invalido recebido do authService")
    identity = auth.call("GET", "/auth/me", token=tokens["access_token"])
    ensure_profile(db, identity)
    return tokens


@router.post("/refresh", response_model=TokenResponse)
def refresh_token(
    data: RefreshRequest, auth: AuthServiceClient = Depends(get_auth_service),
):
    return auth.call("POST", "/auth/refresh", payload=data.model_dump())


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout_user(
    data: RefreshRequest, auth: AuthServiceClient = Depends(get_auth_service),
):
    auth.call("POST", "/auth/logout", payload=data.model_dump())
    return None


@router.post("/forgot-password")
def forgot_password(
    data: ForgotPasswordRequest,
    auth: AuthServiceClient = Depends(get_auth_service),
):
    return auth.call("POST", "/auth/forgot-password", payload=data.model_dump(mode="json"))


@router.post("/reset-password")
def reset_password(
    data: ResetPasswordRequest,
    auth: AuthServiceClient = Depends(get_auth_service),
):
    return auth.call("POST", "/auth/reset-password", payload=data.model_dump())
