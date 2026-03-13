# ADR 006: Python Stack Decision

## Status

Accepted

## Decision

The backend stack is Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2.0, PostgreSQL, pgvector, Alembic, and pytest.

## Rationale

- strong ecosystem fit for typed backend services
- good balance of speed and readability
- broad familiarity for review and interviews
- pragmatic support for APIs, data access, and testing

## Consequences

The repository should avoid introducing competing backend stacks without a clear architectural reason.
