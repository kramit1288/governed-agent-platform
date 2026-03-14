# AGENTS.md

This repository is built as a serious, narrow, production-style AI systems project.

The goal is not to maximize feature count.
The goal is to maximize architectural clarity, safety, traceability, and interview defensibility.
All changes should optimize for architectural clarity, safety, traceability, and interview-defensible design.

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

## Engineering standards

This repository should feel like a serious production-style systems project, not a quick AI demo.

### General quality bar

- Prefer explicit, readable architecture over clever abstractions.
- Keep module boundaries strict and easy to explain in an interview.
- Optimize for correctness, debuggability, and maintainability first.
- Do not add speculative platform features that are not required for V1.
- Do not introduce framework magic into core orchestration logic.

### Language and typing

- Target Python 3.12.
- Use type hints everywhere for non-trivial functions, methods, and public interfaces.
- Prefer explicit domain models and typed contracts over loose dictionaries.
- Use Pydantic v2 for API contracts, tool input/output validation, and other external boundaries.
- Keep shared types in `packages/shared` only when they are truly shared.

### Architecture and package boundaries

- `orchestrator` owns workflow intelligence and run state transitions.
- `gateway` owns provider abstraction, model routing, fallback, and usage metadata.
- `tools` owns tool schemas, permissions, and execution wrappers.
- `retrieval` owns retrieval, filters, and citation packaging.
- `runtime` owns minimal durable execution, retries, timeouts, and resume behavior.
- `tracing` owns append-only execution history and trace read models.
- `evals` owns offline evaluation and regression comparison.
- `db` owns persistence models, repositories, and migrations only.
- Do not move business logic into `db` repositories.
- Do not let `apps/*` accumulate domain logic.
- Avoid circular dependencies completely.

### Orchestration rules

- Keep the orchestrator explicit and interview-defensible.
- Use a visible state machine for run lifecycle transitions.
- Prefer deterministic step transitions where practical.
- Do not hide core workflow behavior behind agent frameworks.
- V1 is single-agent only.
- Do not introduce multi-agent core behavior in V1.
- Risky actions must always go through approval checkpoints.

### Tooling rules

- Every tool must have:
  - a clear name
  - a description
  - an input schema
  - a risk classification
  - a `requires_approval` flag
  - a timeout value
- Read-only tools may execute directly.
- Risky tools must return a preview-style result and wait for approval.
- Do not execute irreversible side effects in V1.
- Enforce tenant context in every tool.
- Keep tool execution wrapped with clear error handling and standardized result objects.

### AI Gateway rules

- The orchestrator must not call provider SDKs directly.
- All model access goes through the AI Gateway.
- Routing policy must be explicit and easy to inspect.
- Provider-specific logic must stay isolated in provider adapter modules.
- Record route decisions with enough detail to explain:
  - selected provider/model
  - reason
  - fallback behavior
  - usage/cost metadata if available

### Persistence rules

- Use SQLAlchemy 2.0 style.
- Keep DB models explicit and simple.
- Model `RunEvent` as append-only.
- Use repositories for persistence access, not for orchestration logic.
- Use Alembic for schema migrations.
- Keep schema evolution readable and intentional.

### Error handling

- Prefer domain-specific exceptions where useful.
- Do not swallow exceptions silently.
- Fail with useful context.
- Distinguish retryable from terminal failures where it matters.
- Make invalid state transitions explicit errors.

### Tracing and observability

- Every important orchestration step should emit a trace/run event.
- Trace events must be append-only.
- Keep event payloads compact but meaningful.
- A run should be explainable from trace data alone.
- Record enough detail to debug:
  - model selection
  - retrieval completion
  - tool calls
  - approval requests/resolution
  - final completion or failure

### Evals

- Evals are first-class in V1.
- Add or update eval cases when behavior materially changes.
- Prefer small, readable eval cases over large benchmark-like suites.
- Regression visibility matters more than fancy scoring.
- Keep scoring functions understandable.

### Testing

- Every non-trivial behavior change should include tests.
- Add unit tests for orchestration transitions, approval flow, routing policy, tool validation, and repositories where relevant.
- Add integration tests when module boundaries interact in important ways.
- Keep tests deterministic.
- Do not rely on external provider calls in tests.
- Use mock providers and seeded local data.

### Code style

- Prefer small functions with clear names.
- Use docstrings/comments for intent, not obvious syntax.
- Avoid deeply nested control flow when a clearer structure is possible.
- Prefer explicit enums and named concepts over magic strings.
- Keep files cohesive; split when responsibilities start to blur.

### Documentation

- Update docs when architecture or important interfaces change.
- Keep ADRs concise and decision-focused.
- If a tradeoff is important enough to discuss in an interview, it is important enough to document.
- Do not leave major design choices undocumented.

### Validation before finishing a task

Before marking work complete, always:

1. run tests
2. run lint/format checks
3. run type checks if configured
4. confirm package boundaries were not violated
5. summarize:
   - what changed
   - what assumptions were made
   - what was intentionally deferred

### V1 guardrails

Do not add these in V1 unless explicitly requested:

- multi-agent core
- custom inference serving platform
- generalized workflow engine
- custom vector database
- fine-tuning/training pipeline
- complex long-term memory system
- speculative enterprise admin/billing surfaces

When in doubt, choose the simpler design that is easier to explain, test, and ship.