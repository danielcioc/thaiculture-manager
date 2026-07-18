from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
from uuid import UUID
from decimal import Decimal

from app.database import get_connection

router = APIRouter(prefix="/tours", tags=["Tours"])


class TourCreate(BaseModel):
    tour_code: str = Field(..., examples=["EAYU2"])
    name: str = Field(..., examples=["Ayutthaya Sunset & Night Temples"])
    category: Optional[str] = Field(default=None, examples=["Cultural Tour"])
    default_duration_hours: Optional[Decimal] = Field(default=None, examples=["10.0"])
    website_url: Optional[str] = None
    is_active: bool = True


@router.get("")
def list_tours():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    id,
                    tour_code,
                    name,
                    category,
                    default_duration_hours,
                    website_url,
                    is_active
                FROM tours
                ORDER BY name ASC;
            """)
            rows = cur.fetchall()
            columns = [desc[0] for desc in cur.description]

    return {
        "count": len(rows),
        "items": [dict(zip(columns, row)) for row in rows],
    }


@router.get("/{tour_id}")
def get_tour(tour_id: UUID):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    id,
                    tour_code,
                    name,
                    category,
                    default_duration_hours,
                    website_url,
                    is_active
                FROM tours
                WHERE id = %s;
            """, (tour_id,))
            row = cur.fetchone()

            if row is None:
                raise HTTPException(status_code=404, detail="Tour not found")

            columns = [desc[0] for desc in cur.description]

    return dict(zip(columns, row))


@router.post("")
def create_tour(payload: TourCreate):
    with get_connection() as conn:
        with conn.cursor() as cur:
            try:
                cur.execute("""
                    INSERT INTO tours (
                        tour_code,
                        name,
                        category,
                        default_duration_hours,
                        website_url,
                        is_active
                    )
                    VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING
                        id,
                        tour_code,
                        name,
                        category,
                        default_duration_hours,
                        website_url,
                        is_active;
                """, (
                    payload.tour_code,
                    payload.name,
                    payload.category,
                    payload.default_duration_hours,
                    payload.website_url,
                    payload.is_active,
                ))

                row = cur.fetchone()
                columns = [desc[0] for desc in cur.description]
                conn.commit()

            except Exception as exc:
                conn.rollback()
                raise HTTPException(status_code=400, detail=str(exc))

    return dict(zip(columns, row))
