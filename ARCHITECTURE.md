# Architecture

## Overview

Governed Agent Platform is a production-style single-agent system with explicit orchestration, model routing, guarded tool use, approval checkpoints, traceability, and offline evals.

V1 is intentionally narrow: a support and ops copilot for grounded question answering and approval-gated actions.

## System shape

```text
Client -> API -> Orchestrator -> Retrieval / Tools -> Gateway -> Model Provider
                          \-> Runtime
                          \-> Tracing
                          \-> DB
                          \-> Evals
```

## Ownership boundaries

### API

Owns HTTP transport, dependency wiring, and application-facing endpoints.

### Orchestrator

Owns the explicit run state machine and workflow decisions.

### Gateway

Owns provider abstraction, routing policy, fallback policy, and normalized model responses.

### Tools

Own tool schemas, permission checks, execution wrappers, and approval classification.

### Retrieval

Owns document lookup, metadata filters, and citation packaging.

### Runtime

Owns retries, timeouts, waits, and resume semantics for interrupted runs.

### Tracing

Owns append-only event capture and trace read models.

### Evals

Owns offline evaluation cases, scoring, and regression reporting.

### DB

Owns persistence models, migrations, and storage integration points.

## Run lifecycle

The intended V1 run lifecycle is:

1. `PENDING`
2. `IN_PROGRESS`
3. `WAITING_FOR_APPROVAL` when a risky action is proposed
4. `COMPLETED` or `FAILED`

Every important transition emits a trace event.

## Risk model

Tooling is split into:

- read-only actions
- approval-gated risky actions

Risky actions must not execute directly. They create an approval artifact, wait for a decision, and resume only after resolution.

## Storage

PostgreSQL is the primary system of record.

It is expected to store:

- runs
- run events
- approvals
- tool invocations
- prompt versions
- eval cases and results

`pgvector` is used for retrieval embeddings. V1 does not introduce a custom vector database.

## Non-goals

V1 explicitly avoids:

- multi-agent core behavior
- generalized workflow engines
- custom inference platforms
- custom vector stores
- deep business logic during bootstrap

These exclusions keep the design explainable, testable, and interview-defensible.
