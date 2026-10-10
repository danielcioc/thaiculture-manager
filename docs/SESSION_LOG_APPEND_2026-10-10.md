# Session Log — 2026-10-10

## Tour mapping correction

- Reviewed the live website catalog at https://thaiculture.tours/en/tours.html.
- Confirmed the catalog contains 26 tours, matching the 26 canonical tours seeded in the manager database.
- Removed two incorrect heuristic mappings from `TOUR_NAME_MAP`:
  - `Khao Yai National Park – Full Day (grup)` -> `Jurassic Park Tour`
  - `Kanchanaburi – River Kwai + Erawan Falls (grup)` -> `Treasure of Isan`
- Added both imported labels to `REVIEW_REQUIRED_TOURS`.
- Updated `pick_tour()` so labels in `REVIEW_REQUIRED_TOURS` return `None` and do not receive a fuzzy tour match.
- Set `tour_id = NULL` for bookings `TCT-IMP-2026-0007` and `TCT-IMP-2026-0008`.
- These bookings remain intentionally unmapped until the correct tour product or a new canonical tour is confirmed.

## Next decision

Decide whether the two legacy labels represent:
- existing canonical tours under different names;
- new canonical tours that must be added to the catalog;
- cancelled, duplicated, or non-bookable historical records.
