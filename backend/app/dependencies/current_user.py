from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.Database.database import get_db
from app.clients.auth_service import AuthServiceClient, get_auth_service
from app.models.user import User
from app.services.profiles import ensure_profile

bearer = HTTPBearer(auto_error=False)


def get_current_user(
        credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
        db: Session = Depends(get_db),
        auth: AuthServiceClient = Depends(get_auth_service)
)-> User:
    if credentials is None:
        raise HTTPException(
            status_code=401,
            detail="Token de autenticacao obrigatorio",
            headers={"WWW-Authenticate": "Bearer"},
        )
    identity = auth.call(
        "GET",
        "/auth/me",
        token=credentials.credentials,
    )
    return ensure_profile(db, identity)