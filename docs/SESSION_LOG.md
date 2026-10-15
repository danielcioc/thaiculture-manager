# ThaiCulture Manager — Session Log

## 2026-10-15 server-side authentication and authorization foundation

### What was done

- Inspected the versioned users/roles schema, dependencies, routers, config, and tests. No auth middleware/dependency, login/token issuer, external auth library, permission seed data, authorization checks, or audit-log writes exist in the app.
- Added opt-in bearer JWT verification in `backend/app/auth.py`. It accepts HS256 only, validates signature, issuer, audience, expiry, optional not-before, and UUID subject; user active state and role permissions are reloaded from the database per request.
- Added reusable `get_current_user` and `require_permission` dependencies. Missing/invalid identity and unknown user return 401; inactive user or missing permission return 403. Missing auth configuration returns 503 and never falls back to a development identity.
- Added optional `AUTH_JWT_SECRET`, `AUTH_JWT_ISSUER`, and `AUTH_JWT_AUDIENCE` settings. The verifier requires a 32-byte minimum secret. No token issuance or route-wide enforcement was added.
- Established the permission format because no real permission values or seeds exist in repository: flat JSON object with boolean permission keys; only literal `true` grants access.
- The schema declares a generic `audit_log`, but no application code writes it. Audit persistence design remains a separate follow-up decision.

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
