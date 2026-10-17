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

## Importer review audit persistence — 2026-10-15

- Reuse the generic `audit_log` table from the versioned schema; do not create a specialized importer-review audit table. Its compatibility was validated against the versioned schema in isolated PostgreSQL. The migration is not applied operationally and runtime code does not yet write the table.
- Migration `database/migrations/20261015_add_audit_log_idempotency_fields.sql` adds nullable `request_id uuid`, `request_payload_hash varchar(64)`, `actor_email_snapshot text`, `actor_name_snapshot text`, and `reason text`, plus a partial unique index on `(user_id, request_id)` for non-NULL request IDs. Existing generic audit rows remain valid; review writes require all five values and an authenticated non-NULL actor. No defaults, `NOT NULL`, checks, or backfill are included.
- Idempotency scope is `(user_id, request_id)`. Hash the normalized semantic payload (booking UUID, expected current mapping fields, target mapping/tour, and trimmed reason), excluding the request ID. Same key/hash returns the original event without another update/event; same key/different hash returns 409. A first no-op consumes the key with one `import_review.noop` event. A unique-index race is resolved by rollback and re-reading the existing event.
- Isolated PostgreSQL validation passed for schema compatibility, generic and review-shaped inserts, unique-key enforcement, multiple NULL request IDs, rollback, canonical hashing, idempotent retry, and refusal of same-key/different-payload requests. Hash/retry semantics were exercised by temporary validation harnesses, not runtime code.
- Event actions: `import_review.approved` for probable/unmapped → confirmed; `import_review.corrected` for confirmed-tour replacement or confirmed → review-state correction; `import_review.rejected` for probable → unmapped; `import_review.noop` for an accepted decision that already matches current state. `old_value`/`new_value` snapshot booking UUID/code, raw label, mapping status, tour UUID/name, and review flag. Actor snapshots, reason, and request fingerprint are dedicated columns; existing `created_at` is the timestamp.
- Audit entries are append-only and have no automatic purge in v1; retain through and beyond booking deletion. Any purge requires a separately approved retention/legal policy. Audit read access requires `bookings.import_review.audit.read`; writes require `bookings.import_review.approve` and authenticated user identity.
- A write transaction locks the booking `FOR UPDATE`, validates expected prior mapping fields, locks/rechecks the chosen tour as active, updates only mapping metadata and `tour_id`, and inserts the audit event atomically. Stale expected values return 409; any failure rolls back both changes.
- This checkpoint adds and validates the migration only in isolated PostgreSQL. No operational schema/data, endpoint, or runtime code was changed. The trusted issuer/key provisioning path remains an implementation prerequisite.

## Website inquiry and idempotency retention — confirmed 2026-10-17

- Delete unconverted website inquiries (`source='Website'`, status `Inquiry`) when `bookings.created_at` is older than 30 days. Any booking that advanced beyond Inquiry is converted and excluded.
- Keep website booking idempotency for 24 hours independently. Within the window, retries preserve current replay/conflict behavior; after expiry, reuse of the same key is a new request. Expired idempotency rows are pruned in bounded batches.
- Delete known booking FK dependents transactionally before deleting the booking. Delete a customer only if no booking references it; shared customers remain. Generic `audit_log` remains append-only.
- The retention script defaults to count-only preview; apply is explicit and requires a backup reference. Do not configure a scheduler against an environment until target identity, verified backup, and release approval are established. No schema change or database cleanup was performed for this decision.
- Subsequent inquiry conversation continues by email, which is outside this Manager retention workflow.
