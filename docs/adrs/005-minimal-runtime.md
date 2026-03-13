# ADR 005: Minimal Runtime

## Status

Accepted

## Decision

V1 uses a minimal runtime focused on retries, timeouts, waiting, and resume.

## Rationale

- avoids importing a generalized workflow engine
- preserves explicit orchestration logic
- keeps failure behavior easier to reason about
- aligns with the narrow V1 scope

## Consequences

Runtime abstractions should stay small and operationally focused.
