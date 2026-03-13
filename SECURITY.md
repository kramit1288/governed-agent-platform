# Security

## Principles

- risky actions require explicit approval
- tool permissions stay explicit and auditable
- traces are append-only
- secrets stay out of source control
- least privilege is the default posture

## V1 expectations

- use environment variables for secrets and connection strings
- restrict production database access by role
- log security-relevant actions through tracing
- validate all tool inputs with typed schemas
- gate side-effecting tools behind approval workflows

## Not yet implemented

This bootstrap does not yet include:

- authentication and authorization
- tenant isolation
- secret rotation
- production deployment hardening
- formal threat modeling

Those items should be addressed before production use.
