from common import ROOT


MIGRATIONS = (
    ROOT / "database/migrations/20261015_add_booking_import_review_metadata.sql",
    ROOT / "database/migrations/20261015_add_audit_log_idempotency_fields.sql",
    ROOT / "database/migrations/20261016_add_booking_deposit_amount.sql",
    ROOT / "database/migrations/20261016_add_website_quote_idempotency.sql",
)

EXPECTED_COLUMNS = {
    "bookings.imported_raw_tour_name|text|YES",
    "bookings.mapping_status|character varying|YES",
    "bookings.needs_manual_review|boolean|YES",
    "bookings.deposit_amount|numeric|YES",
    "audit_log.request_id|uuid|YES",
    "audit_log.request_payload_hash|character varying|YES",
    "audit_log.actor_email_snapshot|text|YES",
    "audit_log.actor_name_snapshot|text|YES",
    "audit_log.reason|text|YES",
    "website_quote_previews.id|uuid|NO",
    "website_quote_previews.tour_id|uuid|NO",
    "website_quote_previews.tour_code|character varying|NO",
    "website_quote_previews.tour_name|character varying|NO",
    "website_quote_previews.website_tour_id|character varying|NO",
    "website_quote_previews.tour_date|date|NO",
    "website_quote_previews.adults|integer|NO",
    "website_quote_previews.children|integer|NO",
    "website_quote_previews.extras|jsonb|NO",
    "website_quote_previews.currency|character|NO",
    "website_quote_previews.total|numeric|NO",
    "website_quote_previews.total_cost|numeric|NO",
    "website_quote_previews.minimum_price|numeric|NO",
    "website_quote_previews.rule_name|character varying|NO",
    "website_quote_previews.pricing_policy_version|character varying|NO",
    "website_quote_previews.breakdown|jsonb|NO",
    "website_quote_previews.expires_at|timestamp with time zone|NO",
    "website_quote_previews.consumed_booking_id|uuid|YES",
    "website_quote_previews.created_at|timestamp with time zone|NO",
    "website_booking_idempotency.idempotency_key|uuid|NO",
    "website_booking_idempotency.payload_hash|character varying|NO",
    "website_booking_idempotency.booking_id|uuid|YES",
    "website_booking_idempotency.response_payload|jsonb|YES",
    "website_booking_idempotency.created_at|timestamp with time zone|NO",
}

EXPECTED_INDEXES = {
    "uq_audit_log_user_request_id": ("audit_log", "(user_id, request_id)", "request_id IS NOT NULL"),
    "idx_website_quote_previews_expires_at": ("website_quote_previews", "(expires_at)", ""),
}


def schema_gaps(lines: list[str]) -> tuple[set[str], set[str]]:
    columns = {line for line in lines if not line.startswith("INDEX|")}
    missing_columns = EXPECTED_COLUMNS - columns
    missing_indexes = set()
    for name, (table, *required_fragments) in EXPECTED_INDEXES.items():
        candidates = [line for line in lines if line.startswith(f"INDEX|{table}|{name}|")]
        if not any(all(fragment in line for fragment in required_fragments) for line in candidates):
            missing_indexes.add(name)
    return missing_columns, missing_indexes
