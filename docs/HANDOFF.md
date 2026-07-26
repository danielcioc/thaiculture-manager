# ThaiCulture Manager — Handoff

## Current task
Stabilize historical booking import so imported bookings map to the canonical tours catalog used by the website.

## Last confirmed state
- Backend Docker image now copies the full backend context via `COPY . .`
- Import script path issue is resolved inside the container
- Canonical tours catalog was seeded into `tours`
- `tours_count` is now 26
- Historical importer was updated to use explicit `TOUR_NAME_MAP`
- Importer now maps all 10 imported bookings to canonical tours
- Current DB check after clean reimport:
  - bookings_count: 10
  - customers_count: 6
  - payments_count: 2
  - tours_count: 26
  - locations_count: 6
- Confirmed imported booking mappings:
  - TCT-IMP-2026-0001 -> WEB-006 Evening in Ayutthaya
  - TCT-IMP-2026-0002 -> WEB-016 Whale Safari
  - TCT-IMP-2026-0003 -> WEB-023 Hua Hin Temple Tour
  - TCT-IMP-2026-0004 -> WEB-021 1-Day Trip – Hua Hin → Bangkok
  - TCT-IMP-2026-0005 -> WEB-022 Elephant Watching in Kui Buri National Park
  - TCT-IMP-2026-0006 -> WEB-007 Ayutthaya: 5 Essential Sights
  - TCT-IMP-2026-0007 -> WEB-010 Jurassic Park Tour
  - TCT-IMP-2026-0008 -> WEB-015 Treasure of Isan
  - TCT-IMP-2026-0009 -> WEB-012 Amphawa: The City on Water
  - TCT-IMP-2026-0010 -> WEB-007 Ayutthaya: 5 Essential Sights

## Files changed
- backend/Dockerfile
- backend/import_thaiculture_data.py
- backend/data/sql/seed_canonical_tours.sql

## Important implementation notes
- `ROOT` in importer now points to `Path(__file__).resolve().parent`
- importer falls back to `row.get("booking_code") or row.get("bookingcode") or f"TCT-IMP-2026-{idx:04d}"`
- importer source now uses `row.get("source") or "Imported CSV"`
- `pick_tour()` now tries exact canonical-name match before fuzzy fallback
- Some mappings are still business assumptions and should be reviewed later:
  - Khao Yai National Park – Full Day (grup) -> Jurassic Park Tour
  - Kanchanaburi – River Kwai + Erawan Falls (grup) -> Treasure of Isan

## Recommended next task
Review business correctness of the remaining heuristic tour mappings against the live website/catalog and decide whether any canonical tours or aliases should be adjusted.

## Restart rule
At the next session start, read in this order:
- docs/PROJECT_STATE.md
- docs/NEXT_STEPS.md
- docs/SESSION_LOG.md
- docs/DECISIONS.md
- docs/HANDOFF.md
