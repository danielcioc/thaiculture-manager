"""Canonical payment status normalization and booking financial derivation."""

from datetime import datetime, timezone
from decimal import Decimal


PAYMENT_STATUSES = frozenset({
    "draft",
    "requested",
    "pending",
    "paid",
    "partiallypaid",
    "overdue",
    "cancelled",
})

_PAYMENT_STATUS_ALIASES = {
    "partially paid": "partiallypaid",
    "partially_paid": "partiallypaid",
}


def normalize_payment_status(value: str) -> str:
    normalized = str(value).strip().casefold()
    normalized = _PAYMENT_STATUS_ALIASES.get(normalized, normalized)
    if normalized not in PAYMENT_STATUSES:
        raise ValueError("Unsupported payment status")
    return normalized


def payment_status_for_response(value: str, due_at=None, *, now=None) -> str:
    """Normalize legacy values and derive overdue from an expired open request."""
    try:
        status = normalize_payment_status(value)
    except ValueError:
        return str(value).strip()

    if status == "overdue":
        return status
    if status not in {"requested", "pending"} or due_at is None:
        return status

    now = now or datetime.now(timezone.utc)
    if due_at.tzinfo is None:
        due_at = due_at.replace(tzinfo=timezone.utc)
    return "overdue" if due_at < now else status


def aggregate_payment_records(payments, booking_currency, *, now=None):
    """Apply payment validity rules to records (also used by isolated unit tests)."""
    paid = Decimal("0.00")
    pending = Decimal("0.00")
    has_overdue = False
    booking_currency = str(booking_currency or "").strip().upper()
    for payment in payments:
        try:
            status = normalize_payment_status(payment.get("status", ""))
        except ValueError:
            continue
        amount = _money(payment.get("amount"))
        if amount <= 0 or str(payment.get("currency") or "").strip().upper() != booking_currency:
            continue
        response_status = payment_status_for_response(status, payment.get("due_at"), now=now)
        if status in {"paid", "partiallypaid"}:
            paid += amount
        elif status in {"requested", "pending", "overdue"}:
            pending += amount
        has_overdue = has_overdue or response_status == "overdue"
    return {"paid_amount": paid, "pending_amount": pending, "has_overdue": has_overdue}


PAYMENT_TOTALS_SQL = """
    COALESCE(SUM(CASE
        WHEN LOWER(BTRIM(p.status)) IN ('paid', 'partiallypaid', 'partially_paid', 'partially paid')
         AND p.amount > 0
         AND UPPER(BTRIM(p.currency::text)) = UPPER(BTRIM(b.currency::text))
        THEN p.amount ELSE 0 END), 0) AS paid_amount,
    COALESCE(SUM(CASE
        WHEN LOWER(BTRIM(p.status)) IN ('requested', 'pending', 'overdue')
         AND p.amount > 0
         AND UPPER(BTRIM(p.currency::text)) = UPPER(BTRIM(b.currency::text))
        THEN p.amount ELSE 0 END), 0) AS pending_amount,
    COALESCE(SUM(CASE
        WHEN LOWER(BTRIM(p.status)) IN ('paid', 'partiallypaid', 'partially_paid', 'partially paid')
         AND p.amount > 0
         AND UPPER(BTRIM(p.currency::text)) = UPPER(BTRIM(b.currency::text))
        THEN p.amount
        WHEN LOWER(BTRIM(p.status)) IN ('requested', 'pending', 'overdue')
         AND p.amount > 0
         AND UPPER(BTRIM(p.currency::text)) = UPPER(BTRIM(b.currency::text))
        THEN p.amount ELSE 0 END), 0) AS requested_amount,
    COALESCE(BOOL_OR(
        p.amount > 0
        AND UPPER(BTRIM(p.currency::text)) = UPPER(BTRIM(b.currency::text))
        AND (
            LOWER(BTRIM(p.status)) = 'overdue'
            OR (
                LOWER(BTRIM(p.status)) IN ('requested', 'pending')
                AND p.due_at IS NOT NULL
                AND p.due_at < CURRENT_TIMESTAMP
            )
        )
    ), false) AS has_overdue
"""


def dashboard_financial_kpis(rows):
    """Aggregate dashboard counts using the canonical per-booking derivation."""
    counts = {
        "unpaid": 0,
        "depositrequested": 0,
        "depositpaid": 0,
        "partiallypaid": 0,
        "paid": 0,
        "overdue": 0,
    }
    outstanding = Decimal("0.00")
    for row in rows:
        summary = booking_financial_summary(
            row["total_amount"],
            row["deposit_amount"],
            row["paid_amount"],
            row["pending_amount"],
            row["has_overdue"],
        )
        counts[summary["booking_financial_status"]] += 1
        outstanding += summary["balance_due"]
    return {**counts, "total_outstanding": outstanding}


def _money(value) -> Decimal:
    if value is None:
        return Decimal("0.00")
    result = value if isinstance(value, Decimal) else Decimal(str(value))
    return result.quantize(Decimal("0.01"))


def booking_financial_summary(
    total_amount,
    deposit_amount,
    paid_amount,
    pending_amount,
    has_overdue=False,
):
    """Derive booking financial values; operational booking status is not involved."""
    total = _money(total_amount)
    paid = max(_money(paid_amount), Decimal("0.00"))
    pending = max(_money(pending_amount), Decimal("0.00"))
    deposit = None if deposit_amount is None else max(_money(deposit_amount), Decimal("0.00"))
    balance_due = max(total - paid, Decimal("0.00"))
    requested = paid + pending

    if total > 0 and paid >= total:
        financial_status = "paid"
    elif balance_due > 0 and has_overdue:
        financial_status = "overdue"
    elif deposit is not None and deposit > 0 and paid >= deposit and paid > 0:
        financial_status = "depositpaid"
    elif paid > 0:
        financial_status = "partiallypaid"
    elif pending > 0:
        financial_status = "depositrequested"
    else:
        financial_status = "unpaid"

    payment_status_by_booking = {
        "unpaid": "Unpaid",
        "depositrequested": "Payment Requested",
        "depositpaid": "Deposit Paid",
        "partiallypaid": "Partially Paid",
        "paid": "Paid",
        "overdue": "Overdue",
    }

    return {
        "total_amount": total,
        "deposit_amount": deposit,
        "deposit_paid_amount": None if deposit is None else min(paid, deposit),
        "selling_price": total,
        "paid_amount": paid,
        "pending_amount": pending,
        "requested_amount": requested,
        "balance_due": balance_due,
        "outstanding_amount": balance_due,
        "remaining_unrequested_amount": max(total - requested, Decimal("0.00")),
        "payment_status": payment_status_by_booking[financial_status],
        "booking_financial_status": financial_status,
    }
