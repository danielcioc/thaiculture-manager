"""Versioned pricing policy for newly generated pricing quotes."""

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Optional


POLICY_VERSION = "minimum-margin-30-v1"
MINIMUM_MARGIN = Decimal("0.30")
MARGIN_DIVISOR = Decimal("0.70")
CENT = Decimal("0.01")


class PricingPolicyInputError(ValueError):
    """Raised when required inputs cannot safely produce a pricing quote."""


@dataclass(frozen=True)
class QuoteCalculation:
    total_cost: Decimal
    minimum_price_net: Optional[Decimal]
    minimum_price_gross: Decimal
    recommended_price_net: Decimal
    recommended_price_gross: Decimal
    final_price_net: Optional[Decimal]
    final_price_gross: Optional[Decimal]
    margin_verdict: str
    approval_status: str
    direct_cost_is_known: bool
    vat_rate: Decimal


def money(value: Decimal) -> Decimal:
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


def decimal_input(value, field_name: str) -> Decimal:
    try:
        result = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        raise PricingPolicyInputError(f"{field_name} is missing or invalid") from None
    if not result.is_finite():
        raise PricingPolicyInputError(f"{field_name} is missing or invalid")
    return result


def calculate_quote(
    *,
    vat_rate,
    direct_cost,
    rule_price_gross,
    direct_cost_is_known: Optional[bool] = None,
    final_price_gross=None,
) -> QuoteCalculation:
    vat = decimal_input(vat_rate, "Active pricing rule vat_rate")
    if vat < 0 or vat > 1:
        raise PricingPolicyInputError("Active pricing rule vat_rate must be between 0 and 1")

    rule_gross = money(decimal_input(rule_price_gross, "Active pricing rule selling_price_gross"))
    if rule_gross < 0:
        raise PricingPolicyInputError("Active pricing rule selling_price_gross must not be negative")

    cost_known = direct_cost is not None if direct_cost_is_known is None else direct_cost_is_known
    if direct_cost is None:
        cost_known = False

    gross_factor = Decimal("1") + vat
    supplied_final = None
    if final_price_gross is not None:
        supplied_final = money(decimal_input(final_price_gross, "final_price_gross"))
        if supplied_final < 0:
            raise PricingPolicyInputError("final_price_gross must not be negative")

    if not cost_known:
        effective_final = supplied_final
        recommended_net = money(rule_gross / gross_factor)
        final_net = money(effective_final / gross_factor) if effective_final is not None else None
        return QuoteCalculation(
            total_cost=Decimal("0.00"),
            minimum_price_net=None,
            minimum_price_gross=Decimal("0.00"),
            recommended_price_net=recommended_net,
            recommended_price_gross=rule_gross,
            final_price_net=final_net,
            final_price_gross=effective_final,
            margin_verdict="direct_cost_unknown",
            approval_status="not_required",
            direct_cost_is_known=False,
            vat_rate=vat,
        )

    cost = money(decimal_input(direct_cost, "Active pricing rule direct_cost_total"))
    if cost < 0:
        raise PricingPolicyInputError("Active pricing rule direct_cost_total must not be negative")

    minimum_net = money(cost / MARGIN_DIVISOR)
    minimum_gross = money(minimum_net * gross_factor)
    recommended_gross = max(rule_gross, minimum_gross)
    recommended_net = money(recommended_gross / gross_factor)
    effective_final = supplied_final
    final_net = money(effective_final / gross_factor) if effective_final is not None else None
    evaluated_gross = effective_final if effective_final is not None else recommended_gross
    evaluated_net = money(evaluated_gross / gross_factor)
    margin_verdict = "meets_margin" if evaluated_net >= minimum_net else "below_margin"

    return QuoteCalculation(
        total_cost=cost,
        minimum_price_net=minimum_net,
        minimum_price_gross=minimum_gross,
        recommended_price_net=recommended_net,
        recommended_price_gross=recommended_gross,
        final_price_net=final_net,
        final_price_gross=effective_final,
        margin_verdict=margin_verdict,
        approval_status="manual_override_required" if margin_verdict == "below_margin" else "not_required",
        direct_cost_is_known=True,
        vat_rate=vat,
    )
