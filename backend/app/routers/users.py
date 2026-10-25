from fastapi import APIRouter, Depends

from app.dependencies.current_user import get_current_user
from app.models.user import User
from app.schemas.user import UserPublic

router = APIRouter(
    prefix="/api/v1/users",
    tags=["Users"],
)


@router.get("/me", response_model=UserPublic)
def get_my_profile(
    current_user: User = Depends(get_current_user),
):
    return current_user
