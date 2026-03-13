# Contributing

## Development principles

- keep the architecture explicit
- preserve package ownership boundaries
- prefer simple abstractions over framework-heavy indirection
- add tests with behavior changes
- update docs when decisions materially change

## Change checklist

Before opening a change:

- confirm the work belongs in V1
- identify the owning package
- avoid circular dependencies
- add or update trace events where needed
- add or update eval coverage when behavior changes

## Local workflow

- use Python 3.12
- use Node.js 20 or newer for the console
- start PostgreSQL with `docker compose up -d postgres`
- run API tests with `make test`

## ADRs

Architectural decisions that affect boundaries or platform direction should be recorded under `docs/adrs/`.
