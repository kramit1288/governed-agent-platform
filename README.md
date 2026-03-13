# Governed Agent Platform

Production-style monorepo for a governed single-agent orchestration platform focused on support and ops workflows.

The repository is intentionally narrow in V1:

- single-agent only
- explicit orchestration
- approval-gated risky actions
- append-only tracing
- offline evals
- PostgreSQL plus pgvector

## Stack

- Python 3.12
- FastAPI
- Pydantic v2
- SQLAlchemy 2.0
- PostgreSQL
- pgvector
- Alembic
- pytest
- Next.js with TypeScript

## Monorepo layout

```text
apps/
  api/          FastAPI application
  console/      Next.js operator console
packages/
  shared/       Shared types and utilities
  db/           Persistence models and migrations ownership
  orchestrator/ Run state transitions and workflow control
  gateway/      Model routing and provider abstraction
  tools/        Tool schemas, permission checks, execution wrappers
  retrieval/    Retrieval interfaces and citation packaging
  runtime/      Retries, timeouts, resume semantics
  tracing/      Append-only run events and trace read models
  evals/        Offline evaluation cases and regression reports
docs/adrs/      Architecture decision records
data/seed/      Seed fixtures
scripts/        Development and maintenance scripts
```

## Getting started

1. Copy `.env.example` to `.env`.
2. Start PostgreSQL with `docker compose up -d postgres`.
3. Install backend dependencies in your preferred Python environment.
4. Run the API with `make dev-api`.
5. Run tests with `make test`.
6. Start the console with `make dev-console`.

## Current status

This bootstrap intentionally includes only:

- a minimal FastAPI app with `/health`
- one API test
- package scaffolding with docstring-only placeholders
- architecture docs and ADRs

Business logic is deliberately deferred.
