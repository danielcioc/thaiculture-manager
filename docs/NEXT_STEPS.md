# ThaiCulture Manager — Next Steps

## Immediate goal
Validate the business correctness of the historical tour mappings and stabilize the canonical tours workflow between the website catalog and the manager database.

## Confirmed current state
- Backend Docker image now includes the full backend context, so `import_thaiculture_data.py` is available inside the container.
- Canonical tours catalog was seeded successfully into the `tours` table.
- `tours_count` is 26.
- Historical importer now maps all 10 imported bookings to canonical tours.
- Latest confirmed DB check:
  - bookings_count: 10
  - customers_count: 6
  - payments_count: 2
  - tours_count: 26
  - locations_count: 6

## Recommended next priorities
1. Review the business correctness of heuristic mappings introduced in `TOUR_NAME_MAP`.
2. Confirm whether these mappings should remain canonical aliases:
   - `Khao Yai National Park – Full Day (grup)` -> `Jurassic Park Tour`
   - `Kanchanaburi – River Kwai + Erawan Falls (grup)` -> `Treasure of Isan`
3. Decide whether `REVIEW_REQUIRED_TOURS` should become active logic rather than a passive constant.
4. Replace the manual SQL seed approach with a durable catalog-ingestion workflow sourced from the website/catalog.
5. Add a safer reimport/update path so existing imported bookings can be backfilled without delete-and-reimport.

## Useful verification commands
cd ~/Projects/thaiculture-manager
git status --short
curl -s http://127.0.0.1:8000/db-check | python3 -m json.tool
docker compose exec -T postgres psql -U tct_admin -d thaiculture_manager -c "
select b.booking_code, t.tour_code, t.name as matched_tour
from bookings b
left join tours t on t.id = b.tour_id
where b.source ilike '%Imported%'
order by b.booking_code;
"

## Important note
Do not treat all current mappings as business-confirmed truth yet.
The import is now technically working, but at least some mappings are still heuristic and must be reviewed against the live website/catalog before being considered final.
