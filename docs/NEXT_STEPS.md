# ThaiCulture Manager — Next Steps

Last updated: 2026-10-16

## Confirmed current state

- Docker stack starts successfully.
- PostgreSQL contains 28 canonical tours.
- All 10 historical imported bookings are mapped to canonical tours.
- The `WEB-027` and `WEB-028` mappings are business-confirmed.
- `backend/import_rules.py::resolve_tour_mapping` is the sole tour-label resolver. Importer mapping now runs once per booking; only `confirmed` creates a canonical `tour_id`, while `probable_manual_review` and `unmapped` keep `tour_id` null and preserve the raw label.
- Resolver/importer tests passed (7 relevant tests). The `test_import*.py` suite retains one pre-existing payments fixture failure because its CSV has no `amount`; payment code and test logic were not changed.
- The versioned importer-review metadata migration was applied twice in an isolated PostgreSQL test only. It has not been applied operationally; defaults, constraints, and backfill remain deferred.
- The controlled importer run processed all 10 historical CSV fixtures; rerunning left 10 bookings with no duplicate booking codes. Payments remained at 0 in the isolated fixture because `payments.csv` has no `amount` column. No operational database was accessed.
- Booking review metadata is now visible read-only in booking list/detail responses and UI. Missing canonical tours display `Needs review`; review fields do not alter booking operational status. Backend tests (8), frontend build, and frontend lint passed.
- Server-side auth foundation provides HS256 bearer validation, active-user lookup, and permission-key dependencies. The permission JSON shape is a flat boolean map. The importer review decision endpoint is protected by it; ten mocked auth tests pass. There is no token issuer/login flow in the application.
- Importer review audit persistence reuses `audit_log`. The additive migration was validated in isolated PostgreSQL and remains unapplied operationally. A caller-transaction audit helper with idempotency and 7 isolated PostgreSQL tests is complete and is now used by the protected approval endpoint.
- `POST /bookings/{booking_code}/import-review/decision` now provides the protected mapping decision endpoint. It requires `bookings.import_review.approve`, checks stale expected mapping state and active canonical tours, preserves raw labels and booking status, and commits mapping plus audit atomically. Identical retries replay the event; payload conflicts return 409. Fourteen endpoint tests passed against disposable PostgreSQL, and auth/read-only visibility tests passed without operational DB access.
- Payment importer is protected against 0 THB artifacts.
- Database currently contains 12 bookings, 8 customers, 3 payments, 28 tours, and 6 locations.
- A minimal idempotent catalog-ingestion workflow now exists and was validated successfully.
- Pricing and financial-contract implementation commit `d728cfd` is published to `origin/main`.
- Importer resolver checkpoint `fb62159` is published on `origin/main`.
- The operational database was not modified during financial-contract work.
- Database counts below are the last recorded snapshot from 2026-10-13 and were not re-queried for this checkpoint.

## Immediate next priority: isolated staging validation

The read-only importer review visibility milestone now has a dedicated Review Queue UI with an explicit approval form wired to `POST /bookings/{booking_code}/import-review/decision`. Approval requires a bearer token, active canonical tour, reason, and explicit confirmation; the token is kept in component memory only. A 409 requires reloading before another decision; transport failures retain the request ID so the same request can be retried idempotently.

The queue also supports mapping-status, manual-review-flag, and booking-status filters, local sorting by creation date/tour date/booking code, ten-row pagination, and a pending-review count. Stale mapping changes and request-ID payload conflicts have distinct feedback. Seven frontend tests pass, with build and lint passing.

Local staging tooling is isolated under `docker-compose.staging.yml` and `scripts/staging/`. The Compose project, containers, network, volume, and localhost ports have dedicated names. Preflight rejects missing settings and any database URL that does not point to the fixed isolated PostgreSQL service/database. Staging validation is pending operator provisioning of `.env.staging` only; the file must remain untracked and secret values must never be printed. Use preflight first, then the documented backup, migration verifier, tests/smoke runner, and cleanup scripts. Do not connect to the operational database.

The approval endpoint is not ready for operational use until the additive audit migration and trusted JWT configuration are provisioned and verified in the intended environment. The endpoint has no login/token issuance flow in the application.

## End-to-End V1 release validation — 2026-10-16

- OpenAPI now documents financial response properties for dashboard summary, payment list/summary, booking list/full detail, and approval decision. Route-specific HTTP errors are declared; the queue continues to use `GET /bookings?needs_manual_review=...`.
- 64 selected backend tests, 16 frontend tests, frontend build/lint, compileall, and `git diff --check` passed. A disposable PostgreSQL test stack was removed. No operational database was accessed.
- Remaining environment-dependent item: staging validation. Do not treat this isolated release validation as a staging or production smoke test.

Use `docs/IMPORTER_REVIEW_APPROVAL_RELEASE_CHECKLIST.md` for the complete operator release procedure. The prior disposable PostgreSQL validation passed 32/32 approval, audit, auth, and visibility tests and its resources were removed. This new isolated staging stack has not been started because `.env.staging` is empty. Provision its dedicated settings, run the preflight, and then follow the backup, migration, smoke-test, and cleanup sequence. This repository does not track applied migration versions; do not infer DB state from migration filenames. No operational DB was accessed.

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

## Website integration V1 — local validation

- A local-only adapter and opt-in Manager API now support Manager-priced quote previews and `Inquiry` submissions with idempotency. See `docs/WEBSITE_TO_MANAGER_INTEGRATION_V1.md`.
- The current E2E environment uses its own Compose project, database, volume, network, and ports. Keep it available for manual review until Daniel confirms completion.
- Backend-local hardening and the approved retention policy are tracked in `docs/WEBSITE_PUBLIC_API_HARDENING.md`. Do not expose `WEBSITE_INTEGRATION_ENABLED` publicly until proxy-level abuse controls, monitoring, the external cleanup scheduler/target, and operational provisioning are configured.
- Pricing remains sourced from active approved Manager rules. Extras without configured prices are rejected. No adult/child tariff split, payment collection, proforma generation, or booking confirmation is inferred.

## Website public API hardening — 2026-10-16

- Keep the website feature flag false in staging and production. Local backend safeguards are implemented, but process-local limits are not a replacement for distributed proxy controls.
- Approved policy: delete unconverted Website Inquiry bookings older than 30 days; use a separate 24-hour TTL for website booking idempotency. The cleanup CLI defaults to count preview and has explicit apply entrypoints; converted bookings are excluded and shared customers are retained until no booking references them.
- Before any environment schedules or runs apply mode, provision that environment's scheduler/target, verify its backup procedure, and complete release approval. No scheduler is configured and no staging/production/database was accessed. Keep the website feature flag false pending exposure approval.

## Booking Financial Workflow V1.1 — 2026-10-16

- V1.1 aligns payment statuses and booking financial derivation and displays total, optional deposit, paid, balance, and financial status in Booking Detail.
- Apply the additive nullable deposit migration through the normal release process. Do not backfill historical deposits without reviewed source data.
- Staging validation remains a separate operator-provisioning task and does not block development.

## Financial Operations Polish — 2026-10-16

- Dashboard financial KPI counts and outstanding total are returned by the backend using the canonical booking financial derivation. `depositpaid` is displayed as its own category in addition to the requested status groups. Definitions appear with each KPI.
- Payments now filters by all canonical payment statuses and sorts by paid date or due date. Collected totals are backend-derived per currency, excluding cancelled/draft, invalid, non-positive, and currency-mismatched rows; mismatch is an explicit error state.
- Bookings shows financial status, paid amount, and balance from the existing backend derivation. Booking Detail includes pending amount and handles unknown deposit, no payments, loading, API error, overdue, and currency mismatch states.
- Operational status and all existing margin formulas remain unchanged. No migration or operational DB access was required.
- Staging validation remains pending operator provisioning and is still separate from product work.
