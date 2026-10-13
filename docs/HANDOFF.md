# ThaiCulture Manager — Handoff

## Current task status

The payment-import cleanup and the minimal catalog-ingestion milestone are complete.

## Last confirmed state

- Local repo and remote `main` include:
  - `8c40160` fix(import): skip payments without a positive amount
  - `0a5f4c1` docs: add 2026-10-13 session checkpoint
  - `bd2f25f` docs: confirm tour mappings and refresh next steps
  - `b9ab701` feat(catalog): add idempotent tours ingestion
- Verified DB state:
  - bookings_count: 12
  - customers_count: 8
  - payments_count: 3
  - tours_count: 28
  - locations_count: 6
- 3 real payments remain in DB.
- 0 zero-amount payment artifacts remain.
- Imported bookings remain linked to the correct canonical tours after catalog ingestion validation.

## Files added or changed in this phase

- `backend/import_thaiculture_data.py`
- `backend/data/catalog/tours.json`
- `backend/ingest_catalog.py`
- `docs/PROJECT_STATE.md`
- `docs/NEXT_STEPS.md`
- `docs/HANDOFF.md`
- `docs/SESSION_LOG.md`

## Important implementation notes

- Payment importer now skips rows without a valid positive `amount`.
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

Advance the catalog-ingestion workflow from locally exported JSON into a more direct website/catalog refresh workflow, while preserving:
- idempotent upsert behavior
- existing booking foreign keys
- zero duplicates
- stable imported booking mappings

## Restart rule

At the next session start, read in this order:

1. `docs/PROJECT_STATE.md`
2. `docs/NEXT_STEPS.md`
3. the latest section in `docs/SESSION_LOG.md`
4. `docs/HANDOFF.md`
5. only then inspect code
