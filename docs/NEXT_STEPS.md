# ThaiCulture Manager — Next Steps

Last updated: 2026-10-15

## Confirmed current state

- Docker stack starts successfully.
- PostgreSQL contains 28 canonical tours.
- All 10 historical imported bookings are mapped to canonical tours.
- The `WEB-027` and `WEB-028` mappings are business-confirmed.
- Payment importer is protected against 0 THB artifacts.
- Database currently contains 12 bookings, 8 customers, 3 payments, 28 tours, and 6 locations.
- A minimal idempotent catalog-ingestion workflow now exists and was validated successfully.
- Pricing and financial-contract implementation commit `d728cfd` is published to `origin/main`.
- The documentation update for this checkpoint is a separate local commit and has not been pushed yet.
- The operational database was not modified during financial-contract work.
- Database counts below are the last recorded snapshot from 2026-10-13 and were not re-queried for this checkpoint.

## Immediate next priority: importer review and data governance

Continue the already documented importer-review mechanism: preserve raw source values, keep deterministic mappings, and make ambiguous or unmapped records visible for business review. Do not make website integration the next task before the broader internal model is aligned.

## Existing catalog-ingestion safeguards

- Keep `backend/data/catalog/tours.json` as a controlled canonical input until website-sourced refresh is implemented.
- Keep `backend/ingest_catalog.py` idempotent.
- Do not delete and recreate tours during refresh.
- Preserve existing booking-to-tour foreign keys.
- Do not create duplicate tours.
- Keep imported bookings stable during future catalog refreshes.

## Verification after future changes

After any catalog-ingestion or importer-mapping change, verify:

- `tours_count` remains correct
- `duplicate_codes = 0`
- all 10 imported bookings retain correct canonical tours
- no payment artifacts are reintroduced
- `db-check` remains healthy

## Existing open questions — retain without assumptions

- Whether `REVIEW_REQUIRED_TOURS` stays passive or becomes stronger review workflow logic.
- The durable path for applying historical booking updates without delete-and-reimport.
- When and how a website-sourced catalog refresh should begin, after internal model alignment.

These are existing project questions, not decisions made by the pricing or financial-contract tasks.
