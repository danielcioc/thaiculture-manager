# ThaiCulture Manager — Decisions

## Continuity decision
Project continuity must not depend on assistant memory alone.
Project state must be stored inside repository/project files.

## Documentation rule
At the end of each meaningful work session, update:
- `docs/PROJECT_STATE.md`
- `docs/NEXT_STEPS.md`
- `docs/SESSION_LOG.md`
- `docs/HANDOFF.md`
- `docs/DECISIONS.md` only when decisions change

## Product understanding
ThaiCulture Manager is an internal operations dashboard, not just a schema experiment.

## Technical understanding
The current local architecture is:
- Docker Compose
- PostgreSQL
- FastAPI
- React/Vite frontend

## Validation model decision
Continuity must track both:
- the original seeded demo flow centered on `TCT-2026-000001`
- the imported bookings validation flow centered on real imported records such as `IMP-20251218-ALEXIS-001`

## Recovery rule
When starting a new session:
1. Read `docs/PROJECT_STATE.md`
2. Read `docs/NEXT_STEPS.md`
3. Read the latest section in `docs/SESSION_LOG.md`
4. Read `docs/HANDOFF.md`
5. Only then inspect code

## Current checkpoint decision
`IMP-20251218-ALEXIS-001` is now the verified paid booking checkpoint and should remain the reference case until the importer is repaired.

## Booking financial contract v1 — confirmed 2026-10-15

- `requested_amount` is the sum of payment rows with status `Paid` and `Pending`; it does not represent a proforma request amount because the current schema has no proforma requested-amount model.
- A positive confirmed payment below the booking selling price yields `partiallypaid`.
- Confirmed payments covering the selling price yield `paid`.
- With no confirmed payment, one or more `Pending` payment rows yield `depositrequested`.
- With no confirmed or Pending payment, the booking financial status is `unpaid`.
- Proforma generation and mandatory full payment at least 48 hours before a tour remain outside the delivered task.
- Dashboard KPI semantics and existing pricing formulas are not changed by this financial-contract decision.

## Server-side authentication foundation — 2026-10-15

- Protected dependencies validate externally issued JWTs using HS256 and require configured secret, issuer, and audience. No login/token-issuance route or development identity bypass is provided.
- `roles.permissions` uses a JSON object mapping permission keys to booleans; only the literal value `true` grants a permission. No role-permission fixtures existed in the repository to establish a prior data format.
- The user identity is the JWT `sub`, resolved against `users` on every request. Active state and current role permissions are read from PostgreSQL rather than trusted from token claims.
- Missing or invalid credentials and unknown users return 401; inactive users and missing permissions return 403. Missing verifier configuration fails closed with 503.
- The auth dependency is opt-in and has not been attached to existing routes. Before a write endpoint uses it, a trusted issuer/key provisioning path and route-level authorization must be configured and verified.
- No operational database was accessed. Tests use mocked database connections.
