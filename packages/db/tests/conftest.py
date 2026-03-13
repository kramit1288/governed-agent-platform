"""Pytest configuration for db package tests."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

ROOT = Path(__file__).resolve().parents[3]
SRC = ROOT / "packages" / "db" / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from db.base import Base
from db.models import ApprovalRequest, EvalCase, EvalResult, EvalRun, PromptVersion, Run, RunEvent, ToolInvocation


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
