# Importer Review Approval Workflow v1 — Design Only

**Status:** proposed; no endpoint, schema, UI, or data changes are implemented by this document.
**Scope:** controlled correction of imported tour mappings. Booking operations, pricing, and payments remain outside this workflow.

## 1. Allowed mapping states

The only allowed `mapping_status` values are:

- `confirmed`
- `probable_manual_review`
- `unmapped`

Do not add workflow or approval states to this field. Booking `status` remains an independent operational field.

## 2. Transition rules

A reviewer may save any of these mapping decisions:

| Current state | New state | Allowed | Result |
| --- | --- | --- | --- |
| `probable_manual_review` | `confirmed` | Yes | Select an existing active canonical tour; set its `tour_id`. |
| `unmapped` | `confirmed` | Yes | Select an existing active canonical tour; set its `tour_id`. |
| `probable_manual_review` | `unmapped` | Yes | Reviewer concludes no safe canonical mapping exists; keep `tour_id` NULL. |
| `confirmed` | `probable_manual_review` | Yes, correction only | Remove the active `tour_id`; retain the raw label and require review. Reason required. |
| `confirmed` | `unmapped` | Yes, correction only | Remove the active `tour_id`; retain the raw label and require review. Reason required. |
| `confirmed` | `confirmed` with a different active `tour_id` | Yes, correction only | Replace the canonical relation. Reason required. |
| Any state | Identical mapping state and `tour_id` | Yes, no-op | Record one `import_review.noop` event; retries with the same request ID return it without another event. |

A later correction follows the same rules and always records a new audit event. A mapping can be reconfirmed after a correction. A reason is required for every state-changing decision. No transition changes the booking's operational status. Automated imports must not overwrite a human-approved mapping; import conflict behavior needs to preserve the approved state and surface a conflict for review.

## 3. Canonical `tour_id` invariant

- `confirmed` requires `tour_id` referencing an existing canonical row in `tours`.
- `probable_manual_review` and `unmapped` require `tour_id = NULL`.
- A confirmed mapping may reference only an active tour (`tours.is_active = true`).
- The selected tour is an existing canonical tour. The review endpoint never creates a tour.
- Validate the tour and update the booking within one transaction. A missing, deleted, or inactive tour is rejected.
- The probable resolver candidate is informational only. It is not an active booking relationship until an authorized reviewer confirms it.

## 4. Raw label preservation

`imported_raw_tour_name` is the immutable source label for this booking. Approval and later correction never replace it with the canonical tour name. The canonical name is displayed separately by joining the current `tour_id` to `tours.name`.

If an upstream re-import contains a different source label, it must not silently replace the preserved label after review. Handling changed source data is a separate importer policy decision.

## 5. `needs_manual_review` rule

Persist the flag, rather than deriving it at read time, so the existing review queue and API continue to use one stored value:

- `confirmed` => `false`
- `probable_manual_review` => `true`
- `unmapped` => `true`

Write `mapping_status`, `tour_id`, and `needs_manual_review` atomically. Validate their consistency in the write path. Existing nullable legacy rows require an explicit backfill/constraint plan before adding database constraints; this design does not authorize a backfill.

## 6. Audit persistence

The chosen design is to reuse the generic `audit_log` table declared in `database/init/001_schema.sql`, not create a specialized review-audit table. Its existing `user_id`, `entity_type`, `entity_id`, `action`, `old_value`, `new_value`, and `created_at` fields represent actor, booking, event type, before/after snapshots, and UTC timestamp. The table is not currently written by application code, so reuse must be implemented and tested before it is relied upon.

The minimal additive migration is recorded at `database/migrations/20261015_add_audit_log_idempotency_fields.sql`. It was applied and validated only in an isolated PostgreSQL instance; it has not been applied to the operational database:

- nullable `request_id uuid` as the idempotency key;
- nullable `request_payload_hash varchar(64)` containing the lowercase SHA-256 digest of the normalized semantic request;
- nullable `actor_email_snapshot text` and `actor_name_snapshot text` so historical identity remains interpretable if the user profile changes;
- nullable `reason text`, required by the endpoint for every state-changing review decision;
- a partial unique index on `(user_id, request_id)` where `request_id IS NOT NULL`.

These columns remain nullable for compatibility with existing generic audit rows. Review writes must provide a non-null actor, request ID, payload hash, actor snapshots, and reason. `created_at` already provides the event timestamp. No separate correlation ID is planned because the app has no request-correlation mechanism; `request_id` is specifically the idempotency key, not a general trace ID.

Proposed additive DDL:

\`\`\`sql
ALTER TABLE audit_log
  ADD COLUMN IF NOT EXISTS request_id uuid,
  ADD COLUMN IF NOT EXISTS request_payload_hash varchar(64),
  ADD COLUMN IF NOT EXISTS actor_email_snapshot text,
  ADD COLUMN IF NOT EXISTS actor_name_snapshot text,
  ADD COLUMN IF NOT EXISTS reason text;

CREATE UNIQUE INDEX IF NOT EXISTS uq_audit_log_user_request_id
  ON audit_log (user_id, request_id)
  WHERE request_id IS NOT NULL;
\`\`\`

No default, `NOT NULL`, backfill, or check constraint is present. Application validation must ensure the hash is exactly 64 lowercase hexadecimal characters for review events. The isolated validation confirmed all columns remain nullable and the partial unique index has the intended predicate.

Use `entity_type = 'booking_import_review'` and these `action` values:

- `import_review.approved` for `probable_manual_review` → `confirmed` and `unmapped` → `confirmed`;
- `import_review.corrected` for a change from one confirmed tour to another, or a confirmed mapping corrected back to either review state;
- `import_review.rejected` for `probable_manual_review` → `unmapped`.
- `import_review.noop` when the requested mapping state and tour already match the booking; `old_value` and `new_value` are identical.

For each event, `entity_id` is the booking UUID. `old_value` and `new_value` are JSON objects with the same keys: `booking_id`, `booking_code`, `imported_raw_tour_name`, `mapping_status`, `tour_id`, `tour_name`, and `needs_manual_review`. `old_value` contains the pre-update snapshot; `new_value` contains the post-update snapshot. For a NULL tour, `tour_name` is null. `reason` is stored in the dedicated column. Actor UUID is `user_id`; actor display name and email are stored in the snapshot columns.

Exact snapshot changes by decision:

| Decision | `action` | `old_value` mapping/tour/review fields | `new_value` mapping/tour/review fields |
| --- | --- | --- | --- |
| `probable_manual_review` → `confirmed` | `import_review.approved` | `probable_manual_review`, `null`, `null`, `true` | `confirmed`, selected active tour UUID, selected tour name, `false` |
| `unmapped` → `confirmed` | `import_review.approved` | `unmapped`, `null`, `null`, `true` | `confirmed`, selected active tour UUID, selected tour name, `false` |
| Confirmed tour replaced by another confirmed tour | `import_review.corrected` | `confirmed`, previous tour UUID/name, `false` | `confirmed`, replacement tour UUID/name, `false` |
| `confirmed` → `probable_manual_review` or `unmapped` | `import_review.corrected` | `confirmed`, previous tour UUID/name, `false` | target review state, `null`, `null`, `true` |
| `probable_manual_review` → `unmapped` | `import_review.rejected` | `probable_manual_review`, `null`, `null`, `true` | `unmapped`, `null`, `null`, `true` |

In each row the four listed values are, in order, `mapping_status`, `tour_id`, `tour_name`, and `needs_manual_review`. Both snapshots also contain the same booking UUID, booking code, and unchanged `imported_raw_tour_name`. Store the reviewer-supplied reason in `audit_log.reason` for every state-changing event.

Idempotency is scoped to `(user_id, request_id)` across the audit log. Canonicalize a semantic request object containing booking UUID, expected current mapping fields, target mapping state and tour UUID, and trimmed reason (empty string when omitted), using UTF-8 JSON with sorted keys and compact separators; hash those bytes with SHA-256 and store the lowercase 64-character hex digest. Normalize UUIDs to canonical lowercase text. Exclude the request ID itself from the hash. Repeating the same key with the same hash returns the original audit event/result and does not update the booking or append an event. Reusing the key with a different hash returns HTTP 409. This applies to no-op decisions too; the first no-op writes one event so its idempotency key is consumed. The unique index is authoritative under concurrent requests; on a uniqueness race, roll back and re-read the existing event to apply these same rules.

Audit entries are append-only and are not automatically purged in v1. Retain them for the lifetime of the booking and after booking deletion; any future purge requires a separately approved retention/legal policy. Viewing review audit history requires `bookings.import_review.audit.read`; approval requires `bookings.import_review.approve`. The existing schema does not enforce these permissions, so route-level server authorization is required before exposing either operation.

## 7. Visibility, approval, and confirmation

- **View:** staff already authorized to view bookings may see raw label, mapping status, review flag, and canonical tour.
- **Approve/correct:** only an authenticated active user with an explicit permission such as `bookings.import_review.approve`. The current application role/permission wiring must be inspected before implementation; do not assume a role name or treat UI visibility as authorization.
- **Explicit confirmation:** required for every decision that changes persisted mapping. The confirmation summarizes raw label, selected canonical tour, and the mapping state that will be saved.
- **Scope of effect:** a decision updates mapping metadata and, for `confirmed`, the booking's canonical `tour_id` relation. It does not alter customer, booking status, tour date, selling price, payments, invoices, assignments, or other booking fields.

If server-side identity and authorization cannot be enforced, do not expose a write endpoint until that prerequisite is implemented and separately approved.

## 8. Protections

The server must enforce all invariants regardless of UI behavior:

- Never modify `booking_status` / `bookings.status`.
- Never modify customer, price, payments, invoices, assignments, or financial summaries.
- Never store a non-NULL `tour_id` for `probable_manual_review` or `unmapped`.
- Reject an unknown, nonexistent, or inactive tour for `confirmed`.
- Never create canonical tours automatically.
- Preserve `imported_raw_tour_name`.
- Reject unsupported mapping states.
- Require a non-empty reason for every state-changing decision; an identical-state no-op may have an empty reason.
- Use a transaction and a row lock for the booking; insert the audit event in that same transaction.
- Recheck authorization and tour activity at write time.

## 9. Proposed API (design only)

### Endpoint

`POST /bookings/{booking_code}/import-review/decision`

A single decision endpoint supports approval and subsequent correction without adding status values or generic booking edit access.

### Request

```json
{
  "expected_mapping_status": "probable_manual_review",
  "expected_tour_id": null,
  "expected_needs_manual_review": true,
  "mapping_status": "confirmed",
  "tour_id": "existing-active-tour-uuid",
  "reason": "Owner verified the source label against the canonical itinerary.",
  "confirm": true,
  "request_id": "client-generated-uuid"
}
```

Rules:

- `mapping_status` must be one of the three allowed values.
- For `confirmed`, `tour_id` is required and must identify an existing active tour.
- For `probable_manual_review` or `unmapped`, `tour_id` must be omitted or null.
- `reason` is required for every state-changing decision. It is trimmed and included in the request fingerprint; a no-op may use an empty reason.
- `confirm` must be `true`.
- Expected current `mapping_status`, `tour_id`, and `needs_manual_review` provide optimistic concurrency protection; the server also locks the booking row.
- `request_id` is a required idempotency key, unique per actor/request.
- A no-op request still validates expected current values and records one `import_review.noop` audit/idempotency event; retries never add another row.

### Success response

Return the updated booking review representation and audit event identifier, for example:

```json
{
  "booking_id": "booking-uuid",
  "booking_code": "TCT-...",
  "status": "unchanged-operational-status",
  "imported_raw_tour_name": "Original source label",
  "mapping_status": "confirmed",
  "needs_manual_review": false,
  "tour_id": "existing-active-tour-uuid",
  "tour_name": "Canonical tour name",
  "review_event_id": "audit-event-uuid"
}
```

Repeated use of the same `request_id` with the same actor and identical payload returns the original successful result without another update or audit event. Reuse with a different payload returns a conflict.

### Validation and conflict errors

- `400 Bad Request`: malformed payload or missing explicit confirmation.
- `401 Unauthorized`: no authenticated identity.
- `403 Forbidden`: caller lacks review permission.
- `404 Not Found`: booking code does not exist.
- `409 Conflict`: stale expected mapping values, conflicting idempotency key, or inconsistent current state.
- `422 Unprocessable Entity`: unsupported state, wrong `tour_id`/state combination, missing/inactive tour, or missing required correction reason.

Responses must state the validation reason without changing data.

## 10. Proposed UI (design only)

1. Keep the existing booking status display separate from importer mapping status.
2. Authorized reviewers see a **Review mapping** action on bookings with `needs_manual_review = true`; users without the permission see read-only metadata only.
3. Show the preserved raw label prominently. For `probable_manual_review`, show the resolver candidate as a suggestion, clearly labeled as unapproved.
4. Offer a selector of existing active canonical tours only. Do not offer tour creation or arbitrary free-text mapping.
5. Show a review summary before save: raw label, current state/tour, proposed state/tour, and the consequences for `tour_id` and `needs_manual_review`.
6. Require an explicit confirmation action. Require a reason when correcting a confirmed mapping.
7. On success, reload booking detail and show the updated mapping plus audit timestamp/actor.
8. On stale update, inactive/deleted tour, permission failure, or validation error, preserve the form values and show a specific message; do not optimistically mutate the booking display.

## 11. Implementation prerequisites and decisions

Before implementation, configure a trusted JWT issuer and signing key, verify route-level permission enforcement, and decide how changed source labels are handled on re-import. The additive audit migration has been validated in isolation but still requires separate operational deployment authorization. This document authorizes design only; it does not authorize endpoint, UI, or operational data changes.

### Isolated audit schema compatibility validation — 2026-10-15

- Applied `database/init/001_schema.sql`, then the additive audit migration, to a dedicated temporary PostgreSQL 16 database with its own port, volume, credentials, and Compose project. Only synthetic fixture rows were used.
- Verified the five nullable columns and exact types, and verified the unique partial index on `(user_id, request_id)` applies only when `request_id IS NOT NULL`.
- A generic audit row omitting new fields inserted successfully; two generic rows with NULL request IDs coexisted. A review-shaped row with all new fields inserted. A duplicate non-NULL actor/request key was rejected.
- A deliberate exception injected after a booking update and audit insert caused both writes to roll back; a follow-up query confirmed neither change persisted.
- A temporary canonicalization harness produced identical SHA-256 hashes for semantic-equivalent payloads and different hashes for distinct payloads. A temporary SQL harness confirmed same-key/same-hash retry leaves one event and same-key/different-hash is refused. Neither harness is connected to application runtime.
- No incompatibility was found with the versioned schema. This validates schema and specified semantics only; it does not validate a production audit helper, endpoint, or concurrent request implementation. The operational database was not accessed.
