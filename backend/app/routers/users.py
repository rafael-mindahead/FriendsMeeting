"""User profiles are authorized by authService, not by local JWT secrets."""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.Database.database import get_db
from app.clients.auth_service import AuthServiceClient, get_auth_service
from app.schemas.user import UserPublic
from app.services.profiles import ensure_profile

router = APIRouter(prefix="/api/v1/users", tags=["Users"])
bearer = HTTPBearer(auto_error=False)


@router.get("/me", response_model=UserPublic)
def get_my_profile(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    auth: AuthServiceClient = Depends(get_auth_service),
    db: Session = Depends(get_db),
):
    if credentials is None:
        raise HTTPException(status_code=401, detail="Token nao informado")
    identity = auth.call("GET", "/auth/me", token=credentials.credentials)
    return ensure_profile(db, identity)
