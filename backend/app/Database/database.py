import os
from collections.abc import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

DATABASE_URL = os.environ["DATABASE_URL"]

engine = create_engine( ##configura a comunicação com o banco de dados
    DATABASE_URL, 
    pool_pre_ping=True, ##verifica se a conexão com o banco de dados ainda está ativa antes de usá-la
    pool_size=5,
    max_overflow=10,
)
SessionLocal = sessionmaker( ##cria uma fábrica de sessões do SQLAlchemy
    bind=engine,
    autoflush=False,
    expire_on_commit=False
)
def get_db()-> Generator[Session, None, None]: ##cria uma função geradora que fornece uma sessão do banco de dados para cada solicitação
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()