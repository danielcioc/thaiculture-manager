# ThaiCulture Manager — Project State

Last updated: 2026-10-13

## Purpose

ThaiCulture Manager este sistemul intern de operațiuni pentru ThaiCulture Tours. El gestionează customers, bookings, canonical tours, payments, invoices, assignments, guides, drivers, locations și rezumate operaționale/financiare.

## Current stack

- PostgreSQL 16 in Docker
- FastAPI backend
- React + TypeScript + Vite frontend
- Docker Compose local orchestration

## Current verified database state

- bookings_count: 12
- customers_count: 8
- payments_count: 3
- tours_count: 28
- locations_count: 6
- guides_count: 0
- drivers_count: 0
- assignments_count: 0

## Payments state

- 3 real payments remain in DB.
- 0 zero-amount payment artifacts remain.
- 0 padded `' Pattaya'` status artifacts remain.
- `backend/import_thaiculture_data.py` now skips payment rows without a valid positive `amount`.
- Commit for payment importer protection: `8c40160`.

## Current canonical catalog

The canonical tours catalog contains 28 active tours:

- `WEB-001` through `WEB-026`: tours sourced from the website catalog baseline
- `WEB-027`: `Khao Yai National Park – Full Day`
- `WEB-028`: `Kanchanaburi: River Kwai & Erawan Falls`

## Historical import status

All 10 imported bookings are mapped to canonical tours and remain correctly linked after catalog ingestion validation:

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

## Importer and catalog state

- Payment importer is protected against missing/invalid/zero amounts.
- Historical tour mappings for `WEB-027` and `WEB-028` are business-confirmed.
- A minimal durable catalog-ingestion workflow now exists:
  - canonical source file: `backend/data/catalog/tours.json`
  - ingestion script: `backend/ingest_catalog.py`
  - ingestion mode: idempotent upsert on `tour_code`
- Catalog ingestion was validated with:
  - dry-run success
  - real run success
  - `tours_count = 28`
  - `duplicate_codes = 0`
  - imported booking-tour links preserved
- Commit for catalog ingestion: `b9ab701`.

## Current technical debt

- Evolve catalog ingestion from local JSON export to website-sourced durable refresh.
- Decide whether `REVIEW_REQUIRED_TOURS` should remain passive or become stronger review workflow logic.
- Clarify the next durable reimport/update path for historical booking updates without delete-and-reimport.
- Continue broader business-model alignment for booking, financial workflow, and future website integration.
