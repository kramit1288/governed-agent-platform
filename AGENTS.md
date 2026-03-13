# AGENTS.md

This repository is built as a serious, narrow, production-style AI systems project.

The goal is not to maximize feature count.
The goal is to maximize architectural clarity, safety, traceability, and interview defensibility.

## Product scope

This repo implements a governed single-agent orchestration platform for support and ops workflows.

The system should demonstrate:

- explicit orchestration
- model routing and fallback
- guarded tool execution
- approval-gated risky actions
- traceability
- offline evals

## Important boundaries

### Orchestrator

Owns workflow intelligence and run state transitions.

### Gateway

Owns model routing, provider abstraction, and fallback policy.

### Tools

Own tool schema, permissions, and execution wrappers.

### Retrieval

Own document retrieval, filters, and citation packaging.

### Runtime

Owns minimal durable execution, retries, timeouts, and resume.

### Tracing

Owns append-only run events and trace read models.

### Evals

Owns offline evaluation and regression comparison.

## Rules for contributors and coding agents

1. Do not add multi-agent architecture in V1.
2. Do not add a custom inference platform.
3. Do not add heavy framework-driven orchestration as the core logic.
4. Keep the orchestrator explicit and easy to read.
5. Keep module boundaries clean.
6. Do not create circular package dependencies.
7. Prefer simple, testable abstractions over clever ones.
8. All risky actions must go through approval.
9. Every important orchestration step should emit a trace event.
10. New features should come with tests and docs when meaningful.

## Code quality expectations

- Prefer typed models with Pydantic.
- Prefer explicit interfaces over hidden behavior.
- Keep side effects easy to trace.
- Keep orchestration logic deterministic where practical.
- Add comments for intent, not for obvious syntax.
- Use small modules with clear responsibilities.

## Before implementing a feature

Ask:

- Does this belong in V1?
- Which package owns this?
- Does it improve product value or just add platform complexity?
- Can it be explained clearly in an interview?
- Does it need a trace event?
- Does it need an eval case?

## Out of scope for V1

- multi-agent core
- generalized workflow engine
- custom vector DB
- fine-tuning pipeline
- complex memory architecture
- Kubernetes-only deployment assumptions
- large enterprise admin surfaces

## Preferred style

This project should feel like it was built by a strong backend/platform engineer:

- explicit
- measured
- pragmatic
- safe
- testable
- observable
