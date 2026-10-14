from fastapi import APIRouter
from app.database import get_connection

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/summary")
def dashboard_summary():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    COUNT(*) AS total_bookings,
                    COUNT(*) FILTER (WHERE status = 'Confirmed') AS confirmed_bookings,
                    COUNT(*) FILTER (WHERE status = 'Inquiry') AS inquiry_bookings,
                    COALESCE(SUM(selling_price), 0) AS total_revenue
                FROM bookings;
            """)
            booking_stats = cur.fetchone()

            cur.execute("""
                SELECT
                    COALESCE(SUM(CASE WHEN status = 'Paid' THEN amount ELSE 0 END), 0) AS paid_revenue,
                    COALESCE(SUM(CASE WHEN status = 'Pending' THEN amount ELSE 0 END), 0) AS pending_revenue
                FROM payments;
            """)
            payment_stats = cur.fetchone()

            cur.execute("""
                SELECT
                    COALESCE(SUM(cost), 0) AS total_costs,
                    COALESCE(SUM(CASE WHEN assignment_type = 'guide' THEN cost ELSE 0 END), 0) AS guide_costs,
                    COALESCE(SUM(CASE WHEN assignment_type = 'driver' THEN cost ELSE 0 END), 0) AS driver_costs,
                    COALESCE(SUM(CASE WHEN assignment_type NOT IN ('guide', 'driver') THEN cost ELSE 0 END), 0) AS other_costs
                FROM assignments;
            """)
            cost_stats = cur.fetchone()

    total_bookings = booking_stats[0]
    confirmed_bookings = booking_stats[1]
    inquiry_bookings = booking_stats[2]
    total_revenue = booking_stats[3]

    paid_revenue = payment_stats[0]
    pending_revenue = payment_stats[1]
    outstanding_revenue = total_revenue - paid_revenue

    total_costs = cost_stats[0]
    guide_costs = cost_stats[1]
    driver_costs = cost_stats[2]
    other_costs = cost_stats[3]

    gross_margin = total_revenue - total_costs

    if total_revenue and total_revenue > 0:
        margin_percent = round((gross_margin / total_revenue) * 100, 2)
    else:
        margin_percent = 0

    return {
        "total_bookings": total_bookings,
        "confirmed_bookings": confirmed_bookings,
        "inquiry_bookings": inquiry_bookings,
        "total_revenue": total_revenue,
        "paid_revenue": paid_revenue,
        "pending_revenue": pending_revenue,
        "outstanding_revenue": outstanding_revenue,
        "total_costs": total_costs,
        "guide_costs": guide_costs,
        "driver_costs": driver_costs,
        "other_costs": other_costs,
        "gross_margin": gross_margin,
        "margin_percent": margin_percent,
        "currency": "THB"
    }


@router.get("/recent-bookings")
def recent_bookings():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    b.booking_code,
                    b.status,
                    c.display_name AS customer_name,
                    c.country AS customer_country,
                    t.name AS tour_name,
                    b.tour_date,
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
                ORDER BY b.created_at DESC
                LIMIT 10;
            """)
            rows = cur.fetchall()
            columns = [desc[0] for desc in cur.description]

    return {
        "count": len(rows),
        "items": [dict(zip(columns, row)) for row in rows],
    }


@router.get("/unpaid-bookings")
def unpaid_bookings():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    b.booking_code,
                    b.status,
                    c.display_name AS customer_name,
                    t.name AS tour_name,
                    b.tour_date,
                    b.selling_price,
                    b.currency,
                    COALESCE(SUM(CASE WHEN p.status = 'Paid' THEN p.amount ELSE 0 END), 0) AS paid_amount,
                    COALESCE(SUM(CASE WHEN p.status = 'Pending' THEN p.amount ELSE 0 END), 0) AS pending_amount,
                    (b.selling_price - COALESCE(SUM(CASE WHEN p.status = 'Paid' THEN p.amount ELSE 0 END), 0)) AS outstanding_amount
                FROM bookings b
                LEFT JOIN customers c ON c.id = b.customer_id
                LEFT JOIN tours t ON t.id = b.tour_id
                LEFT JOIN payments p ON p.booking_id = b.id
                GROUP BY
                    b.id,
                    b.booking_code,
                    b.status,
                    c.display_name,
                    t.name,
                    b.tour_date,
                    b.selling_price,
                    b.currency
                HAVING (b.selling_price - COALESCE(SUM(CASE WHEN p.status = 'Paid' THEN p.amount ELSE 0 END), 0)) > 0
                ORDER BY b.tour_date ASC NULLS LAST, b.created_at DESC
                LIMIT 20;
            """)
            rows = cur.fetchall()
            columns = [desc[0] for desc in cur.description]

    return {
        "count": len(rows),
        "items": [dict(zip(columns, row)) for row in rows],
    }
