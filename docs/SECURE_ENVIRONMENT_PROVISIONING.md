# Secure Environment Provisioning

This document describes configuration names and handling rules only. It contains no secret values.

## Backend settings

The backend `Settings` model accepts these environment variables:

- `DATABASE_URL` — required complete PostgreSQL connection URL for the backend process.
- `AUTH_JWT_SECRET` — signing/verification secret used by protected authentication dependencies. Protected requests fail closed when verifier configuration is incomplete. Use a randomly generated secret of at least 32 bytes.
- `AUTH_JWT_ISSUER` — exact trusted JWT issuer identifier.
- `AUTH_JWT_AUDIENCE` — exact audience expected by this API.

The JWT issuer and audience must come from the trusted identity provider configuration. Do not infer them from a token supplied by a client.

`THAICULTURE_DB_PASSWORD` is not a backend `Settings` field. The current Docker Compose file uses it only for Compose interpolation when configuring the Postgres container and constructing the backend's `DATABASE_URL`. If this Compose-only key is placed in a dotenv file that Pydantic Settings loads, it is treated as an unknown setting and rejected. For a local backend process, provide the supported `DATABASE_URL` setting. Do not relax `extra_forbidden` to hide this mismatch.

There is a configuration boundary to resolve in a separate change: Compose currently requires `THAICULTURE_DB_PASSWORD`, while the backend accepts `DATABASE_URL`. Do not replace the Compose variable or change its behavior by assumption. Provision Compose interpolation and backend process settings through their respective mechanisms until an explicit configuration change defines a shared approach.

## Environment separation

- **Local development:** use a local-only environment file or process environment. Keep application settings separate from Compose-only interpolation values when the same dotenv file would be loaded by Pydantic Settings.
- **Tests:** use disposable, isolated credentials and databases. Database integration tests must receive their dedicated test URL (for example, `TCT_TEST_DATABASE_URL`) and must not point at an operational database. Unit tests should use mocks and synthetic signing keys only.
- **Production:** provision each setting through the deployment platform's secret/configuration manager. Use production-specific database credentials and JWT configuration; never reuse local or test credentials.

Do not copy values between environments. Keep `.env` and `.env.*` files local and untracked. `.env.example` may be tracked only when it contains key names and non-secret placeholders, never usable credentials.

## Rotation and incident handling

Treat any secret exposed in a traceback, terminal capture, log, issue, or commit as compromised, even if truncated. An operator must rotate it at the issuing service, update every dependent deployment/configuration, restart affected services as appropriate, and verify the old credential no longer works. Do not put the old or replacement value in this repository, a commit, a report, or logs.

Rotate database credentials at PostgreSQL and update the Compose/backend provisioning that consumes them. Rotate `AUTH_JWT_SECRET` through the approved deployment process; coordinate rotation with token validity and issuer behavior because changing the key can invalidate tokens. Do not rotate automatically as part of this documentation change.

## Git and logging rules

- Never commit secret values or complete connection URLs containing credentials.
- Never print `.env` contents, secret-bearing environment variables, authorization headers, tokens, or credential-bearing exceptions.
- Log configuration presence or validation categories only, not values.
- `.gitignore` excludes `.env` and `.env.*`, with an exception for `.env.example`. Ignore rules do not remove files already tracked; review tracked backup files separately and do not untrack them without an explicit decision.

## Current provision-before-use checklist

Before enabling protected approval routes in a deployment, an operator must provision `AUTH_JWT_SECRET`, `AUTH_JWT_ISSUER`, `AUTH_JWT_AUDIENCE`, and `DATABASE_URL` in the appropriate environment. The trusted issuer and audience must be confirmed with the identity provider. Resolve the Compose-only `THAICULTURE_DB_PASSWORD` versus backend `DATABASE_URL` boundary before relying on a shared dotenv file for both systems.

For the complete operator-owned backup, migration inspection/application, permission, smoke-test, and rollback procedure for importer review approval, see [IMPORTER_REVIEW_APPROVAL_RELEASE_CHECKLIST.md](IMPORTER_REVIEW_APPROVAL_RELEASE_CHECKLIST.md). The procedure does not print secret values and does not run automatically.

## Local isolated approval staging

The dedicated local Compose definition is `docker-compose.staging.yml`, with project name `thaiculture-staging-approval`, isolated named network/volume/containers, and localhost-only ports distinct from the default stack. Provision a separate `.env.staging` file with the required setting names through the operator's trusted local process; never copy values from another environment. Keep file permissions at `0600` and leave the file untracked.

Run `python3 scripts/staging/preflight.py` first. It reports setting presence and resource names only, validates that the database URL resolves to the isolated Compose PostgreSQL service and fixed test database, and blocks on project, container, port, network, or volume conflicts. It does not start Compose. Only after it reports READY, start with `python3 scripts/staging/up.py`. Before migrations or mutable tests, create and verify a custom-format backup with `python3 scripts/staging/backup.py`. Use `python3 scripts/staging/verify_migrations.py` to inspect schema, or pass `--apply-missing --backup <verified-backup-path>` after the backup requirement is met. `python3 scripts/staging/run_tests.py` runs the database-backed test set; `python3 scripts/staging/smoke_approval.py` runs the focused approval suite; `python3 scripts/staging/cleanup.py` removes only Compose resources carrying this project's explicit staging labels.
