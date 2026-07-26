# ThaiCulture Manager — Decisions

## Continuity decision
Project continuity must not depend on assistant memory alone.
Project state must be stored inside repository/project files.

## Documentation rule
At the end of each meaningful work session, update:
- `docs/PROJECT_STATE.md`
- `docs/NEXT_STEPS.md`
- `docs/SESSION_LOG.md`
- `docs/HANDOFF.md`
- `docs/DECISIONS.md` only when decisions change

## Product understanding
ThaiCulture Manager is an internal operations dashboard, not just a schema experiment.

## Technical understanding
The current local architecture is:
- Docker Compose
- PostgreSQL
- FastAPI
- React/Vite frontend

## Validation model decision
Continuity must track both:
- the original seeded demo flow centered on `TCT-2026-000001`
- the imported bookings validation flow centered on real imported records such as `IMP-20251218-ALEXIS-001`

## Recovery rule
When starting a new session:
1. Read `docs/PROJECT_STATE.md`
2. Read `docs/NEXT_STEPS.md`
3. Read the latest section in `docs/SESSION_LOG.md`
4. Read `docs/HANDOFF.md`
5. Only then inspect code
