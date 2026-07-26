# ThaiCulture Manager — Project State

## Current state
- Repository branch is `main`.
- Working tree is not clean anymore because `backend/app/routers/bookings.py` has local modifications that are not yet committed.
- The current backend router still contains the booking financial status helper `compute_booking_financial_status(...)`, confirming the booking financial status work remains present in code.

## Session checkpoint
- The latest session moved from validating the original seeded demo booking flow to working with imported bookings data from the July 26 terminal session log.
- Imported bookings visible in the captured terminal state include codes such as `IMP-20251218-ALEXIS-001`, `IMP-20260216-ANDREE-003`, `IMP-20260302-CATALI-006`, and others, which confirms the import path is now a live focus area.
- The imported booking `IMP-20251218-ALEXIS-001` was verified through `/bookings/{code}/full`, and its `payment_summary.booking_financial_status` was shown as `unpaid` in the captured output.
- A reset-and-import flow was also executed in the terminal session using Docker Compose rebuild plus `scripts/importseeddata.py`, after which `/db-check` showed 10 bookings, 6 customers, 10 tours, 6 locations, and 0 payments.

## Practical meaning
- The project is no longer only in the original seed-demo validation phase; it is now also validating imported historical bookings and how they appear through the same API contract.
- Before any commit, the next session should first inspect the current diff in `backend/app/routers/bookings.py` to decide whether the uncommitted changes are intentional checkpoint-worthy work or partial edits.
