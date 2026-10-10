# ThaiCulture Manager — Project State

Last updated: 2026-10-10

## Purpose

ThaiCulture Manager is the internal operations system for ThaiCulture Tours. It manages customers, bookings, canonical tours, payments, invoices, assignments, guides, drivers, locations, and operational/financial summaries.

## Current stack

- PostgreSQL 16 in Docker
- FastAPI backend
- React + TypeScript + Vite frontend
- Docker Compose local orchestration

## Current canonical catalog

The canonical tours catalog now contains 28 active tours:

- `WEB-001` through `WEB-026`: tours sourced from the live website catalog.
- `WEB-027`: `Khao Yai National Park – Full Day`
- `WEB-028`: `Kanchanaburi: River Kwai & Erawan Falls`

`WEB-027` and `WEB-028` were added because historical booking labels represented real products that were not present in the original 26-tour website catalog.

## Historical import status

All 10 imported bookings are mapped to canonical tours:

- `TCT-IMP-2026-0001` -> `WEB-006 Evening in Ayutthaya`
- `TCT-IMP-2026-0002` -> `WEB-016 Whale Safari`
- `TCT-IMP-2026-0003` -> `WEB-023 Hua Hin Temple Tour`
- `TCT-IMP-2026-0004` -> `WEB-021 1-Day Trip – Hua Hin → Bangkok`
- `TCT-IMP-2026-0005` -> `WEB-022 Elephant Watching in Kui Buri National Park`
- `TCT-IMP-2026-0006` -> `WEB-007 Ayutthaya: 5 Essential Sights`
- `TCT-IMP-2026-0007` -> `WEB-027 Khao Yai National Park – Full Day`
- `TCT-IMP-2026-0008` -> `WEB-028 Kanchanaburi: River Kwai & Erawan Falls`
- `TCT-IMP-2026-0009` -> `WEB-012 Amphawa: The City on Water`
- `TCT-IMP-2026-0010` -> `WEB-007 Ayutthaya: 5 Essential Sights`

## Importer mapping state

`backend/import_thaiculture_data.py` now uses deterministic mappings in `TOUR_NAME_MAP`.

The two former incorrect heuristic mappings were removed:

- `Khao Yai National Park – Full Day (grup)` no longer maps to `Jurassic Park Tour`.
- `Kanchanaburi – River Kwai + Erawan Falls (grup)` no longer maps to `Treasure of Isan`.

They now map to the new canonical tours `WEB-027` and `WEB-028`.

`REVIEW_REQUIRED_TOURS` remains a passive review list for labels that require business validation. It does not yet write a persistent `mapping_status` or `needs_manual_review` field.

## Current technical debt

- `REVIEW_REQUIRED_TOURS` is not yet connected to persistent review metadata.
- The importer still relies on fuzzy matching as a fallback for unknown tour labels.
- The canonical catalog seed is still manual SQL rather than a durable website/catalog ingestion workflow.
- Invoice CSV parsing is still disabled in the importer.
- Booking financial status is not yet exposed in the booking full-detail API contract.

## Next implementation priority

Implement the importer review mechanism:

1. Preserve the original imported tour label.
2. Add `mapping_status`: `confirmed`, `probable_manual_review`, or `unmapped`.
3. Add `needs_manual_review`.
4. Prevent silent fuzzy matching for unknown labels.
5. Provide a safe review/update workflow for unmapped historical bookings.
