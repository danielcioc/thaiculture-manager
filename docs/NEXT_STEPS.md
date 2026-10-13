# ThaiCulture Manager — Next Steps

Last updated: 2026-10-13

## Confirmed current state

- Docker stack starts successfully.
- PostgreSQL contains 28 canonical tours.
- All 10 historical imported bookings are mapped to canonical tours.
- The `WEB-027` and `WEB-028` mappings are business-confirmed.
- Payment importer is protected against 0 THB artifacts.
- Database currently contains 12 bookings, 8 customers, 3 payments, 28 tours, and 6 locations.
- A minimal idempotent catalog-ingestion workflow now exists and was validated successfully.
- Latest commits are pushed to `main`.

## Immediate next priority

Evolve the catalog-ingestion workflow from local JSON export into a more durable website/catalog refresh path, without losing the safe upsert behavior on `tour_code`.

## Required behavior

- Keep `backend/data/catalog/tours.json` as a controlled canonical input until website-sourced refresh is implemented.
- Keep `backend/ingest_catalog.py` idempotent.
- Do not delete and recreate tours during refresh.
- Preserve existing booking-to-tour foreign keys.
- Do not create duplicate tours.
- Keep imported bookings stable during future catalog refreshes.

## Parallel priority

Continue the importer-review/data-governance path:

- preserve imported raw tour labels
- keep deterministic confirmed mappings
- make reviewable or unmapped records visible for business review
- avoid silent unsafe remapping

## Verification after future changes

After any catalog-ingestion or importer-mapping change, verify:

- `tours_count` remains correct
- `duplicate_codes = 0`
- all 10 imported bookings retain correct canonical tours
- no payment artifacts are reintroduced
- `db-check` remains healthy
