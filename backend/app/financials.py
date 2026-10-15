"""Shared payment aggregation and booking financial summary rules."""


PAYMENT_TOTALS_SQL = """
    COALESCE(SUM(CASE WHEN status = 'Paid' THEN amount ELSE 0 END), 0) AS paid_amount,
    COALESCE(SUM(CASE WHEN status = 'Pending' THEN amount ELSE 0 END), 0) AS pending_amount,
    COALESCE(SUM(CASE WHEN status IN ('Paid', 'Pending') THEN amount ELSE 0 END), 0) AS requested_amount
"""


def booking_financial_summary(selling_price, paid_amount, pending_amount):
    """Return the agreed v1 totals and financial status from payment totals."""
    selling_price = selling_price or 0
    paid_amount = paid_amount or 0
    pending_amount = pending_amount or 0
    requested_amount = paid_amount + pending_amount

    if selling_price > 0 and paid_amount >= selling_price:
        financial_status = "paid"
    elif paid_amount > 0:
        financial_status = "partiallypaid"
    elif pending_amount > 0:
        financial_status = "depositrequested"
    else:
        financial_status = "unpaid"

    if paid_amount <= 0 and pending_amount <= 0:
        payment_status = "Unpaid"
    elif selling_price > 0 and paid_amount >= selling_price:
        payment_status = "Paid"
    elif paid_amount > 0:
        payment_status = "Partially Paid"
    else:
        payment_status = "Payment Requested"

    return {
        "paid_amount": paid_amount,
        "pending_amount": pending_amount,
        "requested_amount": requested_amount,
        "outstanding_amount": selling_price - paid_amount,
        "remaining_unrequested_amount": selling_price - requested_amount,
        "payment_status": payment_status,
        "booking_financial_status": financial_status,
    }
