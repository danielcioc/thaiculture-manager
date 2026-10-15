from decimal import Decimal
from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from psycopg.types.json import Jsonb
from pydantic import BaseModel, Field

from app.database import get_connection
from app.pricing_policy import (
    POLICY_VERSION,
    PricingPolicyInputError,
    calculate_quote,
)

router = APIRouter(prefix="/pricing", tags=["Pricing"])


def _to_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return float(value)
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


class PricingRuleResponse(BaseModel):
    rule_name: str
    tour_id: str
    tour_code: str
    tour_name: str
    rule_type: str
    confidence_status: Optional[str] = None
    pricing_use: Optional[str] = None
    cost_status: Optional[str] = None
    requires_manual_review: Optional[bool] = None
    currency: Optional[str] = None
    selling_price_gross: Optional[float] = None
    selling_price_net: Optional[float] = None
    vat_rate: Optional[float] = None
    direct_cost_total: Optional[float] = None
    insurance_rule: Optional[str] = None
    includes: Optional[str] = None
    excludes: Optional[str] = None
    conditions: dict
    calculation: dict
    is_active: bool


class PricingQuoteResponse(BaseModel):
    booking_code: str
    booking_id: str
    tour_id: str
    tour_code: str
    tour_name: str
    tour_date: Optional[str] = None
    total_cost: float
    recommended_price: float
    minimum_price: float
    final_price: Optional[float] = None
    compatibility_status: Optional[str] = None
    confidence_status: Optional[str] = None
    pricing_use: Optional[str] = None
    cost_status: Optional[str] = None
    direct_cost_is_known: Optional[bool] = None
    historical_price_preserved: Optional[bool] = None
    pricing_policy_version: Optional[str] = None
    minimum_price_net: Optional[float] = None
    minimum_price_gross: Optional[float] = None
    recommended_price_net: Optional[float] = None
    recommended_price_gross: Optional[float] = None
    final_price_net: Optional[float] = None
    margin_verdict: Optional[str] = None
    approval_status: Optional[str] = None
    valid_until: Optional[str] = None
    breakdown: dict


class GeneratePricingQuoteRequest(BaseModel):
    final_price_gross: Optional[float] = Field(default=None, ge=0)


def _serialize_rule(row, columns) -> PricingRuleResponse:
    data = dict(zip(columns, row))
    conditions = data["conditions"] or {}
    calculation = data["calculation"] or {}

    return PricingRuleResponse(
        rule_name=data["rule_name"],
        tour_id=str(data["tour_id"]),
        tour_code=data["tour_code"],
        tour_name=data["tour_name"],
        rule_type=data["rule_type"],
        confidence_status=conditions.get("confidence_status"),
        pricing_use=calculation.get("pricing_use"),
        cost_status=calculation.get("cost_status"),
        requires_manual_review=calculation.get("requires_manual_review"),
        currency=conditions.get("currency"),
        selling_price_gross=_to_float(calculation.get("selling_price_gross")),
        selling_price_net=_to_float(calculation.get("selling_price_net")),
        vat_rate=_to_float(calculation.get("vat_rate")),
        direct_cost_total=_to_float(calculation.get("direct_cost_total")),
        insurance_rule=calculation.get("insurance_rule"),
        includes=calculation.get("includes"),
        excludes=calculation.get("excludes"),
        conditions=conditions,
        calculation=calculation,
        is_active=data["is_active"],
    )


def _serialize_quote(row, columns) -> PricingQuoteResponse:
    data = dict(zip(columns, row))
    breakdown = data["breakdown"] or {}

    return PricingQuoteResponse(
        booking_code=data["booking_code"],
        booking_id=str(data["booking_id"]),
        tour_id=str(data["tour_id"]),
        tour_code=data["tour_code"],
        tour_name=data["tour_name"],
        tour_date=data["tour_date"].isoformat() if data["tour_date"] else None,
        total_cost=float(data["total_cost"]),
        recommended_price=float(data["recommended_price"]),
        minimum_price=float(data["minimum_price"]),
        final_price=_to_float(data["final_price"]),
        compatibility_status=breakdown.get("compatibility_status"),
        confidence_status=breakdown.get("confidence_status"),
        pricing_use=breakdown.get("pricing_use"),
        cost_status=breakdown.get("cost_status"),
        direct_cost_is_known=breakdown.get("direct_cost_is_known"),
        historical_price_preserved=breakdown.get("historical_price_preserved"),
        pricing_policy_version=breakdown.get("pricing_policy_version"),
        minimum_price_net=_to_float(breakdown.get("minimum_price_net")),
        minimum_price_gross=_to_float(breakdown.get("minimum_price_gross")),
        recommended_price_net=_to_float(breakdown.get("recommended_price_net")),
        recommended_price_gross=_to_float(breakdown.get("recommended_price_gross")),
        final_price_net=_to_float(breakdown.get("final_price_net")),
        margin_verdict=breakdown.get("margin_verdict"),
        approval_status=breakdown.get("approval_status"),
        valid_until=data["valid_until"].isoformat()
        if data["valid_until"]
        else None,
        breakdown=breakdown,
    )


def _quote_for_booking(cur, booking_id):
    cur.execute(
        """
        SELECT
            pq.booking_id,
            b.booking_code,
            b.tour_date,
            pq.total_cost,
            pq.recommended_price,
            pq.minimum_price,
            pq.final_price,
            pq.breakdown,
            pq.valid_until,
            t.id AS tour_id,
            t.tour_code,
            t.name AS tour_name
        FROM pricing_quotes pq
        JOIN bookings b ON b.id = pq.booking_id
        JOIN tours t ON t.id = b.tour_id
        WHERE pq.booking_id = %s
        ORDER BY pq.created_at DESC
        LIMIT 1;
        """,
        (booking_id,),
    )
    row = cur.fetchone()
    columns = [desc[0] for desc in cur.description]
    return _serialize_quote(row, columns)


@router.post("/quotes/{booking_code}/generate", response_model=PricingQuoteResponse, status_code=201)
def generate_pricing_quote(
    booking_code: str,
    request: GeneratePricingQuoteRequest = GeneratePricingQuoteRequest(),
):
    """Create a new quote snapshot for an unconfirmed booking on explicit request."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, status, tour_id
                FROM bookings
                WHERE booking_code = %s
                FOR UPDATE;
                """,
                (booking_code,),
            )
            booking = cur.fetchone()
            if booking is None:
                raise HTTPException(status_code=404, detail="Booking not found")
            booking_id, booking_status, tour_id = booking
            if str(booking_status).strip().casefold() == "confirmed":
                raise HTTPException(
                    status_code=409,
                    detail="Pricing quote generation is refused for confirmed bookings",
                )

            cur.execute(
                """
                SELECT rule_name, conditions, calculation
                FROM pricing_rules
                WHERE tour_id = %s
                  AND is_active = true
                ORDER BY rule_name DESC
                LIMIT 1;
                """,
                (tour_id,),
            )
            rule = cur.fetchone()
            if rule is None:
                raise HTTPException(
                    status_code=422,
                    detail="Active pricing rule not found for this booking's tour",
                )

            rule_name, conditions, calculation = rule
            conditions = conditions or {}
            calculation = calculation or {}
            if "vat_rate" not in calculation or calculation.get("vat_rate") is None:
                raise HTTPException(
                    status_code=422,
                    detail="Active pricing rule vat_rate is missing; quote was not generated",
                )
            try:
                result = calculate_quote(
                    vat_rate=calculation.get("vat_rate"),
                    direct_cost=calculation.get("direct_cost_total"),
                    direct_cost_is_known=calculation.get("direct_cost_is_known"),
                    rule_price_gross=calculation.get("selling_price_gross"),
                    final_price_gross=request.final_price_gross,
                )
            except PricingPolicyInputError as exc:
                raise HTTPException(status_code=422, detail=str(exc)) from None

            breakdown = {
                "pricing_policy_version": POLICY_VERSION,
                "pricing_rule_name": rule_name,
                "pricing_rule_conditions": conditions,
                "pricing_rule_calculation": calculation,
                "minimum_margin_rate": "0.30",
                "margin_basis": "net_excluding_vat",
                "vat_rate": str(result.vat_rate),
                "direct_cost_is_known": result.direct_cost_is_known,
                "cost_status": calculation.get("cost_status") or (
                    "available" if result.direct_cost_is_known else "incomplete"
                ),
                "pricing_use": calculation.get("pricing_use"),
                "minimum_price_net": str(result.minimum_price_net)
                if result.minimum_price_net is not None
                else None,
                "minimum_price_gross": str(result.minimum_price_gross),
                "recommended_price_net": str(result.recommended_price_net),
                "recommended_price_gross": str(result.recommended_price_gross),
                "final_price_net": str(result.final_price_net)
                if result.final_price_net is not None
                else None,
                "final_price_gross": str(result.final_price_gross)
                if result.final_price_gross is not None
                else None,
                "margin_verdict": result.margin_verdict,
                "approval_status": result.approval_status,
                "historical_price_preserved": True,
            }

            cur.execute(
                """
                INSERT INTO pricing_quotes (
                    booking_id,
                    total_cost,
                    recommended_price,
                    minimum_price,
                    final_price,
                    breakdown,
                    valid_until
                )
                VALUES (%s, %s, %s, %s, %s, %s, NULL);
                """,
                (
                    booking_id,
                    result.total_cost,
                    result.recommended_price_gross,
                    result.minimum_price_gross,
                    result.final_price_gross,
                    Jsonb(breakdown),
                ),
            )
            quote = _quote_for_booking(cur, booking_id)

    return quote


@router.get("/rules", response_model=list[PricingRuleResponse])
def list_pricing_rules():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    p.rule_name,
                    p.rule_type,
                    p.conditions,
                    p.calculation,
                    p.is_active,
                    t.id AS tour_id,
                    t.tour_code,
                    t.name AS tour_name
                FROM pricing_rules p
                JOIN tours t ON t.id = p.tour_id
                WHERE p.is_active = true
                ORDER BY t.tour_code, p.rule_name;
                """
            )
            rows = cur.fetchall()
            columns = [desc[0] for desc in cur.description]

    return [_serialize_rule(row, columns) for row in rows]


@router.get("/quotes", response_model=list[PricingQuoteResponse])
def list_pricing_quotes():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    pq.booking_id,
                    b.booking_code,
                    b.tour_date,
                    pq.total_cost,
                    pq.recommended_price,
                    pq.minimum_price,
                    pq.final_price,
                    pq.breakdown,
                    pq.valid_until,
                    t.id AS tour_id,
                    t.tour_code,
                    t.name AS tour_name
                FROM pricing_quotes pq
                JOIN bookings b ON b.id = pq.booking_id
                JOIN tours t ON t.id = b.tour_id
                ORDER BY b.tour_date, b.booking_code;
                """
            )
            rows = cur.fetchall()
            columns = [desc[0] for desc in cur.description]

    return [_serialize_quote(row, columns) for row in rows]


@router.get("/quotes/{booking_code}", response_model=PricingQuoteResponse)
def get_pricing_quote(booking_code: str):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    pq.booking_id,
                    b.booking_code,
                    b.tour_date,
                    pq.total_cost,
                    pq.recommended_price,
                    pq.minimum_price,
                    pq.final_price,
                    pq.breakdown,
                    pq.valid_until,
                    t.id AS tour_id,
                    t.tour_code,
                    t.name AS tour_name
                FROM pricing_quotes pq
                JOIN bookings b ON b.id = pq.booking_id
                JOIN tours t ON t.id = b.tour_id
                WHERE b.booking_code = %s
                ORDER BY pq.created_at DESC
                LIMIT 1;
                """,
                (booking_code,),
            )
            row = cur.fetchone()

            if row is None:
                raise HTTPException(
                    status_code=404,
                    detail="Pricing quote not found for this booking",
                )

            columns = [desc[0] for desc in cur.description]

    return _serialize_quote(row, columns)


@router.get("/tours/{tour_code}", response_model=PricingRuleResponse)
def get_pricing_rule_for_tour(tour_code: str):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    p.rule_name,
                    p.rule_type,
                    p.conditions,
                    p.calculation,
                    p.is_active,
                    t.id AS tour_id,
                    t.tour_code,
                    t.name AS tour_name
                FROM pricing_rules p
                JOIN tours t ON t.id = p.tour_id
                WHERE t.tour_code = %s
                  AND p.is_active = true
                ORDER BY p.rule_name DESC
                LIMIT 1;
                """,
                (tour_code,),
            )
            row = cur.fetchone()

            if row is None:
                raise HTTPException(status_code=404, detail="Active pricing rule not found for this tour")

            columns = [desc[0] for desc in cur.description]

    return _serialize_rule(row, columns)
