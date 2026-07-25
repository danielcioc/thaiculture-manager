# ThaiCulture Manager — Next Steps

## Immediate goal
Recover full project continuity and continue from the actual current state, not from assumptions.

## Confirmed current state
- Docker stack starts successfully
- Backend responds on /health
- DB responds on /db-check
- Seed/demo data exists
- Frontend code is already connected to backend endpoints

## Recommended next priorities
1. Refine the canonical booking-level financial status logic so current computed values map cleanly to the intended business meanings (unpaid, depositrequested, depositpaid, partiallypaid, paid, overdue).
2. Review booking detail wording and badge presentation so payment_status and booking_financial_status remain clearly distinct in the UI.
3. Continue the financial model audit against BOOKING_FINANCIAL_WORKFLOW_V1.md, including deposit, balance, proforma, and invoice behavior.

## First commands for next session
cd ~/Projects/thaiculture-manager
docker compose up -d
curl http://localhost:8000/health
curl http://localhost:8000/db-check

## Important note
Do not restart project analysis from schema-only assumptions.
This project already has:
- working backend routes
- seeded data
- connected frontend structure
- booking detail financial/operational flow
