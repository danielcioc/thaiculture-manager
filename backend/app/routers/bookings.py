from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
from datetime import date, time
from decimal import Decimal

from app.database import get_connection

router = APIRouter(prefix="/bookings", tags=["Bookings"])



def compute_booking_financial_status(
    selling_price,
    paid_amount,
    pending_amount,
    requested_amount,
):
    if paid_amount >= selling_price and selling_price > 0:
        return "paid"
    if paid_amount > 0 and paid_amount < selling_price:
        if pending_amount > 0 or requested_amount > paid_amount:
            return "partiallypaid"
        return "depositpaid"
    if paid_amount <= 0 and pending_amount > 0:
        return "depositrequested"
    return "unpaid"


class BookingCreate(BaseModel):
    booking_code: str = Field(..., examples=["TCT-2026-000001"])
    status: str = Field(default="Inquiry")
    source: str = Field(default="Website")
    customer_id: Optional[str] = None
    tour_id: Optional[str] = None
    tour_date: Optional[date] = None
    pickup_time: Optional[time] = None
    pickup_location_id: Optional[str] = None
    dropoff_location_id: Optional[str] = None
    adults: int = 0
    children: int = 0
    infants: int = 0
    guide_language: str = "EN"
    selling_price: Decimal = Decimal("0.00")
    currency: str = "THB"


@router.get("")
def list_bookings():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    b.id,
                    b.booking_code,
                    b.status,
                    b.source,

                    c.display_name AS customer_name,
                    c.email AS customer_email,
                    c.country AS customer_country,

                    t.tour_code,
                    t.name AS tour_name,
                    t.category AS tour_category,
                    t.default_duration_hours AS tour_duration_hours,

                    pickup.name AS pickup_location_name,
                    pickup.address AS pickup_location_address,
                    pickup.google_maps_url AS pickup_google_maps_url,

                    dropoff.name AS dropoff_location_name,
                    dropoff.address AS dropoff_location_address,
                    dropoff.google_maps_url AS dropoff_google_maps_url,

                    b.tour_date,
                    b.pickup_time,
                    b.adults,
                    b.children,
                    b.infants,
                    (COALESCE(b.adults, 0) + COALESCE(b.children, 0) + COALESCE(b.infants, 0)) AS total_guests,
                    b.guide_language,
                    b.selling_price,
                    b.currency,
                    b.created_at
                FROM bookings b
                LEFT JOIN customers c ON c.id = b.customer_id
                LEFT JOIN tours t ON t.id = b.tour_id
                LEFT JOIN locations pickup ON pickup.id = b.pickup_location_id
                LEFT JOIN locations dropoff ON dropoff.id = b.dropoff_location_id
                ORDER BY b.created_at DESC
                LIMIT 100;
            """)
            rows = cur.fetchall()
            columns = [desc[0] for desc in cur.description]

    return {
        "count": len(rows),
        "items": [dict(zip(columns, row)) for row in rows],
    }


@router.get("/{booking_code}")
def get_booking(booking_code: str):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    b.id,
                    b.booking_code,
                    b.status,
                    b.source,

                    c.display_name AS customer_name,
                    c.email AS customer_email,
                    c.country AS customer_country,

                    t.tour_code,
                    t.name AS tour_name,
                    t.category AS tour_category,
                    t.default_duration_hours AS tour_duration_hours,
                    t.website_url AS tour_website_url,

                    pickup.name AS pickup_location_name,
                    pickup.address AS pickup_location_address,
                    pickup.google_maps_url AS pickup_google_maps_url,

                    dropoff.name AS dropoff_location_name,
                    dropoff.address AS dropoff_location_address,
                    dropoff.google_maps_url AS dropoff_google_maps_url,

                    b.tour_date,
                    b.pickup_time,
                    b.adults,
                    b.children,
                    b.infants,
                    (COALESCE(b.adults, 0) + COALESCE(b.children, 0) + COALESCE(b.infants, 0)) AS total_guests,
                    b.guide_language,
                    b.selling_price,
                    b.currency,
                    b.created_at
                FROM bookings b
                LEFT JOIN customers c ON c.id = b.customer_id
                LEFT JOIN tours t ON t.id = b.tour_id
                LEFT JOIN locations pickup ON pickup.id = b.pickup_location_id
                LEFT JOIN locations dropoff ON dropoff.id = b.dropoff_location_id
                WHERE b.booking_code = %s;
            """, (booking_code,))
            row = cur.fetchone()

            if row is None:
                raise HTTPException(status_code=404, detail="Booking not found")

            columns = [desc[0] for desc in cur.description]

    return dict(zip(columns, row))


@router.get("/{booking_code}/payment-summary")
def get_booking_payment_summary(booking_code: str):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    b.id,
                    b.booking_code,
                    b.selling_price,
                    b.currency,
                    c.display_name AS customer_name
                FROM bookings b
                LEFT JOIN customers c ON c.id = b.customer_id
                WHERE b.booking_code = %s;
            """, (booking_code,))

            booking = cur.fetchone()

            if booking is None:
                raise HTTPException(status_code=404, detail="Booking not found")

            booking_columns = [desc[0] for desc in cur.description]
            booking_data = dict(zip(booking_columns, booking))

            cur.execute("""
                SELECT
                    COALESCE(SUM(CASE WHEN status = 'Paid' THEN amount ELSE 0 END), 0) AS paid_amount,
                    COALESCE(SUM(CASE WHEN status = 'Pending' THEN amount ELSE 0 END), 0) AS pending_amount,
                    COALESCE(SUM(CASE WHEN status IN ('Paid', 'Pending') THEN amount ELSE 0 END), 0) AS requested_amount
                FROM payments
                WHERE booking_id = %s;
            """, (booking_data["id"],))

            payment_totals = cur.fetchone()

    selling_price = booking_data["selling_price"]
    paid_amount = payment_totals[0]
    pending_amount = payment_totals[1]
    requested_amount = payment_totals[2]

    outstanding_amount = selling_price - paid_amount
    remaining_unrequested_amount = selling_price - requested_amount

    if paid_amount <= 0 and pending_amount <= 0:
        payment_status = "Unpaid"
    elif paid_amount >= selling_price:
        payment_status = "Paid"
    elif paid_amount > 0:
        payment_status = "Partially Paid"
    elif pending_amount > 0:
        payment_status = "Payment Requested"
    else:
        payment_status = "Unpaid"

    if paid_amount >= selling_price and selling_price > 0:
        booking_financial_status = "paid"
    elif paid_amount > 0:
        booking_financial_status = "partiallypaid"
    elif requested_amount > 0 or pending_amount > 0:
        booking_financial_status = "depositrequested"
    else:
        booking_financial_status = "unpaid"

    booking_financial_status = compute_booking_financial_status(
        selling_price=selling_price,
        paid_amount=paid_amount,
        pending_amount=pending_amount,
        requested_amount=requested_amount,
    )

    booking_financial_status = compute_booking_financial_status(
        selling_price=selling_price,
        paid_amount=paid_amount,
        pending_amount=pending_amount,
        requested_amount=requested_amount,
    )

    return {
        "booking_code": booking_data["booking_code"],
        "customer_name": booking_data["customer_name"],
        "selling_price": selling_price,
        "paid_amount": paid_amount,
        "pending_amount": pending_amount,
        "requested_amount": requested_amount,
        "outstanding_amount": outstanding_amount,
        "remaining_unrequested_amount": remaining_unrequested_amount,
        "payment_status": payment_status,
        "currency": booking_data["currency"],
    }


@router.post("")
def create_booking(payload: BookingCreate):
    with get_connection() as conn:
        with conn.cursor() as cur:
            try:
                cur.execute("""
                    INSERT INTO bookings (
                        booking_code,
                        status,
                        source,
                        customer_id,
                        tour_id,
                        tour_date,
                        pickup_time,
                        pickup_location_id,
                        dropoff_location_id,
                        adults,
                        children,
                        infants,
                        guide_language,
                        selling_price,
                        currency
                    )
                    VALUES (
                        %s, %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s, %s, %s, %s
                    )
                    RETURNING
                        id,
                        booking_code,
                        status,
                        source,
                        customer_id,
                        tour_id,
                        tour_date,
                        pickup_time,
                        pickup_location_id,
                        dropoff_location_id,
                        adults,
                        children,
                        infants,
                        guide_language,
                        selling_price,
                        currency,
                        created_at;
                """, (
                    payload.booking_code,
                    payload.status,
                    payload.source,
                    payload.customer_id,
                    payload.tour_id,
                    payload.tour_date,
                    payload.pickup_time,
                    payload.pickup_location_id,
                    payload.dropoff_location_id,
                    payload.adults,
                    payload.children,
                    payload.infants,
                    payload.guide_language,
                    payload.selling_price,
                    payload.currency,
                ))

                row = cur.fetchone()
                columns = [desc[0] for desc in cur.description]
                conn.commit()

            except Exception as exc:
                conn.rollback()
                raise HTTPException(status_code=400, detail=str(exc))

    return dict(zip(columns, row))


@router.get("/{booking_code}/operations-summary")
def get_booking_operations_summary(booking_code: str):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    b.id,
                    b.booking_code,
                    b.selling_price,
                    b.currency,
                    c.display_name AS customer_name,
                    t.name AS tour_name
                FROM bookings b
                LEFT JOIN customers c ON c.id = b.customer_id
                LEFT JOIN tours t ON t.id = b.tour_id
                WHERE b.booking_code = %s;
            """, (booking_code,))

            booking = cur.fetchone()

            if booking is None:
                raise HTTPException(status_code=404, detail="Booking not found")

            booking_columns = [desc[0] for desc in cur.description]
            booking_data = dict(zip(booking_columns, booking))

            cur.execute("""
                SELECT
                    COALESCE(SUM(CASE WHEN assignment_type = 'guide' THEN cost ELSE 0 END), 0) AS guide_cost,
                    COALESCE(SUM(CASE WHEN assignment_type = 'driver' THEN cost ELSE 0 END), 0) AS driver_cost,
                    COALESCE(SUM(CASE WHEN assignment_type NOT IN ('guide', 'driver') THEN cost ELSE 0 END), 0) AS other_cost,
                    COALESCE(SUM(cost), 0) AS total_cost
                FROM assignments
                WHERE booking_id = %s;
            """, (booking_data["id"],))

            cost_totals = cur.fetchone()

    selling_price = booking_data["selling_price"]
    guide_cost = cost_totals[0]
    driver_cost = cost_totals[1]
    other_cost = cost_totals[2]
    total_cost = cost_totals[3]

    gross_margin = selling_price - total_cost

    if selling_price and selling_price > 0:
        margin_percent = round((gross_margin / selling_price) * 100, 2)
    else:
        margin_percent = 0

    return {
        "booking_code": booking_data["booking_code"],
        "customer_name": booking_data["customer_name"],
        "tour_name": booking_data["tour_name"],
        "selling_price": selling_price,
        "guide_cost": guide_cost,
        "driver_cost": driver_cost,
        "other_cost": other_cost,
        "total_cost": total_cost,
        "gross_margin": gross_margin,
        "margin_percent": margin_percent,
        "currency": booking_data["currency"],
    }


@router.get("/{booking_code}/full")
def get_booking_full_detail(booking_code: str):
    with get_connection() as conn:
        with conn.cursor() as cur:
            # Main booking detail
            cur.execute("""
                SELECT
                    b.id,
                    b.booking_code,
                    b.status,
                    b.source,

                    c.id AS customer_id,
                    c.display_name AS customer_name,
                    c.email AS customer_email,
                    c.phone AS customer_phone,
                    c.whatsapp AS customer_whatsapp,
                    c.country AS customer_country,
                    c.nationality AS customer_nationality,
                    c.preferred_language AS customer_preferred_language,

                    t.id AS tour_id,
                    t.tour_code,
                    t.name AS tour_name,
                    t.category AS tour_category,
                    t.default_duration_hours AS tour_duration_hours,
                    t.website_url AS tour_website_url,

                    pickup.id AS pickup_location_id,
                    pickup.name AS pickup_location_name,
                    pickup.address AS pickup_location_address,
                    pickup.google_maps_url AS pickup_google_maps_url,

                    dropoff.id AS dropoff_location_id,
                    dropoff.name AS dropoff_location_name,
                    dropoff.address AS dropoff_location_address,
                    dropoff.google_maps_url AS dropoff_google_maps_url,

                    b.tour_date,
                    b.pickup_time,
                    b.adults,
                    b.children,
                    b.infants,
                    (COALESCE(b.adults, 0) + COALESCE(b.children, 0) + COALESCE(b.infants, 0)) AS total_guests,
                    b.guide_language,
                    b.selling_price,
                    b.currency,
                    b.created_at
                FROM bookings b
                LEFT JOIN customers c ON c.id = b.customer_id
                LEFT JOIN tours t ON t.id = b.tour_id
                LEFT JOIN locations pickup ON pickup.id = b.pickup_location_id
                LEFT JOIN locations dropoff ON dropoff.id = b.dropoff_location_id
                WHERE b.booking_code = %s;
            """, (booking_code,))

            booking = cur.fetchone()

            if booking is None:
                raise HTTPException(status_code=404, detail="Booking not found")

            booking_columns = [desc[0] for desc in cur.description]
            booking_data = dict(zip(booking_columns, booking))

            # Payments
            cur.execute("""
                SELECT
                    id,
                    amount,
                    currency,
                    method,
                    status,
                    paid_at,
                    reference
                FROM payments
                WHERE booking_id = %s
                ORDER BY paid_at DESC NULLS LAST, amount ASC;
            """, (booking_data["id"],))

            payment_rows = cur.fetchall()
            payment_columns = [desc[0] for desc in cur.description]
            payments = [dict(zip(payment_columns, row)) for row in payment_rows]

            # Payment summary
            cur.execute("""
                SELECT
                    COALESCE(SUM(CASE WHEN status = 'Paid' THEN amount ELSE 0 END), 0) AS paid_amount,
                    COALESCE(SUM(CASE WHEN status = 'Pending' THEN amount ELSE 0 END), 0) AS pending_amount,
                    COALESCE(SUM(CASE WHEN status IN ('Paid', 'Pending') THEN amount ELSE 0 END), 0) AS requested_amount
                FROM payments
                WHERE booking_id = %s;
            """, (booking_data["id"],))

            payment_totals = cur.fetchone()

            # Assignments
            cur.execute("""
                SELECT
                    a.id,
                    a.assignment_type,
                    g.name AS guide_name,
                    g.languages AS guide_languages,
                    g.phone AS guide_phone,
                    g.line_id AS guide_line_id,
                    d.name AS driver_name,
                    d.phone AS driver_phone,
                    d.line_id AS driver_line_id,
                    a.cost,
                    a.status,
                    a.notes
                FROM assignments a
                LEFT JOIN guides g ON g.id = a.guide_id
                LEFT JOIN drivers d ON d.id = a.driver_id
                WHERE a.booking_id = %s
                ORDER BY a.assignment_type ASC;
            """, (booking_data["id"],))

            assignment_rows = cur.fetchall()
            assignment_columns = [desc[0] for desc in cur.description]
            assignments = [dict(zip(assignment_columns, row)) for row in assignment_rows]

            # Operations summary
            cur.execute("""
                SELECT
                    COALESCE(SUM(CASE WHEN assignment_type = 'guide' THEN cost ELSE 0 END), 0) AS guide_cost,
                    COALESCE(SUM(CASE WHEN assignment_type = 'driver' THEN cost ELSE 0 END), 0) AS driver_cost,
                    COALESCE(SUM(CASE WHEN assignment_type NOT IN ('guide', 'driver') THEN cost ELSE 0 END), 0) AS other_cost,
                    COALESCE(SUM(cost), 0) AS total_cost
                FROM assignments
                WHERE booking_id = %s;
            """, (booking_data["id"],))

            cost_totals = cur.fetchone()

    selling_price = booking_data["selling_price"]

    paid_amount = payment_totals[0]
    pending_amount = payment_totals[1]
    requested_amount = payment_totals[2]
    outstanding_amount = selling_price - paid_amount
    remaining_unrequested_amount = selling_price - requested_amount

    if paid_amount <= 0 and pending_amount <= 0:
        payment_status = "Unpaid"
    elif paid_amount >= selling_price:
        payment_status = "Paid"
    elif paid_amount > 0:
        payment_status = "Partially Paid"
    elif pending_amount > 0:
        payment_status = "Payment Requested"
    else:
        payment_status = "Unpaid"

    if paid_amount >= selling_price and selling_price > 0:
        booking_financial_status = "paid"
    elif paid_amount > 0:
        booking_financial_status = "partiallypaid"
    elif requested_amount > 0 or pending_amount > 0:
        booking_financial_status = "depositrequested"
    else:
        booking_financial_status = "unpaid"

    guide_cost = cost_totals[0]
    driver_cost = cost_totals[1]
    other_cost = cost_totals[2]
    total_cost = cost_totals[3]
    gross_margin = selling_price - total_cost

    if selling_price and selling_price > 0:
        margin_percent = round((gross_margin / selling_price) * 100, 2)
    else:
        margin_percent = 0

    return {
        "booking": booking_data,
        "payments": payments,
        "payment_summary": {
            "selling_price": selling_price,
            "paid_amount": paid_amount,
            "pending_amount": pending_amount,
            "requested_amount": requested_amount,
            "outstanding_amount": outstanding_amount,
            "remaining_unrequested_amount": remaining_unrequested_amount,
            "payment_status": payment_status,
            "booking_financial_status": booking_financial_status,
            "currency": booking_data["currency"],
        },
        "assignments": assignments,
        "operations_summary": {
            "selling_price": selling_price,
            "guide_cost": guide_cost,
            "driver_cost": driver_cost,
            "other_cost": other_cost,
            "total_cost": total_cost,
            "gross_margin": gross_margin,
            "margin_percent": margin_percent,
            "currency": booking_data["currency"],
        },
    }
