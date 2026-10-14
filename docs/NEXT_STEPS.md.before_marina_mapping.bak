# ThaiCulture Manager — Next Steps

Last updated: 2026-10-10

## Confirmed current state

- Docker stack starts successfully.
- PostgreSQL contains 28 canonical tours.
- All 10 historical bookings are mapped to canonical tours.
- The two former incorrect heuristic mappings were corrected.
- `WEB-027` and `WEB-028` were added as real canonical products.
- Importer mappings are aligned with the corrected database state.
- Latest commits are pushed to `main`.

## Immediate next priority

Implement the importer review mechanism.

### Required behavior

For every imported booking, preserve or derive:

- `imported_raw_tour_name`
- `mapping_status`
- `needs_manual_review`
- canonical tour reference, when safely mapped

### Mapping statuses

- `confirmed`: deterministic mapping exists and is business-approved.
- `probable_manual_review`: best candidate exists, but business confirmation is required.
- `unmapped`: no safe mapping exists.

### Implementation rules

- Do not silently fuzzy-match unknown labels.
- Do not create canonical tours automatically from imported labels.
- Preserve the original imported label even when a canonical tour is assigned.
- Make reviewable and unmapped records visible for business review.

## Verification after implementation

Run a clean test import or a controlled update path and verify:

- all 10 existing imported bookings retain their correct canonical tours;
- unknown labels become `unmapped`;
- reviewable labels become `probable_manual_review`;
- no duplicate tours are created automatically.
