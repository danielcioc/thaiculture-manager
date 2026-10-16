# Continuous integration

`.github/workflows/ci.yml` runs on pull requests targeting `main` and pushes to `main`. It has `contents: read` permission only and performs no deployment or database setup.

## Runtime choices

The repository does not pin Python or Node versions. CI uses Python 3.12 with the exact package versions in `backend/requirements.txt`. CI uses Node 22; the locked Vite package requires Node `^20.19.0 || >=22.12.0`. Frontend dependencies are installed from `frontend/package-lock.json` with `npm ci`.

## Checks

- Backend: `python -m unittest discover -s tests -p 'test_*.py' -v` from `backend/`. CI provides an ephemeral PostgreSQL 16 service named `thaiculture_test`, with synthetic credentials and no reused data. `DATABASE_URL` and `TCT_TEST_DATABASE_URL` point only to that service. Locally, leave `TCT_TEST_DATABASE_URL` unset/empty to skip database-backed tests unless using a disposable test database.
- Staging tooling: `python -m unittest discover -s scripts/staging -p 'test_staging_tools.py' -v`. These tests use mocked Compose/Docker inventory and synthetic configuration; they do not start services or contact staging.
- Python compilation: `python -m compileall -q backend/app backend/tests scripts/staging`.
- Whitespace: `git diff --check` and a check of the event's commit range.
- Frontend: `npm test`, `npm run build`, and `npm run lint`. The build script already invokes `tsc -b`; there is no separate TypeScript script.

## Current baseline

The importer payment fixture includes a synthetic positive amount when asserting an insert, and a separate test asserts that a source row without an amount is skipped. A local run without a database passed 56 tests and skipped 30 PostgreSQL integration tests. The PostgreSQL service is ephemeral and contains synthetic test data only; it is not staging or production. The workflow has not yet run on GitHub.
