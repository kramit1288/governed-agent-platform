# ADR 003: Approval-Gated Actions

## Status

Accepted

## Decision

All risky side-effecting actions require explicit approval before execution.

## Rationale

- reduces operational risk
- creates a clear human-in-the-loop boundary
- improves auditability
- supports trace-based review of decisions

## Consequences

Tools must classify risk and integrate with the approval flow rather than bypass it.
