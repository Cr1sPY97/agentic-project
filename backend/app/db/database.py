from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from typing import Generator
from app.core.config import settings

db_uri = settings.SQLALCHEMY_DATABASE_URI

connect_args = {}
if db_uri.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(
    db_uri,
    connect_args=connect_args,
    pool_pre_ping=True if not db_uri.startswith("sqlite") else False,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db() -> Generator:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Convenience helper to initialize database tables."""
    Base.metadata.create_all(bind=engine)
