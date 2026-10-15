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
| Any state | Same state | Yes, idempotent | Return the current representation without duplicating audit events. |

A later correction follows the same rules and always records a new audit event. A mapping can be confirmed again after a correction. No transition changes the booking's operational status. Automated imports must not overwrite a human-approved mapping; import conflict behavior needs to preserve the approved state and surface a conflict for review.

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

## 6. Audit history

A separate append-only audit table is required. Current booking columns hold only the latest decision and cannot explain who changed it or preserve previous values.

Each event should record:

- audit event UUID;
- booking UUID and booking code snapshot;
- actor user UUID and actor display/email snapshot;
- timestamp in UTC;
- raw label reviewed (snapshot);
- previous and new `mapping_status`;
- previous and new `tour_id`;
- previous and new `needs_manual_review`;
- correction reason (required for changes from `confirmed`);
- idempotency/request UUID;
- optional request correlation ID.

Audit records must not cascade-delete when a booking or tour is removed. Keep references nullable or use snapshots where necessary. Audit insert and booking update must commit or roll back together. Read access to audit history should be restricted to users permitted to inspect booking review decisions.

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
- Require a non-empty reason for corrections away from `confirmed`.
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
- `reason` is required for every correction from a current `confirmed` state; recommended for all decisions.
- `confirm` must be `true`.
- Expected current values provide optimistic concurrency protection; the server also locks the booking row.
- `request_id` is a required idempotency key, unique per actor/request.

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

Before implementation, verify the application's authentication and permission enforcement, define the audit-table retention/access policy, and decide how changed source labels are handled on re-import. The migration must be additive and separately reviewed. This document authorizes design only; it does not authorize endpoint, UI, schema, or data changes.
