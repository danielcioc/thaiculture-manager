# ThaiCulture Manager — Next Steps

Last updated: 2026-10-15

## Confirmed current state

- Docker stack starts successfully.
- PostgreSQL contains 28 canonical tours.
- All 10 historical imported bookings are mapped to canonical tours.
- The `WEB-027` and `WEB-028` mappings are business-confirmed.
- `backend/import_rules.py::resolve_tour_mapping` is the sole tour-label resolver. Importer mapping now runs once per booking; only `confirmed` creates a canonical `tour_id`, while `probable_manual_review` and `unmapped` keep `tour_id` null and preserve the raw label.
- Resolver/importer tests passed (7 relevant tests). The `test_import*.py` suite retains one pre-existing payments fixture failure because its CSV has no `amount`; payment code and test logic were not changed.
- The versioned importer-review metadata migration was applied twice in an isolated PostgreSQL test only. It has not been applied operationally; defaults, constraints, and backfill remain deferred.
- The controlled importer run processed all 10 historical CSV fixtures; rerunning left 10 bookings with no duplicate booking codes. Payments remained at 0 in the isolated fixture because `payments.csv` has no `amount` column. No operational database was accessed.
- Payment importer is protected against 0 THB artifacts.
- Database currently contains 12 bookings, 8 customers, 3 payments, 28 tours, and 6 locations.
- A minimal idempotent catalog-ingestion workflow now exists and was validated successfully.
- Pricing and financial-contract implementation commit `d728cfd` is published to `origin/main`.
- Importer resolver checkpoint `fb62159` is published on `origin/main`.
- The operational database was not modified during financial-contract work.
- Database counts below are the last recorded snapshot from 2026-10-13 and were not re-queried for this checkpoint.

## Immediate next priority: importer review and data governance

Continue the importer-review mechanism with isolated schema compatibility and importer validation. Preserve raw source values, use the canonical resolver, and keep ambiguous or unmapped records visible for review. Do not make website integration the next task before the broader internal model is aligned.

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

- Whether existing manual-review flags should stay passive or become stronger review workflow logic.
- The durable path for applying historical booking updates without delete-and-reimport.
- When and how a website-sourced catalog refresh should begin, after internal model alignment.

These are existing project questions, not decisions made by the pricing or financial-contract tasks.
