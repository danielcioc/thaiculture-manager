# ThaiCulture Manager — Next Steps

## Update 2026-10-13

- Confirmed: `Khao Yai National Park – Full Day (grup)` maps to `WEB-027 Khao Yai National Park – Full Day`.
- Confirmed: `Kanchanaburi – River Kwai + Erawan Falls (grup)` maps to `WEB-028 Kanchanaburi: River Kwai & Erawan Falls`.
- The historical tour mappings are now business-confirmed.

Last updated: 2026-10-13

## Confirmed current state

- Importer review mechanism is implemented.
- All 10 imported bookings have canonical tours.
- All 10 imported bookings are marked `confirmed` and `needs_manual_review = false`.
- Marina mapping is business-confirmed: `Whale Tour (nespecificat)` -> `WEB-016 Whale Safari`.
- Alexis payment checkpoint is verified: 6,500 THB cash, reference `TCT-TH-2025-1218-001`.
- Backend tests pass: 10 tests, OK.
- Database connectivity is healthy.

## Current status

- Importer review mechanism is implemented.
- All 10 imported bookings have canonical tours.
- All 10 imported bookings are marked `confirmed` and `needs_manual_review = false`.
- Marina mapping is business-confirmed: `Whale Tour (nespecificat)` -> `WEB-016 Whale Safari`.
- Alexis payment checkpoint is verified: 6,500 THB cash, reference `TCT-TH-2025-1218-001`.
- The two former zero-amount payment artifacts were removed through a controlled cleanup.
- Payment importer now skips rows without a valid positive amount.
- Backend tests pass: 10 tests, OK.
- Database connectivity is healthy.

## Next steps

1. Keep the importer guard in place.
2. Review any future heuristic tour mappings before marking them canonical.
3. Maintain durable catalog ingestion and safer reimport/update workflow.
