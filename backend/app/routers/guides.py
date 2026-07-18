from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List
from uuid import UUID
from decimal import Decimal
import json

from app.database import get_connection

router = APIRouter(prefix="/guides", tags=["Guides"])


class GuideCreate(BaseModel):
    name: str = Field(..., examples=["German-speaking guide"])
    phone: Optional[str] = None
    line_id: Optional[str] = None
    languages: List[str] = []
    license_no: Optional[str] = None
    base_area: Optional[str] = Field(default="Bangkok")
    default_cost: Decimal = Decimal("0.00")
    rating: Optional[Decimal] = None
    notes: Optional[str] = None


@router.get("")
def list_guides():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    id,
                    name,
                    phone,
                    line_id,
                    languages,
                    license_no,
                    base_area,
                    default_cost,
                    rating,
                    notes
                FROM guides
                ORDER BY name ASC;
            """)
            rows = cur.fetchall()
            columns = [desc[0] for desc in cur.description]

    return {
        "count": len(rows),
        "items": [dict(zip(columns, row)) for row in rows],
    }


@router.get("/{guide_id}")
def get_guide(guide_id: UUID):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    id,
                    name,
                    phone,
                    line_id,
                    languages,
                    license_no,
                    base_area,
                    default_cost,
                    rating,
                    notes
                FROM guides
                WHERE id = %s;
            """, (guide_id,))
            row = cur.fetchone()

            if row is None:
                raise HTTPException(status_code=404, detail="Guide not found")

            columns = [desc[0] for desc in cur.description]

    return dict(zip(columns, row))


@router.post("")
def create_guide(payload: GuideCreate):
    with get_connection() as conn:
        with conn.cursor() as cur:
            try:
                cur.execute("""
                    INSERT INTO guides (
                        name,
                        phone,
                        line_id,
                        languages,
                        license_no,
                        base_area,
                        default_cost,
                        rating,
                        notes
                    )
                    VALUES (%s, %s, %s, %s::jsonb, %s, %s, %s, %s, %s)
                    RETURNING
                        id,
                        name,
                        phone,
                        line_id,
                        languages,
                        license_no,
                        base_area,
                        default_cost,
                        rating,
                        notes;
                """, (
                    payload.name,
                    payload.phone,
                    payload.line_id,
                    json.dumps(payload.languages),
                    payload.license_no,
                    payload.base_area,
                    payload.default_cost,
                    payload.rating,
                    payload.notes,
                ))

                row = cur.fetchone()
                columns = [desc[0] for desc in cur.description]
                conn.commit()

            except Exception as exc:
                conn.rollback()
                raise HTTPException(status_code=400, detail=str(exc))

    return dict(zip(columns, row))
