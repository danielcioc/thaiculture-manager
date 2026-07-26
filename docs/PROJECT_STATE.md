# ThaiCulture Manager — Project State

## Current state
- Repository branch is `main`.
- Working tree includes local modifications in the importer and imported-data files.
- The backend router still contains the booking financial status helper `compute_booking_financial_status(...)`, confirming the booking financial status work remains present in code.

## Session checkpoint
- The latest session moved from validating the original seeded demo booking flow to validating imported bookings data from the July 26 terminal session log.
- Imported bookings visible in the live API include codes such as `IMP-20251218-ALEXIS-001`, `IMP-20260216-ANDREE-003`, and `IMP-20260302-CATALI-006`.
- The imported booking `IMP-20251218-ALEXIS-001` was first verified with `payment_summary.booking_financial_status = unpaid`, then manually corrected so it now shows `payment_summary.booking_financial_status = paid` with a 6500 THB payment attached.
- The backend import path was used to load payments from the CSV import set.
- The live database now shows 11 bookings, 6 customers, 4 payments, 10 tours, and 6 locations.

## Practical meaning
- The project is no longer only in the original seed-demo validation phase; it is now also validating imported historical bookings through the same API contract.
- The imported booking `IMP-20251218-ALEXIS-001` is now the verified financial-status checkpoint and should be preserved as the current reference case.
- The backend importer still needs cleanup for payment parsing, because earlier imports produced duplicate or misparsed payment rows for other bookings.
