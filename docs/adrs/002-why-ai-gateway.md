# ADR 002: Why an AI Gateway

## Status

Accepted

## Decision

Model access is isolated behind a dedicated gateway package.

## Rationale

- centralizes routing and fallback policy
- isolates provider-specific code
- keeps orchestrator logic provider-agnostic
- improves testability and traceability

## Consequences

The gateway owns model normalization and provider boundaries, not workflow logic.
