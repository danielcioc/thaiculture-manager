# ThaiCulture Manager — Importer Mapping Rule v1

Last updated: 2026-07-26

## Purpose

This document defines the minimum technical rule that the historical data importer must follow when importing legacy booking records.

The importer must not treat imported CSV tour labels as canonical tour products.
It must preserve raw imported wording while attempting to align records to the canonical website tour catalog.

## Required Import Outputs

For each imported booking record, the importer should preserve or derive at least:

- imported_raw_tour_name
- canonical_website_tour_id
- canonical_website_link
- canonical_english_title
- mapping_status
- needs_manual_review

## Mapping Status Values

The importer should use one of these mapping statuses:

- confirmed
- probable_manual_review
- unmapped

## Rule Order

1. Preserve the original imported tour label exactly as received.
2. Attempt deterministic lookup against the approved mapping document:
   - docs/IMPORTED_TOUR_MAPPING_V1.md
3. If mapping status is confirmed:
   - assign canonical website tour fields;
   - set needs_manual_review = false
4. If mapping status is probable_manual_review:
   - assign the best candidate canonical website tour fields;
   - set needs_manual_review = true
5. If no mapping exists:
   - leave canonical fields null;
   - set mapping_status = unmapped;
   - set needs_manual_review = true
6. Do not create new canonical tour products automatically from imported labels.

## Deterministic Matches

The following imported labels should be treated as confirmed mappings:

- Evening Ayutthaya UNESCO Temples Tour (privat) -> Evening in Ayutthaya
- Hua Hin – Bangkok Day Trip -> 1-Day Trip – Hua Hin → Bangkok
- Kui Buri National Park – Elephant Watching -> Elephant Watching in Kui Buri National Park
- Hua Hin Temple Tour – Cultural Day Trip -> Hua Hin Temple Tour
- Classic Bangkok -> Classic Bangkok
- Mystic Bangkok -> Mystic Bangkok

## Reviewable Matches

The following imported labels should be treated as probable_manual_review:

- Whale Tour -> Whale Safari
- Uthai Thani / Sacred River -> Uthai Thani Sacred River & Hidden Heritage
- Ayutthaya 5 Highlights -> Ayutthaya: 5 Essential Sights
- Amphawa Floating Market -> Amphawa: The City on Water

## Non-Goals

This rule does not yet define:
- final database schema changes;
- final admin UI behavior for review queues;
- final website booking API contract;
- final proforma generation triggers.

Those concerns should be implemented only after this importer mapping rule is accepted.

## Implementation Direction

The first safe code implementation should be intentionally small:
- add a mapping dictionary or mapping helper;
- preserve imported_raw_tour_name;
- return or store mapping_status;
- mark reviewable cases explicitly;
- avoid silent auto-creation of duplicate tours.

No importer refactor should be treated as complete unless it follows this rule.
