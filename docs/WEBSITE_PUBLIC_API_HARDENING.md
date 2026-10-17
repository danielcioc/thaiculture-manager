# Website public API hardening

Status: local implementation prepared; staging exposure is not approved. Keep `WEBSITE_INTEGRATION_ENABLED=false` in staging and production until separate approval. No staging or production services were contacted for this work.

## Implemented backend safeguards

- `WEBSITE_MAX_BODY_BYTES` defaults to 16 KiB and is enforced while reading request bodies for the website catalog, pricing, and booking routes. Oversized requests receive `413` with a generic message.
- Per-client, per-process fixed-window limits default to 60 catalog requests/minute, 20 pricing requests/minute, and 5 booking requests/minute. They are configurable with `WEBSITE_CATALOG_REQUESTS_PER_MINUTE`, `WEBSITE_PRICING_REQUESTS_PER_MINUTE`, and `WEBSITE_BOOKINGS_REQUESTS_PER_MINUTE`. `429` responses include `Retry-After` in seconds and a generic message.
- The in-memory limiter has a bounded key count. It is defense in depth only: process restarts reset counters, multiple workers do not share counters, and requests behind one proxy peer can share a bucket. The ingress proxy must enforce distributed client-aware limits using its trusted client address. Do not trust arbitrary forwarded headers at the application.
- Pydantic caps tour identifiers at 255 characters, guest counts at 30 each, extras at 20 entries and 100 characters each, customer names at 255, email at 254, and notes at 2,000 characters. Legacy callers may still send an optional deprecated phone field (maximum 50 characters); new website inquiries do not persist it. Non-empty extras remain rejected until pricing is configured.
- Website database connections use `WEBSITE_DB_CONNECT_TIMEOUT_SECONDS` (default 5) and `WEBSITE_DB_STATEMENT_TIMEOUT_MS` (default 5,000). The general request deadline is not enforced by the application; set request/header/body timeouts at the reverse proxy and ASGI ingress.
- Rejections, idempotency conflicts, rate limiting, oversized bodies, and backend errors emit fixed event names, route names, and status codes only. Logs omit request bodies, customer fields, idempotency keys, authorization headers, secrets, and database URLs.
- Existing idempotency semantics are unchanged. A successful retry with the same key/payload returns the stored response; conflicting payloads still return `409`.

The settings are read from the backend process environment. The staging Compose file does not currently forward these new limit/timeout settings, so it will use the code defaults until deployment configuration is separately reviewed. No deployment configuration is added here.

## Monitoring and alert proposals

The application does not currently export metrics or configure alerts. At the edge, count requests by route and status without recording request bodies or customer identifiers. Ship the sanitized application events to the approved log/metrics system and alert on:

- pricing or booking traffic rising materially above a measured baseline;
- sustained `409` or `422` rates, split by route;
- sustained `429` events, which can indicate abuse or overly tight limits;
- any sustained `5xx` rate (initial candidate: above 1% over five minutes, with a minimum request count to avoid noise).

Set absolute traffic and conflict thresholds after observing staging traffic. Do not enable the public feature until alert ownership, retention, and response procedures are assigned.

## Website retention policy — approved 2026-10-17

- Unconsumed quote previews: retain for 30 days after `expires_at`, then consider cleanup. The quote itself is usable for 30 minutes; the longer period supports short-term operational investigation.
- `website_booking_idempotency` rows have a separate 24-hour TTL. An identical retry within 24 hours replays the stored response; after 24 hours, reuse of the key is a new request. Expired rows are pruned in bounded batches.
- Unconverted Website Inquiry bookings (`source='Website'`, `status='Inquiry'`) are deleted when `created_at` is older than 30 days. Any booking that advanced beyond `Inquiry` is converted and excluded. Customers are deleted only after their last booking reference is removed; shared customers remain.
- The inquiry retention scope ends at Manager records. The subsequent customer conversation continues by email and is outside this workflow's data model and retention job.

Preview-only count mode was an intermediate safety step. The current entrypoint is `scripts/cleanup_website_retention.py`; preview is the default and reports counts only. Apply requires `--mode apply`, a backup reference, and explicit `--backup-verified` operator attestation. Inquiry deletion uses a transaction per booking, rechecks and locks the booking, removes child rows in FK order, deletes the booking, and deletes its customer only if no booking still references it. A failure rolls back that candidate while other candidates can proceed in bounded batches.

The repository has no standard scheduler. These commands are the documented entrypoints for an external scheduled runner; scheduling must be provisioned separately per environment and must supply an explicit target identity. Run idempotency pruning hourly and inquiry cleanup daily. Use preview first; for apply, provide the verified backup reference. No staging or production job was configured or run in this task. The staging Docker cleanup tooling is unrelated and must not be reused.

Deletion order is receipts (which reference payments/documents), then booking guests, assignments, pricing quotes, payments, costs, documents, invoices, emails, reviews, notifications, quote previews, and idempotency rows, followed by the booking and then an unreferenced customer. Generic `audit_log` entries are preserved as append-only records; they have no booking FK. If an unknown FK blocks deletion, the candidate transaction rolls back and only aggregate error/blocker counts are reported.

Example scheduled-run commands (environment supplies `DATABASE_URL`; no values belong in command lines or logs):

```sh
python3 scripts/cleanup_website_retention.py --job idempotency --mode apply --operator "Operator Name" --target-label "staging" --expected-host "<staging-db-host>" --expected-port 5432 --expected-database "<staging-db-name>" --backup-reference "<verified-backup-reference>" --backup-verified
python3 scripts/cleanup_website_retention.py --job inquiries --mode apply --operator "Operator Name" --target-label "staging" --expected-host "<staging-db-host>" --expected-port 5432 --expected-database "<staging-db-name>" --backup-reference "<verified-backup-reference>" --backup-verified
```

## Staging/proxy gate

The approved topology remains same-origin `/api/website/*` proxying. The proxy must preserve method, path, body, response status, and `Idempotency-Key`; enforce client-aware rate limits, request/header/body timeouts, body-size limits, and backend network isolation. It must not expose unrelated Manager API paths. Keep CORS empty for this same-origin route; separately hosted staff UI origins must be explicitly listed.

Before staging exposure, the external scheduler/target and verified backup process must be provisioned, and proxy rate limits, monitoring/alert ownership, and the public exposure window must be confirmed. The retention policy is approved and documented; keep the feature flag false until the other exposure gates pass.
