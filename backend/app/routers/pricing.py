from decimal import Decimal
from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.database import get_connection

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
