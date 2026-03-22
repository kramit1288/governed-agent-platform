"""Pytest configuration for orchestrator tests."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

ROOT = Path(__file__).resolve().parents[3]
for package in ("orchestrator", "tracing", "db", "runtime"):
    src = ROOT / "packages" / package / "src"
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))

from db.base import Base


@pytest.fixture()
def session() -> Session:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)

    with Session(engine) as db_session:
        yield db_session
        db_session.rollback()
