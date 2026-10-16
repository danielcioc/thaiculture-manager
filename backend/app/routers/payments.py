from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field, field_validator
from typing import Literal, Optional
from uuid import UUID
from decimal import Decimal
from datetime import datetime

from app.database import get_connection
from app.financials import normalize_payment_status, payment_status_for_response
from app.response_models import (
    API_ERROR_RESPONSES,
    PaymentListResponse,
    PaymentResponse,
    PaymentsSummaryResponse,
)

router = APIRouter(prefix="/payments", tags=["Payments"])


class PaymentCreate(BaseModel):
    booking_id: UUID
    amount: Decimal = Field(..., gt=0, max_digits=12, decimal_places=2, examples=["3000.00"])
    currency: str = Field(default="THB", min_length=3, max_length=3)
    method: str = Field(..., min_length=1, max_length=40, examples=["Thai QR"])
    status: str = Field(default="pending", min_length=1, max_length=40, examples=["pending"])
    paid_at: Optional[datetime] = None
    due_at: Optional[datetime] = None
    reference: Optional[str] = None
    notes: Optional[str] = None

    @field_validator("status")
    @classmethod
    def validate_status(cls, value):
        try:
            return normalize_payment_status(value)
        except ValueError as exc:
            raise ValueError(str(exc)) from exc

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value):
        normalized = value.strip().upper()
        if len(normalized) != 3 or not normalized.isalpha():
            raise ValueError("Currency must be a three-letter code")
        return normalized


_RESPONSE_STATUS_SQL = """CASE
    WHEN LOWER(BTRIM(p.status)) = 'overdue'
      OR (LOWER(BTRIM(p.status)) IN ('requested', 'pending') AND p.due_at IS NOT NULL AND p.due_at < CURRENT_TIMESTAMP)
    THEN 'overdue'
    WHEN LOWER(BTRIM(p.status)) IN ('partially_paid', 'partially paid') THEN 'partiallypaid'
    ELSE LOWER(BTRIM(p.status))
END"""


def _payment_response(row, columns):
    item = dict(zip(columns, row))
    item["status"] = payment_status_for_response(item["status"], item.get("due_at"))
    item["currency_matches_booking"] = (
        str(item.get("currency") or "").strip().upper()
        == str(item.get("booking_currency") or "").strip().upper()
    )
    item["financial_error"] = None if item["currency_matches_booking"] else "currency_mismatch"
    return item


@router.get(
    "",
    response_model=PaymentListResponse,
    response_model_exclude_unset=True,
    responses={422: API_ERROR_RESPONSES[422]},
)
def list_payments(
    status: Optional[str] = None,
    sort_by: Literal["paid_at", "due_at"] = "paid_at",
    sort_order: Literal["asc", "desc"] = "desc",
):
    normalized_status = None
    if status:
        try:
            normalized_status = normalize_payment_status(status)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
    sort_column = "p.paid_at" if sort_by == "paid_at" else "p.due_at"
    sort_direction = "ASC" if sort_order == "asc" else "DESC"
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(f"""
                SELECT
                    p.id,
                    p.booking_id,
                    b.booking_code,
                    c.display_name AS customer_name,
                    p.amount,
                    p.currency,
                    p.method,
                    p.status,
                    p.paid_at,
                    p.due_at,
                    p.reference,
                    p.notes,
                    b.currency AS booking_currency
                FROM payments p
                LEFT JOIN bookings b ON b.id = p.booking_id
                LEFT JOIN customers c ON c.id = b.customer_id
                WHERE (%s::text IS NULL OR ({_RESPONSE_STATUS_SQL}) = %s)
                ORDER BY {sort_column} {sort_direction} NULLS LAST, b.created_at DESC
                LIMIT 100;
            """, (normalized_status, normalized_status))
            rows = cur.fetchall()
            columns = [desc[0] for desc in cur.description]

    return {
        "count": len(rows),
        "filters": {"status": normalized_status, "sort_by": sort_by, "sort_order": sort_order},
        "items": [_payment_response(row, columns) for row in rows],
    }


@router.get(
    "/summary",
    response_model=PaymentsSummaryResponse,
    response_model_exclude_unset=True,
)
def payments_summary():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(f"""
                SELECT
                    UPPER(BTRIM(p.currency::text)) AS currency,
                    COUNT(*) FILTER (WHERE ({_RESPONSE_STATUS_SQL}) = 'draft') AS draft_count,
                    COUNT(*) FILTER (WHERE ({_RESPONSE_STATUS_SQL}) = 'requested') AS requested_count,
                    COUNT(*) FILTER (WHERE ({_RESPONSE_STATUS_SQL}) = 'pending') AS pending_count,
                    COUNT(*) FILTER (WHERE ({_RESPONSE_STATUS_SQL}) = 'paid') AS paid_count,
                    COUNT(*) FILTER (WHERE ({_RESPONSE_STATUS_SQL}) = 'partiallypaid') AS partiallypaid_count,
                    COUNT(*) FILTER (WHERE ({_RESPONSE_STATUS_SQL}) = 'overdue') AS overdue_count,
                    COUNT(*) FILTER (WHERE ({_RESPONSE_STATUS_SQL}) = 'cancelled') AS cancelled_count,
                    COUNT(*) FILTER (WHERE UPPER(BTRIM(p.currency::text)) <> UPPER(BTRIM(b.currency::text))) AS currency_mismatch_count,
                    COALESCE(SUM(p.amount) FILTER (
                        WHERE ({_RESPONSE_STATUS_SQL}) IN ('paid', 'partiallypaid')
                          AND p.amount > 0
                          AND UPPER(BTRIM(p.currency::text)) = UPPER(BTRIM(b.currency::text))
                    ), 0) AS collected_amount
                FROM payments p
                JOIN bookings b ON b.id = p.booking_id
                GROUP BY UPPER(BTRIM(p.currency::text))
                ORDER BY currency;
            """)
            rows = cur.fetchall()
            columns = [desc[0] for desc in cur.description]
    return {"currencies": [dict(zip(columns, row)) for row in rows]}


@router.post(
    "",
    response_model=PaymentResponse,
    response_model_exclude_unset=True,
    responses={code: detail for code, detail in API_ERROR_RESPONSES.items() if code in {400, 404, 422}},
)
def create_payment(payload: PaymentCreate):
    with get_connection() as conn:
        with conn.cursor() as cur:
            try:
                cur.execute("SELECT currency FROM bookings WHERE id = %s", (payload.booking_id,))
                booking = cur.fetchone()
                if booking is None:
                    raise HTTPException(status_code=404, detail="Booking not found")
                if str(booking[0]).strip().upper() != payload.currency:
                    raise HTTPException(status_code=422, detail="Payment currency must match booking currency")
                cur.execute("""
                    INSERT INTO payments (
                        booking_id,
                        amount,
                        currency,
                        method,
                        status,
                        paid_at,
                        due_at,
                        reference,
                        notes
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING
                        id,
                        booking_id,
                        amount,
                        currency,
                        method,
                        status,
                        paid_at,
                        due_at,
                        reference,
                        notes;
                """, (
                    payload.booking_id,
                    payload.amount,
                    payload.currency,
                    payload.method,
                    payload.status,
                    payload.paid_at,
                    payload.due_at,
                    payload.reference,
                    payload.notes,
                ))

                row = cur.fetchone()
                columns = [desc[0] for desc in cur.description]
                conn.commit()

            except Exception as exc:
                conn.rollback()
                if isinstance(exc, HTTPException):
                    raise
                raise HTTPException(status_code=400, detail=str(exc))

    result = dict(zip(columns, row))
    result["status"] = payment_status_for_response(result["status"], result.get("due_at"))
    return result


@router.get("/booking/{booking_code}")
def list_payments_for_booking(booking_code: str):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    p.id,
                    p.booking_id,
                    b.booking_code,
                    c.display_name AS customer_name,
                    p.amount,
                    p.currency,
                    p.method,
                    p.status,
                    p.paid_at,
                    p.due_at,
                    p.reference,
                    p.notes,
                    b.currency AS booking_currency
                FROM payments p
                LEFT JOIN bookings b ON b.id = p.booking_id
                LEFT JOIN customers c ON c.id = b.customer_id
                WHERE b.booking_code = %s
                ORDER BY p.paid_at DESC NULLS LAST;
            """, (booking_code,))

            rows = cur.fetchall()
            columns = [desc[0] for desc in cur.description]

    return {
        "booking_code": booking_code,
        "count": len(rows),
        "items": [
                    _payment_response(row, columns)
            for row in rows
        ],
    }


class PaymentStatusUpdate(BaseModel):
    status: str = Field(..., examples=["paid"])
    paid_at: Optional[datetime] = None
    due_at: Optional[datetime] = None
    reference: Optional[str] = None
    notes: Optional[str] = None

    @field_validator("status")
    @classmethod
    def validate_status(cls, value):
        try:
            return normalize_payment_status(value)
        except ValueError as exc:
            raise ValueError(str(exc)) from exc


@router.patch("/{payment_id}/status")
def update_payment_status(payment_id: UUID, payload: PaymentStatusUpdate):
    with get_connection() as conn:
        with conn.cursor() as cur:
            try:
                cur.execute("""
                    UPDATE payments
                    SET
                        status = %s,
                        paid_at = COALESCE(%s, paid_at),
                        due_at = COALESCE(%s, due_at),
                        reference = COALESCE(%s, reference),
                        notes = COALESCE(%s, notes)
                    WHERE id = %s
                    RETURNING
                        id,
                        booking_id,
                        amount,
                        currency,
                        method,
                        status,
                        paid_at,
                        due_at,
                        reference,
                        notes;
                """, (
                    payload.status,
                    payload.paid_at,
                    payload.due_at,
                    payload.reference,
                    payload.notes,
                    payment_id,
                ))

                row = cur.fetchone()

                if row is None:
                    raise HTTPException(status_code=404, detail="Payment not found")

                columns = [desc[0] for desc in cur.description]
                conn.commit()

            except HTTPException:
                conn.rollback()
                raise

            except Exception as exc:
                conn.rollback()
                raise HTTPException(status_code=400, detail=str(exc))

    result = dict(zip(columns, row))
    result["status"] = payment_status_for_response(result["status"], result.get("due_at"))
    return result
