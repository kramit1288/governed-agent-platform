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

## Demo flow

For the end-to-end V1 demo:

1. Start the API and console.
2. Open the console home page and submit a run such as `Summarize ticket T-100 for me.`
3. Open the run detail page to inspect status, output, and the append-only trace timeline.
4. Try a risky request such as `Draft a refund request for customer C-100 on ticket T-100 for 42.50.`
5. Open the approval page, approve or reject the draft, and then return to the run detail page to inspect the resumed outcome.
6. Trigger the offline eval suite from the home page and open the report detail page for pass/fail and regression summary data.

## Database foundation

Phase 2 establishes the schema foundation in `packages/db` for:

- runs and append-only run events
- tool invocations and approval requests
- prompt version storage
- eval cases, eval runs, and eval results

Repositories in this package stay intentionally small and persistence-only. Orchestration logic, approval policy, and business workflows remain outside the db layer.

## Orchestrator lifecycle

Phase 3 adds the explicit single-agent lifecycle skeleton in `packages/orchestrator` with:

- a visible run state machine
- deterministic step ordering
- approval pause and resume handling
- placeholder collaborator protocols for gateway, retrieval, tools, tracing, and runtime hooks

The flow is deliberately narrow and testable. It is our own orchestration code, not a framework-managed workflow graph.

## Current status

This bootstrap currently includes:

- a demoable FastAPI app with run, approval, trace, and eval endpoints
- initial PostgreSQL schema models and Alembic migration
- focused repository methods for runs, approvals, and eval storage
- pgvector-backed retrieval chunking, citations, and deterministic seed ingestion
- explicit orchestrator state machine and lifecycle skeleton
- a minimal Next.js operator console for runs, approvals, traces, and eval reports
- API, db, and orchestrator pytest coverage
- architecture docs and ADRs
