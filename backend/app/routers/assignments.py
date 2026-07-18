from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
from uuid import UUID
from decimal import Decimal

from app.database import get_connection

router = APIRouter(prefix="/assignments", tags=["Assignments"])


class AssignmentCreate(BaseModel):
    booking_id: UUID
    assignment_type: str = Field(..., examples=["guide"])
    guide_id: Optional[UUID] = None
    driver_id: Optional[UUID] = None
    supplier_id: Optional[UUID] = None
    cost: Decimal = Decimal("0.00")
    status: str = "assigned"
    notes: Optional[str] = None


@router.get("")
def list_assignments():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    a.id,
                    a.booking_id,
                    b.booking_code,
                    a.assignment_type,
                    g.name AS guide_name,
                    d.name AS driver_name,
                    a.cost,
                    a.status,
                    a.notes
                FROM assignments a
                LEFT JOIN bookings b ON b.id = a.booking_id
                LEFT JOIN guides g ON g.id = a.guide_id
                LEFT JOIN drivers d ON d.id = a.driver_id
                ORDER BY b.tour_date ASC NULLS LAST, b.created_at DESC;
            """)
            rows = cur.fetchall()
            columns = [desc[0] for desc in cur.description]

    return {
        "count": len(rows),
        "items": [dict(zip(columns, row)) for row in rows],
    }


@router.post("")
def create_assignment(payload: AssignmentCreate):
    with get_connection() as conn:
        with conn.cursor() as cur:
            try:
                cur.execute("""
                    INSERT INTO assignments (
                        booking_id,
                        assignment_type,
                        guide_id,
                        driver_id,
                        supplier_id,
                        cost,
                        status,
                        notes
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING
                        id,
                        booking_id,
                        assignment_type,
                        guide_id,
                        driver_id,
                        supplier_id,
                        cost,
                        status,
                        notes;
                """, (
                    payload.booking_id,
                    payload.assignment_type,
                    payload.guide_id,
                    payload.driver_id,
                    payload.supplier_id,
                    payload.cost,
                    payload.status,
                    payload.notes,
                ))

                row = cur.fetchone()
                columns = [desc[0] for desc in cur.description]
                conn.commit()

            except Exception as exc:
                conn.rollback()
                raise HTTPException(status_code=400, detail=str(exc))

    return dict(zip(columns, row))


@router.get("/booking/{booking_code}")
def list_assignments_for_booking(booking_code: str):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    a.id,
                    b.booking_code,
                    a.assignment_type,
                    g.name AS guide_name,
                    g.languages AS guide_languages,
                    g.phone AS guide_phone,
                    d.name AS driver_name,
                    d.phone AS driver_phone,
                    a.cost,
                    a.status,
                    a.notes
                FROM assignments a
                LEFT JOIN bookings b ON b.id = a.booking_id
                LEFT JOIN guides g ON g.id = a.guide_id
                LEFT JOIN drivers d ON d.id = a.driver_id
                WHERE b.booking_code = %s
                ORDER BY a.assignment_type ASC;
            """, (booking_code,))

            rows = cur.fetchall()
            columns = [desc[0] for desc in cur.description]

    return {
        "booking_code": booking_code,
        "count": len(rows),
        "items": [dict(zip(columns, row)) for row in rows],
    }
