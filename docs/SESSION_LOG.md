# ThaiCulture Manager — Session Log

## 2026-10-16 protected importer review approval endpoint

### What changed

- Added `POST /bookings/{booking_code}/import-review/decision`, protected by the existing JWT dependency and permission `bookings.import_review.approve`.
- Supports documented transitions among `confirmed`, `probable_manual_review`, and `unmapped`, including approval, probable-to-unmapped rejection, and corrections. It requires explicit confirmation, expected current mapping fields, and a UUID `request_id`; state-changing decisions require a reason.
- Locks the booking row and validates the expected mapping snapshot. A confirmed mapping requires an existing active canonical tour locked for share. Review/unmapped targets store `tour_id = NULL`.
- Updates only `mapping_status`, `tour_id`, and `needs_manual_review`; it preserves `imported_raw_tour_name` and operational booking status.
- Uses the existing caller-transaction audit helper. Booking update and audit insert are atomic; identical retries return the existing event and a reused actor/request ID with a different payload returns 409.
- No frontend, migration, global resolver, booking status, payment, or operational database changes were made. The published audit migration remains unapplied operationally.

### Verification

- Fourteen approval endpoint tests passed against a dedicated temporary PostgreSQL instance using synthetic fixtures. Coverage includes success, missing booking, missing/inactive tour, stale update, permission binding/denial, missing/invalid token, invalid issuer/audience, required request ID and explicit confirmation, probable-to-unmapped, atomic audit, audit failure rollback, sequential/concurrent idempotent retry, and payload conflict.
- Ten auth tests and the booking review visibility test passed; auth tests cover missing/invalid identity, invalid issuer/audience, and permission rejection using mocked connections.
- `compileall` passed. Final `git diff --check` is run before commit.
- The temporary PostgreSQL container, named volume, Compose network, and temporary fixture files were removed. The operational database was not accessed.

### Deployment blockers and security note

- Do not use the endpoint operationally until the additive audit migration is separately authorized/applied and trusted JWT settings are provisioned.
- Existing import-script DB URL fallbacks look placeholder-like/local, but may be used if `DATABASE_URL` is absent. Values are intentionally omitted; credential/configuration cleanup remains separate and Git history was not rewritten.

## 2026-10-16 transactional audit helper and idempotency

- Added `backend/app/audit.py` with deterministic UTF-8 compact/sorted JSON canonicalization, UUID normalization, trimmed reason, and lowercase SHA-256 request hashing. `request_id` is excluded from the hash.
- Added `run_idempotent_audit_event`, which uses the caller's PostgreSQL connection, obtains a transaction-scoped advisory lock for `(user_id, request_id)`, returns the existing audit event for a same-hash retry, and raises `AuditIdempotencyConflict` when the same actor/key has a different hash. For a new request it runs the supplied business callback and inserts the audit row in the same caller-owned transaction. It never commits, rolls back, or closes the connection; callback and database errors propagate.
- Added isolated tests for canonical hash equivalence/difference, first write, same-key retry, conflicting payload, rollback after both booking and audit writes, callback error propagation, and transaction ownership.
- All 7 tests passed against a temporary PostgreSQL 16 test container using the published audit migration. Container, volume, network, and schema fixture were removed.
- No operational database was accessed. No migration, endpoint, frontend, booking mapping/status, payment behavior, or deduplication was changed.

# 2026-10-15 isolated audit_log compatibility validation

- Added `database/migrations/20261015_add_audit_log_idempotency_fields.sql`: nullable `request_id uuid`, `request_payload_hash varchar(64)`, actor email/name snapshots and `reason text`, plus partial unique index `(user_id, request_id) WHERE request_id IS NOT NULL`. No defaults, `NOT NULL`, `CHECK`, or backfill.
- Applied the versioned schema and migration only to a dedicated temporary PostgreSQL 16 container/database/volume on port 55439. Verified exact column types/nullability and the partial unique index.
- Synthetic SQL checks passed: legacy generic insert without new fields; review insert with all new fields; duplicate actor/request rejected; multiple generic NULL request IDs accepted. A deliberate exception injected after a booking update and audit insert rolled both writes back.
- Test-only canonical hashing confirmed key-order, UUID-case, and trimmed-reason normalization produce the same SHA-256 for semantically identical payloads; changing the booking or reason changed the hash. A test-only SQL idempotency harness confirmed same-key/same-hash retry leaves exactly one row and same-key/same-actor with a different hash is rejected. These checks do not implement or validate application runtime code or concurrent request handling.
- The temporary Compose container, volume, and network were removed. No operational database or real data was accessed. No application code or frontend was changed; no commit or push was made.
- No schema incompatibility was observed. The migration remains unapplied to the operational database; audit helper and approval endpoint remain future work.

## 2026-10-15 importer review audit persistence decision — design only

### Decision and plan

- Reuse the generic `audit_log` declared by the versioned schema rather than introduce a specialized table. Existing columns represent entity/action, actor FK, before/after JSON, and timestamp; no application writes it yet.
- Planned additive nullable columns: `request_id uuid`, `request_payload_hash varchar(64)`, actor email/name snapshots, and `reason text`; add a partial unique index on `(user_id, request_id)` where request ID is non-NULL.
- Idempotency is unique per actor/request ID. Same normalized payload returns the original result/event without a second write; a different payload returns 409. The normalized hash includes booking, expected old mapping values, target state/tour, and trimmed reason. A first no-op writes one `import_review.noop` event to consume its key.
- Defined event actions and exact before/after payload shape in the approval workflow document. Entries are append-only, not automatically purged in v1, and read/write access uses explicit review audit/approval permission keys.
- Transaction plan locks the booking, compares expected current mapping fields, validates/locks an active canonical tour, and commits the mapping update plus audit insert atomically.

### Scope and verification

- Documentation/design only at that checkpoint. No SQL, endpoint, frontend, mapping behavior, or database change/access occurred in the design task.
- The server-side auth foundation is committed; the trusted JWT issuer/key provisioning path is still required before a protected write endpoint can be deployed.

## 2026-10-15 server-side authentication and authorization foundation

### What was done

- Inspected the versioned users/roles schema, dependencies, routers, config, and tests. No auth middleware/dependency, login/token issuer, external auth library, permission seed data, authorization checks, or audit-log writes exist in the app.
- Added opt-in bearer JWT verification in `backend/app/auth.py`. It accepts HS256 only, validates signature, issuer, audience, expiry, optional not-before, and UUID subject; user active state and role permissions are reloaded from the database per request.
- Added reusable `get_current_user` and `require_permission` dependencies. Missing/invalid identity and unknown user return 401; inactive user or missing permission return 403. Missing auth configuration returns 503 and never falls back to a development identity.
- Added optional `AUTH_JWT_SECRET`, `AUTH_JWT_ISSUER`, and `AUTH_JWT_AUDIENCE` settings. The verifier requires a 32-byte minimum secret. No token issuance or route-wide enforcement was added.
- Established the permission format because no real permission values or seeds exist in repository: flat JSON object with boolean permission keys; only literal `true` grants access.
- The schema declares a generic `audit_log`, but no application code writes it. The subsequent persistence decision reuses it with additive idempotency and actor snapshot fields.

### Verification and limits

- `backend/tests/test_auth.py`: 10 passed using mocked DB connections; tests include missing/invalid identity and signature, unsupported algorithm, expired/wrong-issuer/audience token, unknown/inactive user, granted/denied permission, malformed permission shape, and missing verifier configuration.
- Tests did not connect to PostgreSQL. No operational database was accessed.
- Existing API routes remain unauthenticated until each route/router opts into these dependencies. A trusted issuer and key provisioning path are prerequisites before deploying a protected write endpoint.

## 2026-10-15 importer review visibility — read-only

### What was done

- Confirmed booking list/detail APIs already returned `imported_raw_tour_name`, `mapping_status`, and `needs_manual_review`; full detail also returned the canonical `tour_id` and tour name.
- Added `tour_id` to list and basic booking detail SELECT responses; frontend booking types now model nullable review fields and tour IDs.
- Booking List and Booking Detail display mapping status as a separate badge, preserve/display the imported raw label, and show a visual review warning. A missing canonical tour is labeled `Needs review`.
- No review editing, approval workflow, or write endpoint was added. Booking status, mapping data, payments, deduplication, and the operational database were not changed.

### Verification

- Backend booking review visibility and importer mapping tests: 8 passed, using mocked database connections.
- Frontend production build and `oxlint`: passed. No frontend test runner is configured.
- No database was accessed.

## 2026-10-15 importer resolver unification checkpoint

### What was done

- Made `backend/import_rules.py::resolve_tour_mapping` the single source of truth for imported tour labels; removed the duplicate tour maps and resolver from `backend/import_thaiculture_data.py`.
- The importer resolves each label once and passes only a `confirmed` canonical name to `pick_tour`. `probable_manual_review` and `unmapped` preserve the raw label and review metadata while leaving `tour_id` null.
- Booking status, booking deduplication, and payments were not changed. No operational database was accessed, and no compatibility SQL was applied.

### Verification

- Relevant `import_rules` and booking-import tests: 7 passed.
- Full `test_import*.py` discovery: 10 passed, 1 pre-existing payments test failed because its fixture has no `amount` while expecting an insert. Payments code and test logic were outside this phase.
- `git diff --check` passed. Commit `fb62159` was subsequently published on `origin/main`.

## 2026-10-15 importer review schema and isolated import checkpoint

### What was done

- Added `database/migrations/20261015_add_booking_import_review_metadata.sql` with nullable `imported_raw_tour_name`, `mapping_status varchar(40)`, and `needs_manual_review` columns using `ADD COLUMN IF NOT EXISTS`.
- Applied `database/init/001_schema.sql` and the migration twice in a dedicated isolated PostgreSQL database. The second application skipped existing columns successfully.
- Kept `database/init/001_schema.sql` unchanged. No default, `NOT NULL`, `CHECK`, or backfill was added; the migration was not applied to the operational database.
- In the isolated importer run, 10 fixture bookings were processed: 7 confirmed with tour links and 3 probable-review rows with null `tour_id`. Raw labels were preserved. A second run left the count at 10 with no duplicate booking codes.
- Current booking status behavior remained 8 `Confirmed`, 1 `Pending`, and 1 `Cancelled`. Payments remained at 0 because the fixture CSV has no `amount`; payment code and semantics were not changed.
- The isolated test database, volume, network, and temporary files were removed. The operational database was not accessed.

### Verification

- Relevant `import_rules` and importer tests: 7 passed.
- Isolated schema checks confirmed the three columns are nullable with no defaults and no mapping CHECK constraint.

## 2026-10-15 financial contract v1 and documentation checkpoint

### What was done

- Published commit `d728cfd` to `origin/main` to stabilize the booking financial contract.
- Fixed `POST /payments`: all nine inserted columns receive matching values; the response includes `due_at` and `notes`; positive amount and DB field-limit validations are enforced.
- Fixed `GET /invoices/{invoice_no}` to use the existing header-only invoice schema and return `items: []`, without querying nonexistent `invoice_items`.
- Added `backend/app/financials.py` as the shared Paid/Pending aggregation and booking financial-summary implementation used by booking list, payment summary, and booking detail.
- Kept the confirmed financial rules: `requested_amount` is Paid + Pending; a positive partial confirmed payment is `partiallypaid`; covered selling price is `paid`; Pending with no confirmed payment is `depositrequested`; no Paid or Pending payment is `unpaid`.
- Kept proformas and the mandatory full-payment 48-hour deadline out of scope. No financial business decisions remain open for this task.
- Did not modify the operational database, dashboard KPI semantics, pricing formulas, or pricing quote flow.
- Created and removed a separate PostgreSQL test environment; its container, volume, and network were removed after verification.

### Verification

- Financial and pricing tests: 14 passed, including 4 new financial-contract tests (3 connected to isolated PostgreSQL and 1 unit test for aggregation statuses).
- Full backend suite: 23 passed, 1 failed. The failure is pre-existing and unrelated: `test_importer.py` supplies a CSV fixture without `amount`, which the importer skips.
- `compileall` and `git diff --check` passed.
- Commit `d728cfd` is on `origin/main`; `main` was synchronized after the push. This documentation checkpoint is committed locally only and has not been pushed.
- No application code or operational database was changed during this documentation update.

## 2026-10-15 minimum-margin quote policy v1

### What was done

- Added versioned quote calculation policy `minimum-margin-30-v1` for a 30% minimum net margin excluding VAT.
- Added an explicit `POST /pricing/quotes/{booking_code}/generate` action. It locks the booking, refuses confirmed bookings, validates the active tour rule VAT rate, and inserts a new quote snapshot in one transaction.
- Kept new quote legacy price columns gross and stored net equivalents, VAT, verdict, and approval status in `pricing_quotes.breakdown`.
- Added a quote generation action and latest quote policy status to booking detail/list views. Existing booking, dashboard, and operations margin calculations were not changed.
- Added unit tests and mocked endpoint integration tests. No database rows or schema were changed during implementation.
- Added `docs/PRICING_POLICY_MINIMUM_MARGIN_30_V1.md`.

### Verification

- Backend pricing tests: 8 passed.
- Frontend production build: passed (`tsc -b` and Vite build).
- No live quote generation or database write was performed.

## 2026-10-13 continuity and catalog-ingestion checkpoint

### What was done

- Cleaned the payment-import surface:
  - removed the two accidental 0 THB payment artifacts
  - confirmed 3 real payments remain
  - confirmed 0 padded `' Pattaya'` payment-status artifacts remain
- Patched `backend/import_thaiculture_data.py` so payment rows without valid positive `amount` are skipped.
- Confirmed and published the payment-import fix in commit `8c40160`.
- Added and published a continuity checkpoint in commit `0a5f4c1`.
- Confirmed that `TCT-IMP-2026-0007` maps to `WEB-027 Khao Yai National Park – Full Day`.
- Confirmed that `TCT-IMP-2026-0008` maps to `WEB-028 Kanchanaburi: River Kwai & Erawan Falls`.
- Updated `docs/NEXT_STEPS.md` to reflect confirmed tour mappings in commit `bd2f25f`.
- Created `backend/data/catalog/tours.json` as canonical local catalog input.
- Created `backend/ingest_catalog.py` as minimal idempotent catalog-ingestion runner.
- Validated catalog ingestion with dry-run in Docker backend container.
- Patched container/runtime compatibility:
  - switched from `psycopg2` to `psycopg`
  - moved DB connection to `DATABASE_URL`
  - aligned catalog path to `data/catalog/tours.json`
  - aligned backend-to-postgres host resolution
- Ran real catalog ingestion successfully:
  - `upserted 28 tours`
  - `tours_count = 28`
  - `duplicate_codes = 0`
- Verified all 10 imported bookings remained linked to the same canonical tours after ingestion.
- Published catalog-ingestion milestone in commit `b9ab701`.

### What it means

- ThaiCulture Manager now has a minimal durable catalog-ingestion flow, not only a manual SQL seed.
- Imported-booking tour links survived a real catalog refresh based on upsert, which reduces risk for future catalog maintenance.
- Payment import is protected against recreation of 0 THB artifacts.
- The project continuity docs are now expected to treat both payments cleanup and catalog ingestion as completed checkpoints.

### Current verified state

- bookings_count: 12
- customers_count: 8
- payments_count: 3
- tours_count: 28
- locations_count: 6
- guides_count: 0
- drivers_count: 0
- assignments_count: 0
- local and remote `main` include the payment-import and catalog-ingestion milestones

## 2026-10-16 importer review approval release readiness

### What was checked

- Confirmed `app.main` imports and registers `bookings.router`; the bookings router does not import the app module, so the observed import direction is not circular.
- Documented the current approval endpoint contract: request/auth requirements, success response fields, and HTTP error codes. The route currently returns a dict without an explicit FastAPI `response_model`.
- Confirmed approval tests cover authorized confirmation, review state with null `tour_id`, stale state, identical retry, changed-payload conflict, audit rollback, and auth/permission rejection.
- Confirmed migration files are discoverable by filename but there is no migration runner or applied migration ledger. Deployment must inspect schema state directly under operator authorization.
- Added a secret-safe operator release checklist covering environment provisioning, backup, both additive migrations, reviewer permission, staging smoke tests, rollback, and manual secret rotation.

### Scope and outcome

- No backend/frontend logic, migration SQL, or live data changed.
- No operational database was accessed, no migration was applied, and Compose was not started.
- Operator-owned deployment steps remain pending; see `docs/IMPORTER_REVIEW_APPROVAL_RELEASE_CHECKLIST.md`.

## 2026-10-16 isolated approval staging validation

- Started PostgreSQL 16 in a dedicated Compose project using a dedicated localhost port, volume, and network. Applied the versioned initial schema and both additive importer-review/audit migrations only in that isolated environment.
- Verified the expected booking review and audit idempotency columns are nullable and verified the partial unique audit index definition.
- Took a custom-format backup before mutable tests and validated the archive with `pg_restore --list`.
- Passed 14 approval tests, 7 audit helper tests, 10 auth tests, and 1 booking visibility test (32 total; no skips/failures). Coverage included all requested auth/smoke cases, retry/conflict, stale update, audit rollback/atomicity, and preservation of raw label and booking operational status.
- The required operator setting names were all absent from this process environment; external secret-manager state was not inspected. No actual operator credentials were used.
- Removed the test container, volume, network, backup, and temporary Compose file. No operational database was accessed or modified.

## 2026-10-16 review approval UI and isolated staging tooling

- Added a Review Queue navigation view that lists bookings flagged for manual mapping review, displays the imported raw tour label, mapping status, booking status, current canonical tour, and active canonical tour candidates.
- Added an approval form with required active-tour selection, required reason, explicit confirmation, reviewer bearer token held only in component memory, and a request ID retained across retryable transport failures. HTTP 403 and 409 receive dedicated feedback; 409 disables a repeat decision until the queue is reloaded.
- Added API mock tests for successful approval, permission denied, stale update, and idempotency payload conflict. All four frontend API tests passed; frontend production build and lint passed.
- Added isolated-tool preflight tests for missing settings, wrong database target, explicit resource names, and safe resource resolution (4/4 passed). `compileall` and `git diff --check` passed.
- Added a separate staging Compose file and secret-safe scripts for preflight, isolated startup, custom-format backup/restore-list verification, migration/index verification, test/smoke execution, and label-scoped cleanup. The scripts never print environment values and reject missing settings before invoking Docker operations.
- Backend auth (10) and booking visibility (1) tests passed. Audit payload unit tests passed (2); five PostgreSQL audit tests and all 14 PostgreSQL approval tests were skipped because no isolated test database was configured. The four staging preflight tests passed. A backend test attempt without a test-only `DATABASE_URL` first failed during settings import; a synthetic unreachable test-only settings URL was then used to run non-database tests. No database connection was attempted.
- Secret-safe staging preflight reports BLOCKED because all five required keys are absent from the empty `.env.staging`; it returned before invoking Docker. Compose was not started; no database was accessed.
- No booking status, raw label, financial logic, payment behavior, mapping resolver, or operational database data was changed.

## 2026-10-16 Review Queue refinements

- Added client-side filters for mapping status, `needs_manual_review`, and booking status, using only statuses returned by the existing bookings API.
- Added local sorting by created date, tour date, or booking code; ten-row pagination; and a pending-review count that remains independent of current filters.
- Distinguished stale booking-mapping conflicts from reused request-ID payload conflicts. A 409 disables another submission until the queue is reloaded; transport failures retain the original request ID for safe retry.
- Added frontend tests for filters/counts, sorting/pagination without duplicates, conflict classification, and the approval API's success/403/409 paths. All 7 frontend tests passed; production build and lint passed.
- No backend/API/schema, booking status, mapping data, payment, financial, or operational database changes were made. Staging validation remains pending operator provisioning of `.env.staging`.

## 2026-10-16 Booking Financial Workflow V1.1

- Added nullable `bookings.deposit_amount` through `20261016_add_booking_deposit_amount.sql`; no defaults, constraints, or historical backfill.
- Centralized payment status normalization and financial derivation. Only positive same-currency paid/partiallypaid amounts enter paid totals; open requests feed pending totals; cancelled and draft are excluded. Balance never falls below zero.
- Added total/deposit/paid/balance/status to booking financial summary and full detail. Payment details include due date and notes. Payment writes validate the seven canonical statuses and booking currency.
- Booking Detail now presents a separate financial summary with empty/loading/error states. Operational booking status, review behavior, and margin formulas were left unchanged; invoice generation was not added.
- Staging remains separate. No operational database was accessed.
- Verification: financial/API tests passed against a dedicated temporary PostgreSQL container; the migration was applied after the initial schema in a disposable schema and verified as nullable `numeric(12,2)` with no default. Auth (10), visibility (1), compileall, frontend tests (9), build, lint, and `git diff --check` passed. The final full backend suite ran 67 tests: 66 passed and the existing `test_current_payment_import_inserts_row` failed because its payment CSV fixture lacks `amount`; no tests were skipped with the isolated test DB available. The temporary container, volume, network, and helper files were removed.
