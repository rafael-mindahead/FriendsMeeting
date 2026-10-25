from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from app.routers.auth import router as auth_router
from app.routers.users import router as users_router

from app.Database.database import get_db
from app.routers.friends import router as friends_router

app = FastAPI(
    title = "FriendsMeeting API",
    description = "API de gerenciamento de usuarios e amizades",
    version = "0.1.0"
)
app.include_router(auth_router)
app.include_router(users_router)
app.include_router(friends_router)

@app.get("/api/v1/health")
def health_check():
    return {
        "status": "ok",
        "service" : "FriendsMeeting",
        "version" : "0.1.0"
    }

@app.get("/api/v1/health/database")
def database_health(db: Session = Depends(get_db)):
    try:
        result = db.execute(text("SELECT 1"))
        if result.scalar_one() != 1:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="falha na verificaçao do banco"
            )
        return {
            "status": "ok",
            "database": "PostgreSQL",
            "connection": "healthy"
        }
    except SQLAlchemyError:
        raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="Banco de dados indisponivel"
        )