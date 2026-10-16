# Importer Review Approval — Operational Release Checklist

This checklist prepares the protected mapping approval endpoint for deployment. It does not authorize a production change by itself. Do not run the database steps until the operator has an approved maintenance window and a verified backup.

## Current endpoint contract

- Method and path: `POST /bookings/{booking_code}/import-review/decision`
- Permission: `bookings.import_review.approve`
- Authentication: externally issued bearer JWT; the API validates HS256 signature, configured issuer, and configured audience, then reloads the active user and role permission from PostgreSQL.
- Request body: required `expected_mapping_status`, nullable `expected_tour_id`, required `expected_needs_manual_review`, required target `mapping_status`, optional nullable `tour_id`, optional `reason`, required `confirm`, and required UUID `request_id`. Extra fields are rejected.
- Success/replay: HTTP `200`, JSON fields `booking_id`, `booking_code`, `status`, `imported_raw_tour_name`, `mapping_status`, `needs_manual_review`, `tour_id`, `tour_name`, `review_event_id`, and `replayed`.
- Error responses: `400` when explicit confirmation is false; `401` for missing/invalid bearer identity; `403` for inactive user or missing permission; `404` for a missing booking; `409` for stale/inconsistent mapping or same actor/request ID with a different payload; `422` for invalid request fields, missing/inactive canonical tour, or invalid mapping transition; `503` when JWT verifier configuration is incomplete. FastAPI's standard validation response also uses `422`.
- Request requires `request_id`, expected current mapping status/tour/review flag, target mapping status, and `confirm: true`. A mapping change requires a non-empty reason. A `confirmed` target requires an existing active canonical `tour_id`; review/unmapped targets require null `tour_id`.
- Mapping fields and the audit event are written in one caller-owned transaction. An identical retry returns the existing audit event and does not repeat the mapping callback.
- The endpoint does not change booking operational status, customer, price, payments, invoices, or the raw imported tour label.

## Release checklist — operator-owned steps

### 1. Confirm the release artifact and migration state

- Confirm the deployed application artifact contains the protected endpoint and audit helper.
- The repository has two additive SQL files, ordered by their filename date:
  1. `database/migrations/20261015_add_booking_import_review_metadata.sql`
  2. `database/migrations/20261015_add_audit_log_idempotency_fields.sql`
- The website quote snapshot/idempotency migration is `database/migrations/20261016_add_website_quote_idempotency.sql`. The staging schema verifier checks its quote snapshot and idempotency tables plus the quote expiry index; include it after the existing review, audit, and deposit migrations when validating the complete application schema.
- The approval route reads the three importer-review columns and the audit helper writes the five audit columns/index. Verify both migrations are already present in the target schema before enabling the route.
- There is no migration runner or schema-version ledger in this repository. A filename listing identifies available migration files, not which files have been applied. The release operator must inspect `information_schema.columns` and `pg_indexes` in the target environment and record the result in the deployment record. Do not infer migration state from this checklist.
- Do not edit the published migrations or apply them automatically during application startup.

### 2. Provision configuration without exposing values

Provision each setting in its correct environment using the approved secret/configuration manager:

- `DATABASE_URL`: backend connection URL for the target database.
- `THAICULTURE_DB_PASSWORD`: Compose interpolation input for the PostgreSQL container only. It is not a backend Settings field. Do not put this Compose-only key into a dotenv file loaded by backend Settings; provision backend `DATABASE_URL` separately.
- `AUTH_JWT_SECRET`: trusted HS256 verification secret, with at least 32 random bytes.
- `AUTH_JWT_ISSUER`: exact issuer configured by the trusted identity provider.
- `AUTH_JWT_AUDIENCE`: exact audience configured for this API.

Keep local development, isolated tests, staging, and production credentials and databases separate. Do not copy a real secret into a test fixture. The endpoint must remain fail-closed if any JWT verifier setting is absent or invalid. Never place values in Git, tickets, screenshots, terminal transcripts, exception output, or logs.

### 3. Safe presence and route-registration preflight

Run from a shell that has the intended environment provisioned. This prints only setting names and whether each is present; it never prints values:

```sh
python - <<'PY'
import os

for name in (
    "DATABASE_URL",
    "THAICULTURE_DB_PASSWORD",
    "AUTH_JWT_SECRET",
    "AUTH_JWT_ISSUER",
    "AUTH_JWT_AUDIENCE",
):
    print(f"{name}: {'set' if os.environ.get(name) else 'missing'}")
PY
```

This is a presence check only. Confirm issuer and audience with the identity provider; do not treat presence as validation. Before deployment, run the application's existing isolated auth/approval tests and a route-registration/import check. Never use the operational `DATABASE_URL` for tests.

### 4. Backup and rollback

- Take a PostgreSQL backup using the organization's approved backup process and credential handling. Do not place the connection URL/password in command output or process arguments. Record the backup identifier, time, and restore owner without recording credentials.
- Confirm the backup is restorable according to the normal recovery procedure before schema changes.
- Record the current application artifact and schema inspection results.
- Rollback plan: disable the approval route by redeploying the previous application artifact. Leave additive nullable columns and the partial index in place; do not drop them as an application rollback step. Restore the database backup only if data recovery is required and an authorized incident/recovery decision is made.

### 5. Apply schema changes under the approved window

- If either migration is absent, apply only the missing additive migration(s), in the order listed above, through the operator's controlled SQL deployment process.
- Verify the three booking metadata columns and five audit columns are nullable and have no unintended defaults or constraints; verify the partial unique index covers `(user_id, request_id)` only where `request_id IS NOT NULL`.
- Re-run the schema inspection. Do not run the importer or backfill as part of endpoint enablement.

### 6. Verify permission and smoke behavior

- Confirm the intended reviewer user exists and is active.
- Confirm the reviewer's assigned role has the boolean permission key `bookings.import_review.approve` enabled. Grant only to the approved reviewer role; do not enable it broadly.
- In an isolated/staging environment with synthetic bookings and canonical tours, verify: no token and invalid token return `401`; valid identity without permission returns `403`; authorized approval returns `200`; a repeated identical request returns `200` with `replayed: true`; changed expected state returns `409`; the audit event exists exactly once.
- Verify the response fields listed above and confirm booking status, raw label, customer, price, payments, and invoices are unchanged.
- Only after the staging smoke checks pass may an operator enable the route for its intended environment. Production smoke testing must use an explicitly approved test booking; do not modify a real booking just to test deployment.

### 7. Secret rotation

The previously exposed credential-like value is considered compromised. The operator must identify its service and rotate it manually at the credential authority, then update the appropriate local/Compose/backend secret stores. Rotate PostgreSQL credentials and JWT verification material independently as applicable. Coordinate JWT key rotation with token lifetime and issuer behavior. Verify the old credential is revoked; do not copy it into this checklist or a deployment record.

## Static readiness findings (2026-10-16)

- `backend/app/main.py` imports and registers `bookings.router`; the route module does not import `app.main`, so static import direction has no circular dependency.
- The approval endpoint has no explicit FastAPI `response_model`; its current JSON response contract is documented above. HTTP behavior is implemented with explicit FastAPI exceptions plus standard request validation.
- `backend/tests/test_import_review_approval.py` covers confirmed approval, a review mapping with null `tour_id`, stale update, identical retry, changed-payload conflict, audit rollback, and permission/authentication outcomes. PostgreSQL endpoint tests require a disposable local test URL and are skipped if a safe isolated URL is not configured.
- Migration files are discoverable by filename, but the repository has no automatic migration head/applied-state tracking. Operational schema state remains unverified until an authorized operator inspects the target DB.

## Isolated staging validation (2026-10-16)

- Started a dedicated PostgreSQL 16 Compose project on localhost port `55441`, with its own named volume and network. Applied `database/init/001_schema.sql`, then the importer-review metadata migration and audit idempotency migration to the isolated test databases only.
- Verified all three booking metadata fields and all five audit idempotency/actor/reason fields exist and are nullable. Verified the partial unique index `uq_audit_log_user_request_id` on `(user_id, request_id)` where `request_id IS NOT NULL`.
- Created a custom-format PostgreSQL backup before running mutable tests; `pg_restore --list` successfully read its archive catalog.
- Tests passed: 14 approval PostgreSQL tests, 7 audit helper tests (including PostgreSQL transaction/idempotency tests), 10 auth tests, and 1 booking visibility test. Total: 32 passed, 0 failed, 0 skipped.
- The approval test suite exercised missing/invalid tokens, invalid issuer/audience, missing permission, valid approval, missing booking, missing/inactive tour, stale state, identical and concurrent retry, changed payload conflict, and audit failure rollback. It verified the raw label and operational booking status remained unchanged and update/audit writes were atomic.
- The five operator settings were absent from the current process environment. This check did not inspect an external secret manager. No operator credentials were used.
- Removed the staging container, named volume, network, backup, and temporary Compose file. No operational database or existing application stack was accessed.

## Website integration staging readiness (2026-10-16)

- Provision `WEBSITE_INTEGRATION_ENABLED=false` by default. Set it to `true` only for an explicitly approved staging validation; production remains disabled until a separate release decision.
- Staging uses a same-origin reverse proxy for `/api/website/*`. The proxy must forward those paths to the Manager backend without rewriting request bodies, response status codes, or the `Idempotency-Key` header. This path does not require cross-origin CORS.
- Set `CORS_ALLOWED_ORIGINS` empty for same-origin website traffic. If the Manager staff UI is served from a separate origin, list only its exact trusted origins; wildcard origins are rejected.
- Apply/verify `20261016_add_website_quote_idempotency.sql` only in the isolated staging database after the usual backup check. `scripts/staging/verify_migrations.py` verifies this migration's columns and `idx_website_quote_previews_expires_at` along with the review, audit, and deposit schema.
- Rollback by disabling `WEBSITE_INTEGRATION_ENABLED` and removing/disabling the `/api/website/*` proxy route, then revert the application artifact if needed. Keep additive tables and submitted Inquiry records; do not drop schema or business data as an automatic rollback.
- This is a provisioning/readiness plan only. It does not mean staging has been started or deployed.
