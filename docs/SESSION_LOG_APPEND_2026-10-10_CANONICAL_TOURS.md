# Session Log — 2026-10-10: Canonical tour additions

## Business decision

Confirmed that the following legacy tour labels represent real, distinct products that were missing from the canonical website catalog:

- `Khao Yai National Park – Full Day (grup)`
- `Kanchanaburi – River Kwai + Erawan Falls (grup)`

## Canonical tours added

- `WEB-027` — `Khao Yai National Park – Full Day`
- `WEB-028` — `Kanchanaburi: River Kwai & Erawan Falls`

## Booking mapping corrected

- `TCT-IMP-2026-0007` mapped to `WEB-027`.
- `TCT-IMP-2026-0008` mapped to `WEB-028`.

## Importer alignment

- Added deterministic mappings for both legacy labels in `TOUR_NAME_MAP`.
- Removed both labels from `REVIEW_REQUIRED_TOURS`.
- Future imports will map these labels to the correct canonical tours.
