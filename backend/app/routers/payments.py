from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, field_validator
from typing import Optional
from uuid import UUID
from decimal import Decimal
from datetime import datetime

from app.database import get_connection
from app.financials import normalize_payment_status, payment_status_for_response

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


@router.get("")
def list_payments():
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
                    p.notes
                FROM payments p
                LEFT JOIN bookings b ON b.id = p.booking_id
                LEFT JOIN customers c ON c.id = b.customer_id
                ORDER BY p.paid_at DESC NULLS LAST, b.created_at DESC
                LIMIT 100;
            """)
            rows = cur.fetchall()
            columns = [desc[0] for desc in cur.description]

    return {
        "count": len(rows),
        "items": [
            {**dict(zip(columns, row)), "status": payment_status_for_response(row[7], row[9])}
            for row in rows
        ],
    }


@router.post("")
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
                    p.notes
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
            {**dict(zip(columns, row)), "status": payment_status_for_response(row[7], row[9])}
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
