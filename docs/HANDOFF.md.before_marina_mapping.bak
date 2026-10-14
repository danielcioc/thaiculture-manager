# ThaiCulture Manager — Handoff

Last updated: 2026-10-10

## Current state

The historical booking import is stable and all 10 imported bookings are mapped to canonical tours.

The canonical catalog contains 28 tours:

- `WEB-001` through `WEB-026`: website catalog tours.
- `WEB-027`: `Khao Yai National Park – Full Day`
- `WEB-028`: `Kanchanaburi: River Kwai & Erawan Falls`

## Corrected mappings

The former incorrect heuristic mappings were removed:

- `Khao Yai National Park – Full Day (grup)` no longer maps to `Jurassic Park Tour`.
- `Kanchanaburi – River Kwai + Erawan Falls (grup)` no longer maps to `Treasure of Isan`.

They now map to:

- `WEB-027 Khao Yai National Park – Full Day`
- `WEB-028 Kanchanaburi: River Kwai & Erawan Falls`

## Database corrections applied

- `TCT-IMP-2026-0007` is mapped to `WEB-027`.
- `TCT-IMP-2026-0008` is mapped to `WEB-028`.
- No imported booking remains without a canonical tour.

## Importer state

`backend/import_thaiculture_data.py` contains deterministic mappings for both corrected legacy labels.

`REVIEW_REQUIRED_TOURS` still contains:

- `Whale Tour`
- `Uthai Thani / Sacred River`
- `Ayutthaya 5 Highlights`
- `Amphawa Floating Market`

It is not yet connected to persistent review metadata.

## Next task

Implement persistent importer review metadata:

- `imported_raw_tour_name`
- `mapping_status`
- `needs_manual_review`

Do not silently fuzzy-match unknown tour labels. Mark unknown labels as `unmapped` and reviewable labels as `probable_manual_review`.
