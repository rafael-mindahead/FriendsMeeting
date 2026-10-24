from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.Database.database import get_db
from app.models.user import User, generate_friend_code
from app.schemas.user import UserCreate, UserPublic
from app.security.password import hash_password

router = APIRouter(
    prefix="/api/v1/auth",
    tags=["Authentication"]
)
@router.post("/register", response_model=UserPublic,status_code=status.HTTP_201_CREATED)
def register_user(
    data: UserCreate,
    db: Session = Depends(get_db)
):
    if db.scalar(select(User.id).where(User.email == data.email)) is not None: ##verifica se o email ja existe no banco de dados
        raise HTTPException(
            status_code=409,
            detail="E-mail ja cadastrado"
        )

    if db.scalar(select(User.id).where(User.username == data.username)) is not None: ##verifica se o username ja existe no banco de dados
        raise HTTPException(
            status_code=409,
            detail="Nome de usuario ja cadastrado"
        )
    password_hash = hash_password(data.password) ##nao deixa a senha em texto puro, faz o hash da senha

    for _ in range(5):
        user = User(
            username=data.username,
            email=data.email,
            password_hash=password_hash,
            friend_code=generate_friend_code()
        )
        db.add(user)
        try:
            db.commit()
            db.refresh(user)
            return user
        except IntegrityError as exc:
            db.rollback()

            diagnostic = getattr(exc.orig, "diag", None)
            constraint_name = getattr(diagnostic, "constraint_name", None)
            if constraint_name == "ix_users_friend_code":
                continue
            if constraint_name == "ix_users_email":
                raise HTTPException(
                    status_code=409,
                    detail="E-mail ja cadastrado"
                )
            if constraint_name == "ix_users_username":
                raise HTTPException(
                    status_code=409,
                    detail="Nome de usuario ja cadastrado"
                )
            raise

        raise HTTPException(
            status_code=503,
            detail="nao foi possivel criar o usuario, tente novamente mais tarde"
        )
    

    

    
