# ThaiCulture Manager — Decisions

## Continuity decision
Project continuity must not depend on assistant memory alone.
Project state must be stored inside repository/project files.

## Documentation rule
At the end of each meaningful work session, update:
- docs/PROJECT_STATE.md
- docs/NEXT_STEPS.md
- docs/SESSION_LOG.md
- docs/DECISIONS.md only when decisions change

## Product understanding
ThaiCulture Manager is an internal operations dashboard, not just a schema experiment.

## Technical understanding
The current local architecture is:
- Docker Compose
- PostgreSQL
- FastAPI
- React/Vite frontend

## Demo understanding
The current seed data is centered on a realistic example booking:
TCT-2026-000001

This booking should remain available as a reference flow unless intentionally replaced by richer seed data.

## Recovery rule
When starting a new session:
1. Read docs/PROJECT_STATE.md
2. Read docs/NEXT_STEPS.md
3. Read the latest section in docs/SESSION_LOG.md
4. Only then inspect code
