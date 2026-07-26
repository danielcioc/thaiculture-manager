# ThaiCulture Manager — Next Steps

## Immediate goal
Continue from the imported-bookings validation state and decide whether the current backend router change should be preserved, completed, or reverted.

## Recommended next priorities
1. Inspect the exact uncommitted diff in `backend/app/routers/bookings.py`.
2. Re-run the key API checks for imported bookings, especially `/bookings` and `/bookings/{code}/full`.
3. Decide whether imported payments should remain absent after the reset-and-import run or whether payment import logic must be fixed next.
4. Reconcile the imported flow with the canonical booking financial workflow definitions in `docs/BOOKING_FINANCIAL_WORKFLOW_V1.md`.

## First commands for next session
cd ~/Projects/thaiculture-manager
git diff -- backend/app/routers/bookings.py
curl -s http://127.0.0.1:8000/bookings | python3 -m json.tool | sed -n '1,260p'
curl -s http://127.0.0.1:8000/bookings/IMP-20251218-ALEXIS-001/full | python3 -m json.tool | sed -n '1,280p'
curl -s http://127.0.0.1:8000/db-check

## Important note
Do not assume the seed-demo reference booking is the only validation path anymore.
The imported dataset is now part of the active continuity state.
