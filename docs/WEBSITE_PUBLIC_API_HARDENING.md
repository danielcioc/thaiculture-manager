# Website public API hardening

Status: local implementation prepared; staging exposure is not approved. Keep `WEBSITE_INTEGRATION_ENABLED=false` in staging and production until separate approval. No staging or production services were contacted for this work.

## Implemented backend safeguards

- `WEBSITE_MAX_BODY_BYTES` defaults to 16 KiB and is enforced while reading request bodies for the website catalog, pricing, and booking routes. Oversized requests receive `413` with a generic message.
- Per-client, per-process fixed-window limits default to 60 catalog requests/minute, 20 pricing requests/minute, and 5 booking requests/minute. They are configurable with `WEBSITE_CATALOG_REQUESTS_PER_MINUTE`, `WEBSITE_PRICING_REQUESTS_PER_MINUTE`, and `WEBSITE_BOOKINGS_REQUESTS_PER_MINUTE`. `429` responses include `Retry-After` in seconds and a generic message.
- The in-memory limiter has a bounded key count. It is defense in depth only: process restarts reset counters, multiple workers do not share counters, and requests behind one proxy peer can share a bucket. The ingress proxy must enforce distributed client-aware limits using its trusted client address. Do not trust arbitrary forwarded headers at the application.
- Pydantic caps tour identifiers at 255 characters, guest counts at 30 each, extras at 20 entries and 100 characters each, customer names at 255, email at 254, phone at 50, and notes at 2,000 characters. Non-empty extras remain rejected until pricing is configured.
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

## Retention proposal; approval required

- Unconsumed quote previews: retain for 30 days after `expires_at`, then consider cleanup. The quote itself is usable for 30 minutes; the longer period supports short-term operational investigation.
- Completed idempotency rows: retain for 180 days after creation, then consider cleanup. This makes the supported retry horizon explicit; retries older than that horizon could no longer replay the stored response. Do not delete rows with an incomplete response as part of routine cleanup.
- Inquiry bookings and customer PII: follow the organization's approved customer-record retention and legal policy. No automatic deletion period is assigned here because the applicable business/legal requirement is not established. Keep conversion and complaint/dispute holds in mind.

Cleanup must be a separate operator-invoked job, never an application-startup action. Before any cleanup, obtain retention approval, take and verify a backup, run a read-only count preview, delete in bounded batches with `SKIP LOCKED`, verify affected counts, and retain a cleanup record. Do not delete bookings/customers as part of quote/idempotency cleanup. No cleanup was run for this milestone.

## Staging/proxy gate

The approved topology remains same-origin `/api/website/*` proxying. The proxy must preserve method, path, body, response status, and `Idempotency-Key`; enforce client-aware rate limits, request/header/body timeouts, body-size limits, and backend network isolation. It must not expose unrelated Manager API paths. Keep CORS empty for this same-origin route; separately hosted staff UI origins must be explicitly listed.

Before staging exposure, Daniel must approve the retention periods and confirm proxy rate limits, monitoring/alert ownership, and the public exposure window. Until then, keep the feature flag false.
