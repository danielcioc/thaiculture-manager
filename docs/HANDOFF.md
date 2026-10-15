# ThaiCulture Manager — Handoff

## Current task status

Pricing policy v1 and booking financial contract v1 are implemented. Financial-contract commit `d728cfd` and resolver-unification commit `fb62159` are published on `origin/main`. Importer-review schema compatibility is represented by migration `20261015_add_booking_import_review_metadata.sql` in commit `3738923`; it has only been tested in isolated PostgreSQL. The current local checkpoint adds read-only importer-review visibility and is not yet committed.

## Last confirmed state

- `d728cfd fix(financials): repair payment and invoice contract aggregation` is published on `origin/main`.
- The last recorded operational DB snapshot (2026-10-13) was 12 bookings, 8 customers, 3 payments, 28 tours, and 6 locations. It was not re-queried for the financial-contract task.
- 3 real payments remain in DB.
- 0 zero-amount payment artifacts remain.
- Imported bookings remain linked to the correct canonical tours after catalog ingestion validation.
- No operational DB write was made during the pricing and financial-contract work.
- Importer resolver unification and the phase-3 importer/schema checks did not access the operational database.
- The read-only importer-review visibility checkpoint exposes the raw imported tour label, mapping status, review flag, and canonical tour data in booking list/detail. Missing tours display as `Needs review`; no edit or approval action is present. Backend visibility/importer tests (8), frontend build, and lint passed; no frontend test runner is configured. No database was accessed.

## Files added or changed in this phase

- `backend/import_thaiculture_data.py`
- `backend/tests/test_importer.py`
- `database/migrations/20261015_add_booking_import_review_metadata.sql`
- `backend/data/catalog/tours.json`
- `backend/ingest_catalog.py`
- `docs/PROJECT_STATE.md`
- `docs/NEXT_STEPS.md`
- `docs/HANDOFF.md`
- `docs/SESSION_LOG.md`

## Important implementation notes

- Tour mapping has one source of truth in `backend/import_rules.py::resolve_tour_mapping`. The importer resolves once and does not re-resolve inside `pick_tour`.
- Only `confirmed` mappings look up and set canonical `tour_id`. `probable_manual_review` and `unmapped` preserve the raw imported label and review fields with `tour_id` null.
- Relevant importer/mapping tests passed (7). Full `test_import*.py` discovery has one pre-existing failure in the payments fixture, which omits `amount` while expecting an insert; payment code and test logic were not changed.
- The additive migration adds nullable `imported_raw_tour_name`, `mapping_status varchar(40)`, and `needs_manual_review` columns using `ADD COLUMN IF NOT EXISTS`. It was applied twice in isolated PostgreSQL only; no defaults, `NOT NULL`, `CHECK`, or backfill were added, and it has not been applied to the operational database.
- Phase-3 isolated import processed 10 bookings (7 confirmed and linked, 3 probable-review with `tour_id` NULL). The second run left 10 bookings and no duplicate booking codes. Raw labels were preserved. The no-amount payments fixture inserted no payments; payments remain outside this scope.
- Payment importer now skips rows without a valid positive `amount`.
- Pricing quote generation applies `minimum-margin-30-v1` at a 30% net minimum margin and is limited to `Inquiry`, `Offer Prepared`, and `Awaiting Confirmation`. Existing pricing formulas were not changed and no new tariffs were introduced.
- `POST /payments` now writes all nine fields consistently and returns `due_at` and `notes`; positive amount and database field-size constraints are validated.
- Invoice detail returns an empty `items` array because the current schema has no `invoice_items` table.
- `backend/app/financials.py` centralizes Paid/Pending amounts and the confirmed booking financial statuses for booking list, payment summary, and booking detail.
- Dashboard KPI semantics and the existing pricing formulas remain unchanged. Proformas and the 48-hour payment deadline are out of scope.
- Verification: 14 financial/pricing tests passed, including 4 new financial-contract tests (3 connected to isolated PostgreSQL and 1 unit test); whole backend suite 23 passed and 1 pre-existing importer fixture failure. `compileall` and `git diff --check` passed; the isolated test DB was removed.
- Catalog ingestion now exists as a minimal durable path:
  - source: `backend/data/catalog/tours.json`
  - runner: `backend/ingest_catalog.py`
  - DB write mode: `ON CONFLICT (tour_code) DO UPDATE`
- In container context:
  - script path resolves as `/app/ingest_catalog.py`
  - catalog path resolves as `/app/data/catalog/tours.json`
  - DB connection works through `DATABASE_URL`
  - backend container uses `psycopg`, not `psycopg2`

## Recommended next task

Continue the importer-review/data-governance path with remaining validation and review workflow decisions. The additive schema migration has been tested only in isolation. Keep raw tour labels, deterministic mappings, and review visibility; avoid silent remapping.

Keep the following existing questions open without assumptions: whether manual-review flags become an active review workflow, and how historical booking updates should be reapplied without delete-and-reimport. Defer website integration until the broader internal model is aligned.

## Restart rule

At the next session start, read in this order:

1. `docs/PROJECT_STATE.md`
2. `docs/NEXT_STEPS.md`
3. the latest section in `docs/SESSION_LOG.md`
4. `docs/HANDOFF.md`
5. only then inspect code
