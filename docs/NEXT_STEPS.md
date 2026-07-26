# ThaiCulture Manager — Next Steps

## Immediate goal
Preserve the Alexis paid checkpoint and clean up the import pipeline so payments are imported correctly without duplicates or misparsed fields.

## Recommended next priorities
1. Inspect the current diff in `backend/import_thaiculture_data.py`.
2. Patch payment parsing so `payments.csv` maps correctly into `payments`.
3. Remove duplicate or misparsed payments created during earlier import attempts.
4. Re-run the import pipeline from a clean state and confirm imported bookings still resolve correctly.
5. Keep `IMP-20251218-ALEXIS-001` as the verified payment-status checkpoint.

## Useful verification commands
cd ~/Projects/thaiculture-manager
source .venv/bin/activate
git status --short
curl -s http://127.0.0.1:8000/bookings/IMP-20251218-ALEXIS-001/full | python3 -m json.tool | sed -n '1,260p'

## Important note
Do not rerun the bootstrap script without first confirming whether it rewrites the import files.
