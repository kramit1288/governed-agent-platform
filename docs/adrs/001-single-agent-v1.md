# ADR 001: Single-Agent V1

## Status

Accepted

## Decision

V1 will implement a single-agent architecture only.

## Rationale

- keeps the orchestrator explicit
- reduces debugging and evaluation complexity
- avoids premature coordination abstractions
- is easier to explain in an interview setting

## Consequences

Future extensibility seams may exist, but no multi-agent core behavior is part of V1.
