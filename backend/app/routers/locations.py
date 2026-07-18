from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
from uuid import UUID

from app.database import get_connection

router = APIRouter(prefix="/locations", tags=["Locations"])


class LocationCreate(BaseModel):
    name: str = Field(..., examples=["Amara Hotel Bangkok"])
    address: Optional[str] = None
    google_maps_url: Optional[str] = None
    city: Optional[str] = Field(default="Bangkok")
    country: str = "Thailand"


@router.get("")
def list_locations():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    id,
                    name,
                    address,
                    google_maps_url,
                    city,
                    country
                FROM locations
                ORDER BY name ASC;
            """)
            rows = cur.fetchall()
            columns = [desc[0] for desc in cur.description]

    return {
        "count": len(rows),
        "items": [dict(zip(columns, row)) for row in rows],
    }


@router.get("/{location_id}")
def get_location(location_id: UUID):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    id,
                    name,
                    address,
                    google_maps_url,
                    city,
                    country
                FROM locations
                WHERE id = %s;
            """, (location_id,))
            row = cur.fetchone()

            if row is None:
                raise HTTPException(status_code=404, detail="Location not found")

            columns = [desc[0] for desc in cur.description]

    return dict(zip(columns, row))


@router.post("")
def create_location(payload: LocationCreate):
    with get_connection() as conn:
        with conn.cursor() as cur:
            try:
                cur.execute("""
                    INSERT INTO locations (
                        name,
                        address,
                        google_maps_url,
                        city,
                        country
                    )
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING
                        id,
                        name,
                        address,
                        google_maps_url,
                        city,
                        country;
                """, (
                    payload.name,
                    payload.address,
                    payload.google_maps_url,
                    payload.city,
                    payload.country,
                ))

                row = cur.fetchone()
                columns = [desc[0] for desc in cur.description]
                conn.commit()

            except Exception as exc:
                conn.rollback()
                raise HTTPException(status_code=400, detail=str(exc))

    return dict(zip(columns, row))
