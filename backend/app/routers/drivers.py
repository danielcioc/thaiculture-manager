from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
from uuid import UUID
from decimal import Decimal

from app.database import get_connection

router = APIRouter(prefix="/drivers", tags=["Drivers"])


class DriverCreate(BaseModel):
    name: str = Field(..., examples=["Private van driver"])
    phone: Optional[str] = None
    line_id: Optional[str] = None
    base_area: Optional[str] = Field(default="Bangkok")
    default_cost: Decimal = Decimal("0.00")
    rating: Optional[Decimal] = None


@router.get("")
def list_drivers():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    id,
                    name,
                    phone,
                    line_id,
                    base_area,
                    default_cost,
                    rating
                FROM drivers
                ORDER BY name ASC;
            """)
            rows = cur.fetchall()
            columns = [desc[0] for desc in cur.description]

    return {
        "count": len(rows),
        "items": [dict(zip(columns, row)) for row in rows],
    }


@router.get("/{driver_id}")
def get_driver(driver_id: UUID):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    id,
                    name,
                    phone,
                    line_id,
                    base_area,
                    default_cost,
                    rating
                FROM drivers
                WHERE id = %s;
            """, (driver_id,))
            row = cur.fetchone()

            if row is None:
                raise HTTPException(status_code=404, detail="Driver not found")

            columns = [desc[0] for desc in cur.description]

    return dict(zip(columns, row))


@router.post("")
def create_driver(payload: DriverCreate):
    with get_connection() as conn:
        with conn.cursor() as cur:
            try:
                cur.execute("""
                    INSERT INTO drivers (
                        name,
                        phone,
                        line_id,
                        base_area,
                        default_cost,
                        rating
                    )
                    VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING
                        id,
                        name,
                        phone,
                        line_id,
                        base_area,
                        default_cost,
                        rating;
                """, (
                    payload.name,
                    payload.phone,
                    payload.line_id,
                    payload.base_area,
                    payload.default_cost,
                    payload.rating,
                ))

                row = cur.fetchone()
                columns = [desc[0] for desc in cur.description]
                conn.commit()

            except Exception as exc:
                conn.rollback()
                raise HTTPException(status_code=400, detail=str(exc))

    return dict(zip(columns, row))
