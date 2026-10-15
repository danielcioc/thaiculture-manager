# ThaiCulture Manager — Project State

Last updated: 2026-10-15

## Purpose

ThaiCulture Manager este sistemul intern de operațiuni pentru ThaiCulture Tours. El gestionează customers, bookings, canonical tours, payments, invoices, assignments, guides, drivers, locations și rezumate operaționale/financiare.

## Current stack

- PostgreSQL 16 in Docker
- FastAPI backend
- React + TypeScript + Vite frontend
- Docker Compose local orchestration

## Server-side authentication foundation

- `backend/app/auth.py` provides reusable FastAPI dependencies for externally issued HS256 JWT validation, active-user lookup, and permission checks.
- The JWT subject is resolved against `users` for each protected request; role permissions are loaded from the current `roles.permissions` JSONB value.
- Permission JSON contract: a flat object mapping permission keys to booleans; only literal `true` grants access. No existing permission data or seed format was present in the repository.
- Missing/invalid identity and unknown user return 401; inactive user or missing permission returns 403. Missing verifier settings fail closed with 503.
- Auth settings are optional for the existing app, but protected dependencies cannot authenticate unless `AUTH_JWT_SECRET`, `AUTH_JWT_ISSUER`, and `AUTH_JWT_AUDIENCE` are configured. Secret values are never logged or returned.
- No login/token issuance, development identity bypass, audit writing, or route-wide protection was added. Existing routes remain as before; future protected endpoints must opt into the dependency.
- Authentication tests: 10 passed with database access mocked. No database was accessed.

## Importer review audit persistence decision

- The review workflow reuses the generic schema `audit_log`; no specialized audit table is planned. Migration `database/migrations/20261015_add_audit_log_idempotency_fields.sql` adds nullable request/idempotency, actor snapshot, and reason fields plus partial uniqueness. It passed isolated PostgreSQL compatibility and behavior checks; it has not been applied operationally. No runtime audit writer or approval endpoint exists.
- Idempotency is actor-scoped. Same key and normalized payload returns the original event; same key with a different payload returns 409. A first no-op consumes the key with one no-op event. Audit actions and before/after payload keys are specified in `docs/IMPORTER_REVIEW_APPROVAL_WORKFLOW_V1.md`.
- Entries are append-only with no automatic purge in v1. Access uses `bookings.import_review.audit.read`; writes use `bookings.import_review.approve` after authentication is configured.
- Transaction plan: lock booking, validate expected old mapping fields, lock and verify active canonical tour, then update booking mapping fields and insert audit event in one transaction.
- The persistence decision is documented in `docs/DECISIONS.md`; migration compatibility was validated in an isolated database only. No operational database was accessed or changed.

## Last verified operational database snapshot

The counts below were last verified on 2026-10-13. They were not re-read during the 2026-10-15 financial-contract work; no operational database writes were made.

- bookings_count: 12
- customers_count: 8
- payments_count: 3
- tours_count: 28
- locations_count: 6
- guides_count: 0
- drivers_count: 0
- assignments_count: 0

## Payments state

- 3 real payments remain in DB.
- 0 zero-amount payment artifacts remain.
- 0 padded `' Pattaya'` status artifacts remain.
- `backend/import_thaiculture_data.py` now skips payment rows without a valid positive `amount`.
- Commit for payment importer protection: `8c40160`.

## Current canonical catalog

The canonical tours catalog contains 28 active tours:

- `WEB-001` through `WEB-026`: tours sourced from the website catalog baseline
- `WEB-027`: `Khao Yai National Park – Full Day`
- `WEB-028`: `Kanchanaburi: River Kwai & Erawan Falls`

## Historical import status

All 10 imported bookings are mapped to canonical tours and remain correctly linked after catalog ingestion validation:

- `TCT-IMP-2026-0001` -> `WEB-006 Evening in Ayutthaya`
- `TCT-IMP-2026-0002` -> `WEB-016 Whale Safari`
- `TCT-IMP-2026-0003` -> `WEB-023 Hua Hin Temple Tour`
- `TCT-IMP-2026-0004` -> `WEB-021 1-Day Trip – Hua Hin → Bangkok`
- `TCT-IMP-2026-0005` -> `WEB-022 Elephant Watching in Kui Buri National Park`
- `TCT-IMP-2026-0006` -> `WEB-007 Ayutthaya: 5 Essential Sights`
- `TCT-IMP-2026-0007` -> `WEB-027 Khao Yai National Park – Full Day`
- `TCT-IMP-2026-0008` -> `WEB-028 Kanchanaburi: River Kwai & Erawan Falls`
- `TCT-IMP-2026-0009` -> `WEB-012 Amphawa: The City on Water`
- `TCT-IMP-2026-0010` -> `WEB-007 Ayutthaya: 5 Essential Sights`

## Importer and catalog state

- Payment importer is protected against missing/invalid/zero amounts.
- Tour-label resolution now has one source of truth: `backend/import_rules.py::resolve_tour_mapping`. The importer no longer carries a duplicate resolver or resolves the same label again in `pick_tour`.
- Only `confirmed` mappings perform canonical-tour lookup and set `tour_id`. `probable_manual_review` and `unmapped` preserve `imported_raw_tour_name`, retain their mapping/review values, and leave `tour_id` null. A probable candidate remains a resolver result, not an active booking relationship.
- Relevant mapping/importer tests passed (7 tests). The `test_import*.py` suite still has one pre-existing unrelated payments test failure: its fixture omits `amount` while expecting an insert. Payments behavior and test logic were outside this phase.
- Persistent compatibility migration: `database/migrations/20261015_add_booking_import_review_metadata.sql`. It adds the three nullable review columns with `ADD COLUMN IF NOT EXISTS`; it was applied twice successfully in isolated PostgreSQL only. `database/init/001_schema.sql` remains unchanged, and the migration has not been applied operationally.
- No `DEFAULT`, `NOT NULL`, `CHECK`, or backfill was added. Those choices remain deferred.
- Controlled isolated importer run: all 10 repository booking fixtures imported; 7 were `confirmed` and linked, 3 were `probable_manual_review` with `tour_id` NULL; raw labels were retained. Re-running left the booking count at 10 with no duplicate booking codes. Current importer statuses were 8 `Confirmed`, 1 `Pending`, and 1 `Cancelled`. The payments fixture without `amount` inserted 0 payments. This test did not access the operational database.
- Resolver checkpoint commit `fb62159` is published on `origin/main`.
- Import-review metadata is exposed read-only by the booking list and detail APIs. The list and basic detail SELECTs now include `tour_id`; full detail already returned `tour_id`, tour name, customer, booking code, and all three review fields.
- Booking List and Booking Detail show a separate mapping-status badge, imported raw label, and visual review warning. Missing canonical tour names display as `Needs review`; booking operational status is shown independently. No review editing or approval actions were added.
- Backend booking review visibility tests passed (8 relevant tests); frontend production build and lint passed. No frontend test runner is configured in `frontend/package.json`.
- This visibility checkpoint did not access or write to any database.
- Historical tour mappings for `WEB-027` and `WEB-028` are business-confirmed.
- A minimal durable catalog-ingestion workflow now exists:
  - canonical source file: `backend/data/catalog/tours.json`
  - ingestion script: `backend/ingest_catalog.py`
  - ingestion mode: idempotent upsert on `tour_code`
- Catalog ingestion was validated with:
  - dry-run success
  - real run success
  - `tours_count = 28`
  - `duplicate_codes = 0`
  - imported booking-tour links preserved
- Commit for catalog ingestion: `b9ab701`.

## Pricing and financial contract release — 2026-10-15

- The versioned `minimum-margin-30-v1` policy uses a 30% minimum margin on net price, excluding VAT, when generating a new quote.
- Quote generation is restricted to bookings in `Inquiry`, `Offer Prepared`, or `Awaiting Confirmation`. Confirmed, cancelled, post-confirmation, and unknown statuses are refused.
- Existing pricing formulas and the margin formulas in Booking Detail, Dashboard, and Operations Summary were not changed. No new costs or tariffs were introduced.
- `POST /payments` now inserts all nine payment columns with their matching values and returns `due_at` and `notes`. It validates positive amounts and DB field limits.
- `GET /invoices/{invoice_no}` returns `items: []`: the current database schema has invoice headers and amounts but no `invoice_items` table.
- `backend/app/financials.py` centralizes Paid/Pending aggregation and the confirmed booking financial summary rules; booking list, payment summary, and booking detail use the same rules.
- The contract commit `d728cfd` (`fix(financials): repair payment and invoice contract aggregation`) is published on `origin/main`. The `main` branch was synchronized after that push; this documentation update is being committed locally and is not pushed yet.
- Verification: 14 financial/pricing tests passed, including 4 new financial-contract tests: 3 connected to isolated PostgreSQL and 1 unit test for aggregation statuses. The full backend suite reported 23 passed and 1 pre-existing importer fixture failure (the CSV fixture lacks `amount`). `compileall` and `git diff --check` passed. The isolated PostgreSQL test environment was stopped and removed.
- No business decisions remain open for the financial contract delivered in `d728cfd`. Proformas and mandatory full payment at least 48 hours before a tour remain outside that task.

## Current technical debt

- Keep the importer review mechanism and data-governance path as the next internal priority.
- Decide whether the existing manual-review flags should remain passive or become a stronger review workflow.
- Clarify the durable reimport/update path for historical booking updates without delete-and-reimport.
- Defer website integration until the broader internal booking model is aligned; completion of the financial contract v1 does not settle the other documented workflow questions.
