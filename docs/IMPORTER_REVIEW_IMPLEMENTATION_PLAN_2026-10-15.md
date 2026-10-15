# Importer Review Mechanism — Design Note

Status: schema compatibility migration implemented and validated in isolated PostgreSQL; importer resolver unified and published. Remaining importer-review work is pending.
Scope: historical booking import review and safe re-runs. This plan does not include pricing, financial contract, Dashboard KPI, or website integration work.

## 1. Schema compatibility

### Versioned schema compared with importer and API

`database/init/001_schema.sql` defines `bookings.tour_id` as a nullable foreign key to `tours.id` and makes `booking_code` unique. The `tours` table has a unique `tour_code`, but no uniqueness constraint on `name`.

The versioned `bookings` definition does not declare the following columns:

- `imported_raw_tour_name`
- `mapping_status`
- `needs_manual_review`

However, `backend/import_thaiculture_data.py` inserts all three, and the booking list/detail queries in `backend/app/routers/bookings.py` select them. The frontend types and views also consume them. The checked-in schema therefore cannot, by itself, initialize the schema expected by the current importer and API.

This is a comparison of repository files only. The operational database will not be connected to, so the runtime catalog and whether it already has these columns remain unverified.

The additive migration `database/migrations/20261015_add_booking_import_review_metadata.sql` adds the three nullable columns with `ADD COLUMN IF NOT EXISTS`. It was applied twice successfully to isolated PostgreSQL. It has not been applied to the operational database. No default, `NOT NULL`, `CHECK`, or backfill was added.

### Non-destructive compatibility options

1. Add the three columns to the base `CREATE TABLE bookings` definition for fresh databases.
2. Provide a separate additive, repeatable migration for existing installations, using `ADD COLUMN IF NOT EXISTS`; do not drop, rename, or rewrite existing columns or rows.
3. Consider a nullable check constraint for `mapping_status` that permits only `confirmed`, `probable_manual_review`, and `unmapped`. Do not add other values. Existing-row backfill and the default/null behavior for `needs_manual_review` require review because assigning a value can change how historical bookings appear in the review queue.
4. Before applying any schema change to any non-test database, inspect its catalog, back it up, and use a transaction. This plan authorizes no such action.

### Checks in an isolated database

- Start from the checked-in schema in a dedicated test database with its own port and volume; do not reuse the operational Compose database or volume.
- Verify the base schema, then apply the additive migration twice and verify it remains safe and repeatable.
- Inspect the three column types, nullability/defaults, and allowed `mapping_status` values.
- Exercise importer and booking API queries against that schema, including existing-row nulls if allowed.
- Ensure test configuration accepts only the isolated test connection and fails closed when it is missing or points at the operational endpoint.

The implementation and tests will not connect to the operational database. No operational credentials or `.env` values should be printed or copied into test output.

## 2. Single resolver

`backend/import_rules.py::resolve_tour_mapping` should be the only source for tour-label resolution. It already returns the existing states `confirmed`, `probable_manual_review`, and `unmapped`, and identifies reviewable candidate names.

In `backend/import_thaiculture_data.py`:

- Remove or delegate its duplicate `TOUR_NAME_MAP`, `REVIEW_REQUIRED_TOURS`, and `resolve_tour_mapping` definitions.
- Import and call the resolver from `backend/import_rules.py`.
- Pass the resolved mapping result into canonical lookup rather than resolving the same label again inside `pick_tour`.
- Keep booking status and language mapping outside this resolver change. In particular, do not change `booking_status` or create additional booking or mapping statuses in this milestone.

No fuzzy matching or automatic canonical-tour creation is part of the resolver or importer.

## 3. Mapping semantics

- `confirmed`: exact approved source-label mapping. Preserve the original label, set `mapping_status=confirmed`, set `needs_manual_review=false`, and keep the canonical `tour_id` when the deterministic canonical target exists.
- `probable_manual_review`: a candidate exists but remains reviewable. Preserve the original label, set `mapping_status=probable_manual_review`, and set `needs_manual_review=true`.
- `unmapped`: no approved mapping exists. Preserve the original label, set `mapping_status=unmapped`, set `needs_manual_review=true`, leave the canonical relationship null, and do not create a tour.

**Decision required before implementation:** for `probable_manual_review`, should the booking retain the candidate canonical `tour_id` while flagged for review, as the mapping-rule document describes, or should `tour_id` remain null until manual approval? The resolver currently returns a candidate; this plan does not choose how the importer should persist that candidate.

## 4. Booking status ambiguity

For the source label `Cerere (fără răspuns)`, `backend/import_rules.py::booking_status` returns `Inquiry`, while the inline `STATUS_MAP` in `backend/import_thaiculture_data.py` returns `Pending`.

This milestone will not change `booking_status`, the inline booking-status map, or stored booking statuses. Which value is canonical remains an explicit business decision for a separate change; no new status is proposed here.

## 5. Booking idempotency

The current CSV has no `booking_code`; the importer derives one from row position. Its existing-record lookup uses customer, tour date, and pickup location, but omits the tour. That can mistake two distinct tours for the same booking when customer/date/pickup match. Conversely, row-position-derived codes can shift if the source file is reordered. The current lookup can also match rows where date and pickup are both null.

Candidate options:

1. Prefer a stable booking identifier supplied by the source export, when present; retain existing generated `TCT-IMP-2026-....` codes for the already imported records.
2. If the source has no stable identifier, use an explicitly approved composite key that includes the canonical tour reference as well as customer/date/pickup, with a defined policy for null fields and multiple same-day bookings.
3. If neither identity can distinguish a row safely, place it in review and do not insert automatically.

**Decision required before implementation:** choose the source identity and null-field behavior for rows without a source booking ID. The current composite must not be silently expanded into a new business rule. Existing ten booking codes and links must remain unchanged and must not be duplicated.

## 6. Payment idempotency

The checked-in `backend/data/imports/payments.csv` header has no `amount` column. `import_payments` reads `amount` and skips rows when it is absent, invalid, or non-positive. The importer test fixture also omits `amount` while expecting a payment insert, which conflicts with the current importer behavior.

The importer currently derives `reference` from `invoice_no`, but `invoice_no` is not documented as a unique payment identifier. One invoice could potentially have more than one payment, attempt, or transfer row; the current payment schema does not enforce uniqueness on this value. Using `invoice_no` alone as a dedupe key could therefore suppress a legitimate payment or fail to prevent duplicates across bookings.

Unapproved source-key proposal: have the source provide a stable payment-row ID, scoped by source system (for example, `(source_system, source_payment_id)`), and persist that key with an appropriate unique constraint after schema review. If the export cannot provide a stable row ID, hold payment import for review rather than infer uniqueness from `invoice_no` or a row hash.

No payment key, new payment status, or amount will be invented in this milestone. Rows without `amount` must continue to be skipped and tested as skipped unless the source format and business handling are explicitly changed later.

## 7. Test plan

Run these tests only against an isolated PostgreSQL database and pure unit tests:

- Load the ten current booking CSV fixture rows and verify their expected canonical targets/statuses against the approved mapping table, without reading or writing the operational records.
- Exercise every existing mapping status: `confirmed`, `probable_manual_review`, and `unmapped`.
- Verify an unknown tour label is `unmapped`, sets `needs_manual_review=true`, leaves `tour_id` null, and creates no canonical tour.
- Verify the raw `tour` field is stored byte-for-byte/string-for-string as received, including leading/trailing whitespace in a synthetic test row; normalization is only for lookup.
- Run the same booking import twice and verify no duplicate booking rows and stable existing booking codes/links. Cover null dates/locations and distinct tours to expose the current composite-key risk.
- Start from the versioned schema in isolated PostgreSQL, apply only the additive compatibility migration, and test importer/API queries. Reapply the migration to verify idempotence.
- Feed a payment row without `amount` and verify it is skipped with no payment insert. Do not synthesize an amount for the checked-in fixture.
- Verify payment idempotency only after a source key has been approved; before that decision, test that ambiguous rows are not inserted twice by any newly introduced path.
- Prove isolation by requiring an explicit test-only database URL, rejecting the configured operational host/port/database, and asserting that all test connections use the dedicated test database. Do not read or connect to the operational `.env` URL.

## 8. Minimal implementation order

1. Schema compatibility in an isolated database only; confirm column/backfill behavior without touching operations.
2. Unify tour resolution through `backend/import_rules.py`, after approval of the `probable_manual_review` `tour_id` behavior.
3. Add importer tests for the ten rows, the three mapping states, unknown labels, raw-label preservation, and skipped no-amount payment rows.
4. Verify repeated import behavior and booking/payment idempotency after their identity rules are approved.
5. Update mapping documentation, project state, next steps, and session log to reflect implemented behavior and remaining decisions.
6. Create a separate local implementation commit after review.
7. Push separately only after explicit approval.

The schema compatibility migration and resolver-unification checkpoint are implemented. The remaining decisions and importer idempotency/test work above remain open; no operational database, operational records, or payments were changed as part of these checkpoints.
