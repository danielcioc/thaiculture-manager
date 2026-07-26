from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
from uuid import UUID
from decimal import Decimal
from datetime import datetime

from app.database import get_connection

router = APIRouter(prefix="/payments", tags=["Payments"])


class PaymentCreate(BaseModel):
    booking_id: UUID
    amount: Decimal = Field(..., examples=["3000.00"])
    currency: str = "THB"
    method: str = Field(..., examples=["Thai QR"])
    status: str = Field(default="Pending", examples=["Pending"])
    paid_at: Optional[datetime] = None
    due_at: Optional[datetime] = None
    reference: Optional[str] = None
    notes: Optional[str] = None


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
        "items": [dict(zip(columns, row)) for row in rows],
    }


@router.post("")
def create_payment(payload: PaymentCreate):
    with get_connection() as conn:
        with conn.cursor() as cur:
            try:
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
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    RETURNING
                        id,
                        booking_id,
                        amount,
                        currency,
                        method,
                        status,
                        paid_at,
                        reference;
                """, (
                    payload.booking_id,
                    payload.amount,
                    payload.currency,
                    payload.method,
                    payload.status,
                    payload.paid_at,
                    payload.reference,
                ))

                row = cur.fetchone()
                columns = [desc[0] for desc in cur.description]
                conn.commit()

            except Exception as exc:
                conn.rollback()
                raise HTTPException(status_code=400, detail=str(exc))

    return dict(zip(columns, row))


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
        "items": [dict(zip(columns, row)) for row in rows],
    }


class PaymentStatusUpdate(BaseModel):
    status: str = Field(..., examples=["Paid"])
    paid_at: Optional[datetime] = None
    due_at: Optional[datetime] = None
    reference: Optional[str] = None
    notes: Optional[str] = None


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
                        reference;
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

    return dict(zip(columns, row))
