"""Session and engine helpers for the database package."""

from __future__ import annotations

import os

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker


DEFAULT_DATABASE_URL = "postgresql+psycopg://postgres:postgres@localhost:5432/governed_agent"


def get_database_url() -> str:
    """Return the configured database URL."""
    return os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL)


def create_db_engine(database_url: str | None = None, *, echo: bool = False) -> Engine:
    """Create a SQLAlchemy engine for the configured database."""
    return create_engine(database_url or get_database_url(), echo=echo, future=True)


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    """Create a typed session factory bound to the provided engine."""
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
