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
                WITH assignment_costs AS (
                    SELECT
                        booking_id,
                        COALESCE(SUM(CASE WHEN assignment_type = 'guide' THEN cost ELSE 0 END), 0) AS guide_cost,
                        COALESCE(SUM(CASE WHEN assignment_type = 'driver' THEN cost ELSE 0 END), 0) AS driver_cost,
                        COALESCE(SUM(CASE WHEN assignment_type NOT IN ('guide', 'driver') THEN cost ELSE 0 END), 0) AS other_cost,
                        COALESCE(SUM(cost), 0) AS total_cost
                    FROM assignments
                    GROUP BY booking_id
                ),
                latest_quotes AS (
                    SELECT DISTINCT ON (booking_id)
                        booking_id,
                        total_cost,
                        breakdown
                    FROM pricing_quotes
                    ORDER BY booking_id, created_at DESC
                ),
                resolved_costs AS (
                    SELECT
                        b.id AS booking_id,
                        CASE
                            WHEN COALESCE(ac.total_cost, 0) > 0 THEN ac.guide_cost
                            WHEN lq.total_cost IS NOT NULL
                                 AND (COALESCE((lq.breakdown ->> 'direct_cost_is_known')::boolean, true) = true OR lq.total_cost > 0)
                                THEN COALESCE((lq.breakdown ->> 'guide_cost')::numeric, (lq.breakdown ->> 'guide_cost_total')::numeric, 0)
                            ELSE 0
                        END AS guide_cost,
                        CASE
                            WHEN COALESCE(ac.total_cost, 0) > 0 THEN ac.driver_cost
                            WHEN lq.total_cost IS NOT NULL
                                 AND (COALESCE((lq.breakdown ->> 'direct_cost_is_known')::boolean, true) = true OR lq.total_cost > 0)
                                THEN COALESCE((lq.breakdown ->> 'driver_cost')::numeric, (lq.breakdown ->> 'driver_cost_total')::numeric, 0)
                            ELSE 0
                        END AS driver_cost,
                        CASE
                            WHEN COALESCE(ac.total_cost, 0) > 0 THEN ac.other_cost
                            WHEN lq.total_cost IS NOT NULL
                                 AND (COALESCE((lq.breakdown ->> 'direct_cost_is_known')::boolean, true) = true OR lq.total_cost > 0)
                                THEN COALESCE(
                                    (lq.breakdown ->> 'other_cost')::numeric,
                                    (lq.breakdown ->> 'other_cost_total')::numeric,
                                    GREATEST(
                                        lq.total_cost
                                        - COALESCE((lq.breakdown ->> 'guide_cost')::numeric, (lq.breakdown ->> 'guide_cost_total')::numeric, 0)
                                        - COALESCE((lq.breakdown ->> 'driver_cost')::numeric, (lq.breakdown ->> 'driver_cost_total')::numeric, 0),
                                        0
                                    )
                                )
                            ELSE 0
                        END AS other_cost,
                        CASE
                            WHEN COALESCE(ac.total_cost, 0) > 0 THEN ac.total_cost
                            WHEN lq.total_cost IS NOT NULL
                                 AND (COALESCE((lq.breakdown ->> 'direct_cost_is_known')::boolean, true) = true OR lq.total_cost > 0)
                                THEN lq.total_cost
                            ELSE 0
                        END AS total_cost
                    FROM bookings b
                    LEFT JOIN assignment_costs ac ON ac.booking_id = b.id
                    LEFT JOIN latest_quotes lq ON lq.booking_id = b.id
                )
                SELECT
                    COALESCE(SUM(total_cost), 0) AS total_costs,
                    COALESCE(SUM(guide_cost), 0) AS guide_costs,
                    COALESCE(SUM(driver_cost), 0) AS driver_costs,
                    COALESCE(SUM(other_cost), 0) AS other_costs
                FROM resolved_costs;
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
