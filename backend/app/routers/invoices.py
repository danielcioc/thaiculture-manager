from fastapi import APIRouter, HTTPException
from app.database import get_connection

router = APIRouter(prefix="/invoices", tags=["Invoices"])


def _invoice_rows():
    return """
        SELECT
            i.id,
            i.booking_id,
            i.invoice_no,
            i.invoice_type,
            i.amount,
            i.status,
            i.issued_at,
            b.booking_code,
            b.status AS booking_status,
            b.source AS booking_source,
            c.display_name AS customer_name,
            c.email AS customer_email
        FROM invoices i
        LEFT JOIN bookings b ON b.id = i.booking_id
        LEFT JOIN customers c ON c.id = b.customer_id
    """


@router.get("")
def list_invoices():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                _invoice_rows() + " ORDER BY i.issued_at DESC NULLS LAST, i.invoice_no ASC LIMIT 100;"
            )
            rows = cur.fetchall()
            columns = [desc[0] for desc in cur.description]

    return {"count": len(rows), "items": [dict(zip(columns, row)) for row in rows]}


@router.get("/{invoice_no}")
def get_invoice(invoice_no: str):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(_invoice_rows() + " WHERE i.invoice_no = %s;", (invoice_no,))
            row = cur.fetchone()

            if row is None:
                raise HTTPException(status_code=404, detail="Invoice not found")

            columns = [desc[0] for desc in cur.description]

            cur.execute(
                """
                SELECT
                    ii.id,
                    ii.invoice_id,
                    ii.booking_id,
                    ii.description,
                    ii.qty,
                    ii.unit_amount,
                    ii.line_amount,
                    ii.service_date,
                    b.booking_code
                FROM invoice_items ii
                LEFT JOIN bookings b ON b.id = ii.booking_id
                WHERE ii.invoice_id = %s
                ORDER BY ii.service_date NULLS LAST, ii.description ASC;
                """,
                (row[0],),
            )
            item_rows = cur.fetchall()
            item_columns = [desc[0] for desc in cur.description]

    return {
        "invoice": dict(zip(columns, row)),
        "items": [dict(zip(item_columns, r)) for r in item_rows],
    }
