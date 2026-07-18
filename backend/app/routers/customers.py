from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr
from typing import Optional
from uuid import UUID

from app.database import get_connection

router = APIRouter(prefix="/customers", tags=["Customers"])


class CustomerCreate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    display_name: str
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    whatsapp: Optional[str] = None
    country: Optional[str] = None
    nationality: Optional[str] = None
    preferred_language: str = "EN"
    notes: Optional[str] = None


@router.get("")
def list_customers():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    id,
                    first_name,
                    last_name,
                    display_name,
                    email,
                    phone,
                    whatsapp,
                    country,
                    nationality,
                    preferred_language,
                    notes,
                    created_at
                FROM customers
                ORDER BY created_at DESC
                LIMIT 100;
            """)
            rows = cur.fetchall()
            columns = [desc[0] for desc in cur.description]

    return {
        "count": len(rows),
        "items": [dict(zip(columns, row)) for row in rows],
    }


@router.get("/{customer_id}")
def get_customer(customer_id: UUID):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    id,
                    first_name,
                    last_name,
                    display_name,
                    email,
                    phone,
                    whatsapp,
                    country,
                    nationality,
                    preferred_language,
                    notes,
                    created_at
                FROM customers
                WHERE id = %s;
            """, (customer_id,))
            row = cur.fetchone()

            if row is None:
                raise HTTPException(status_code=404, detail="Customer not found")

            columns = [desc[0] for desc in cur.description]

    return dict(zip(columns, row))


@router.post("")
def create_customer(payload: CustomerCreate):
    with get_connection() as conn:
        with conn.cursor() as cur:
            try:
                cur.execute("""
                    INSERT INTO customers (
                        first_name,
                        last_name,
                        display_name,
                        email,
                        phone,
                        whatsapp,
                        country,
                        nationality,
                        preferred_language,
                        notes
                    )
                    VALUES (
                        %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s
                    )
                    RETURNING
                        id,
                        first_name,
                        last_name,
                        display_name,
                        email,
                        phone,
                        whatsapp,
                        country,
                        nationality,
                        preferred_language,
                        notes,
                        created_at;
                """, (
                    payload.first_name,
                    payload.last_name,
                    payload.display_name,
                    payload.email,
                    payload.phone,
                    payload.whatsapp,
                    payload.country,
                    payload.nationality,
                    payload.preferred_language,
                    payload.notes,
                ))

                row = cur.fetchone()
                columns = [desc[0] for desc in cur.description]
                conn.commit()

            except Exception as exc:
                conn.rollback()
                raise HTTPException(status_code=400, detail=str(exc))

    return dict(zip(columns, row))
