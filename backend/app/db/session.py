import os
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Resolve relative to the backend package (not the process's cwd) so the
# database lands in the same place regardless of where uvicorn/alembic is
# launched from. Override with DATABASE_URL for Postgres/MySQL/etc.
_BACKEND_ROOT = Path(__file__).resolve().parents[2]
DATABASE_URL = os.getenv(
    "DATABASE_URL", f"sqlite:///{_BACKEND_ROOT / 'organization.db'}"
)

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()