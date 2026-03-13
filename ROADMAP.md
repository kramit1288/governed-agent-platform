# Roadmap

## Phase 0: Bootstrap

- establish monorepo layout
- define architecture boundaries
- add API and console skeletons
- add PostgreSQL and pgvector development setup
- add ADRs and contributor guidance

## Phase 1: Core governed run flow

- define run, approval, and trace domain models
- add explicit orchestrator state transitions
- add trace event emission interfaces
- add approval-gated tool execution path
- add minimal retrieval interface and citation envelope

## Phase 2: Gateway and persistence

- implement provider-agnostic model gateway
- add model routing and fallback policy
- add SQLAlchemy models and Alembic migrations
- add repository interfaces with explicit ownership boundaries

## Phase 3: Console and operations

- add run list and run detail views
- add approval review and decision flow
- add trace timeline views
- add eval report surfaces

## Phase 4: Evaluation and hardening

- add offline eval fixtures and comparison tooling
- add regression baselines
- add failure injection for runtime paths
- add security and operational hardening
