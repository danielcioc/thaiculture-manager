"""Narrow public website quote and inquiry API.

The API is disabled by default. It returns only customer-facing pricing and
creates website submissions as Inquiry bookings; internal workflow and
financial state remain owned by ThaiCulture Manager.
"""

import hashlib
import json
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Any
from urllib.parse import urlparse
from uuid import UUID, uuid4

from fastapi import APIRouter, Header, HTTPException, status
from pydantic import BaseModel, EmailStr, Field, model_validator
from psycopg.types.json import Jsonb

from app.config import settings
from app.database import get_connection
from app.pricing_policy import POLICY_VERSION, PricingPolicyInputError, calculate_quote


router = APIRouter(prefix="/api/website", tags=["Website integration"])
QUOTE_TTL = timedelta(minutes=30)
SUPPORTED_CURRENCIES = frozenset({"THB", "EUR", "USD"})


class WebsitePricingRequest(BaseModel):
    website_tour_id: str = Field(min_length=1, max_length=255)
    date: date
    adults: int = Field(ge=0, le=30)
    children: int = Field(default=0, ge=0, le=30)
    extras: list[str] = Field(default_factory=list, max_length=20)
    currency: str = Field(min_length=3, max_length=3)

    @model_validator(mode="after")
    def validate_party_and_extras(self):
        if self.adults + self.children < 1:
            raise ValueError("At least one adult or child is required")
        if self.extras:
            raise ValueError("No extras are currently configured for website pricing")
        if self.date < date.today():
            raise ValueError("Travel date must be today or later")
        if self.currency != self.currency.upper() or self.currency not in SUPPORTED_CURRENCIES:
            raise ValueError("Currency must be a supported uppercase ISO code")
        return self


class WebsiteCustomer(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    email: EmailStr
    phone: str = Field(min_length=1, max_length=50)


class WebsiteBookingRequest(BaseModel):
    quote_id: UUID
    date: date
    adults: int = Field(ge=0, le=30)
    children: int = Field(default=0, ge=0, le=30)
    extras: list[str] = Field(default_factory=list, max_length=20)
    currency: str = Field(min_length=3, max_length=3)
    customer: WebsiteCustomer
    notes: str = Field(default="", max_length=2000)

    @model_validator(mode="after")
    def validate_party(self):
        if self.adults + self.children < 1:
            raise ValueError("At least one adult or child is required")
        if self.extras:
            raise ValueError("No extras are currently configured for website pricing")
        if self.date < date.today():
            raise ValueError("Travel date must be today or later")
        if self.currency != self.currency.upper() or self.currency not in SUPPORTED_CURRENCIES:
            raise ValueError("Currency must be a supported uppercase ISO code")
        return self


def _ensure_enabled():
    if not settings.website_integration_enabled:
        raise HTTPException(status_code=404, detail="Website integration is disabled")


def _slug(value: str) -> str:
    path = urlparse(value).path
    return path.rstrip("/").rsplit("/", 1)[-1]


def _money(value: Any) -> Decimal:
    return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _canonical_payload_hash(payload: dict[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _find_public_rule(cur, website_tour_id: str):
    slug = _slug(website_tour_id)
    cur.execute(
        """
        SELECT t.id, t.tour_code, t.name, t.website_url,
               pr.rule_name, pr.conditions, pr.calculation
        FROM tours t
        JOIN LATERAL (
            SELECT rule_name, conditions, calculation
            FROM pricing_rules
            WHERE tour_id = t.id AND is_active = true
              AND calculation->>'pricing_use' = 'approved_for_quote'
            ORDER BY rule_name DESC
            LIMIT 1
        ) pr ON true
        WHERE t.is_active = true
          AND regexp_replace(t.website_url, '^.*/', '') = %s
        ORDER BY t.tour_code;
        """,
        (slug,),
    )
    rows = cur.fetchall()
    if not rows:
        raise HTTPException(status_code=404, detail="No active website pricing rule exists for this tour")
    if len(rows) > 1:
        raise HTTPException(status_code=409, detail="Website tour mapping is ambiguous")
    return rows[0]


def _calculate_public_price(conditions: dict, calculation: dict, request: WebsitePricingRequest):
    conditions = conditions or {}
    calculation = calculation or {}
    if "vat_rate" not in calculation or calculation.get("vat_rate") is None:
        raise HTTPException(status_code=422, detail="Active pricing rule VAT rate is missing")
    rule_currency = conditions.get("currency")
    if not rule_currency or rule_currency != request.currency:
        raise HTTPException(status_code=422, detail="Requested currency does not match the active pricing rule")
    if calculation.get("pricing_use") != "approved_for_quote":
        raise HTTPException(status_code=422, detail="Active pricing rule is not approved for customer quotes")

    guest_count = request.adults + request.children
    minimum = conditions.get("min_guests")
    maximum = conditions.get("max_guests")
    if minimum is not None and guest_count < int(minimum):
        raise HTTPException(status_code=422, detail=f"This pricing rule requires at least {minimum} guests")
    if maximum is not None and guest_count > int(maximum):
        raise HTTPException(status_code=422, detail=f"This pricing rule allows at most {maximum} guests")

    basis = conditions.get("group_size_basis")
    if basis not in {"per_person", "per_booking"}:
        raise HTTPException(status_code=422, detail="Active pricing rule has no supported group-size basis")
    multiplier = guest_count if basis == "per_person" else 1
    try:
        result = calculate_quote(
            vat_rate=calculation.get("vat_rate"),
            direct_cost=calculation.get("direct_cost_total"),
            direct_cost_is_known=calculation.get("direct_cost_is_known"),
            rule_price_gross=calculation.get("selling_price_gross"),
        )
    except PricingPolicyInputError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None

    total = _money(result.recommended_price_gross * multiplier)
    total_cost = _money(result.total_cost * multiplier)
    minimum_gross = _money(result.minimum_price_gross * multiplier)
    breakdown = {
        "pricing_policy_version": POLICY_VERSION,
        "pricing_rule_conditions": conditions,
        "pricing_rule_calculation": calculation,
        "pricing_rule_currency": rule_currency,
        "group_size_basis": basis,
        "guest_count": guest_count,
        "multiplier": multiplier,
        "minimum_margin_rate": "0.30",
        "margin_basis": "net_excluding_vat",
        "vat_rate": str(result.vat_rate),
        "direct_cost_is_known": result.direct_cost_is_known,
        "minimum_price_net": str(_money(result.minimum_price_net * multiplier)) if result.minimum_price_net is not None else None,
        "minimum_price_gross": str(minimum_gross),
        "recommended_price_net": str(_money(result.recommended_price_net * multiplier)),
        "recommended_price_gross": str(total),
        "margin_verdict": result.margin_verdict,
        "approval_status": result.approval_status,
        "extras_total": "0.00",
    }
    return total, total_cost, minimum_gross, breakdown


@router.get("/catalog")
def public_catalog():
    _ensure_enabled()
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT t.tour_code, t.name, t.website_url,
                   pr.conditions, pr.calculation
            FROM tours t
            JOIN LATERAL (
                SELECT conditions, calculation
                FROM pricing_rules
                WHERE tour_id = t.id AND is_active = true
                  AND calculation->>'pricing_use' = 'approved_for_quote'
                ORDER BY rule_name DESC LIMIT 1
            ) pr ON true
            WHERE t.is_active = true AND t.website_url IS NOT NULL
            ORDER BY t.name;
            """
        )
        rows = cur.fetchall()
    items = []
    for tour_code, name, website_url, conditions, calculation in rows:
        conditions = conditions or {}
        calculation = calculation or {}
        items.append({
            "website_tour_id": _slug(website_url),
            "manager_tour_id": tour_code,
            "slug": _slug(website_url),
            "english_title": name,
            "active": True,
            "currency": conditions.get("currency"),
            "pricing_mode": conditions.get("group_size_basis"),
            "min_guests": conditions.get("min_guests"),
            "max_guests": conditions.get("max_guests"),
        })
    return {"count": len(items), "items": items}


@router.post("/pricing", status_code=status.HTTP_201_CREATED)
def create_website_price_preview(request: WebsitePricingRequest):
    _ensure_enabled()
    quote_id = uuid4()
    expires_at = datetime.now(timezone.utc) + QUOTE_TTL
    with get_connection() as conn, conn.cursor() as cur:
        tour_id, tour_code, tour_name, website_url, rule_name, conditions, calculation = _find_public_rule(cur, request.website_tour_id)
        total, total_cost, minimum_gross, breakdown = _calculate_public_price(conditions, calculation, request)
        cur.execute(
            """
            INSERT INTO website_quote_previews (
                id, tour_id, tour_code, tour_name, website_tour_id, tour_date,
                adults, children, extras, currency, total, total_cost,
                minimum_price, rule_name, pricing_policy_version, breakdown,
                expires_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
            """,
            (
                quote_id, tour_id, tour_code, tour_name, _slug(request.website_tour_id),
                request.date, request.adults, request.children, Jsonb(request.extras),
                request.currency, total, total_cost, minimum_gross, rule_name,
                POLICY_VERSION, Jsonb(breakdown), expires_at,
            ),
        )
    return {
        "quote_id": str(quote_id),
        "website_tour_id": _slug(request.website_tour_id),
        "currency": request.currency,
        "subtotal": float(total),
        "extras_total": 0.0,
        "total": float(total),
        "expires_at": expires_at.isoformat(),
        "pricing_version": POLICY_VERSION,
    }


def _normalized_booking_payload(request: WebsiteBookingRequest) -> dict[str, Any]:
    return {
        "quote_id": str(request.quote_id),
        "date": request.date.isoformat(),
        "adults": request.adults,
        "children": request.children,
        "extras": sorted(request.extras),
        "currency": request.currency,
        "customer": {
            "name": request.customer.name.strip(),
            "email": str(request.customer.email).strip().casefold(),
            "phone": request.customer.phone.strip(),
        },
        "notes": request.notes.strip(),
        "source": "Website",
    }


@router.post("/bookings", status_code=status.HTTP_201_CREATED)
def create_website_booking(
    request: WebsiteBookingRequest,
    idempotency_key: UUID = Header(alias="Idempotency-Key"),
):
    _ensure_enabled()
    normalized = _normalized_booking_payload(request)
    payload_hash = _canonical_payload_hash(normalized)
    now = datetime.now(timezone.utc)

    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO website_booking_idempotency (idempotency_key, payload_hash)
            VALUES (%s, %s)
            ON CONFLICT (idempotency_key) DO NOTHING
            RETURNING idempotency_key;
            """,
            (idempotency_key, payload_hash),
        )
        inserted = cur.fetchone()
        if inserted is None:
            cur.execute(
                """
                SELECT payload_hash, response_payload
                FROM website_booking_idempotency
                WHERE idempotency_key = %s
                FOR UPDATE;
                """,
                (idempotency_key,),
            )
            existing_hash, response_payload = cur.fetchone()
            if existing_hash != payload_hash:
                raise HTTPException(status_code=409, detail="Idempotency-Key was already used with a different request")
            if response_payload is None:
                raise HTTPException(status_code=409, detail="The original booking request is still being processed")
            response_payload = dict(response_payload)
            response_payload["replayed"] = True
            return response_payload

        cur.execute(
            """
            SELECT id, tour_id, tour_code, tour_name, website_tour_id, tour_date,
                   adults, children, extras, currency, total, total_cost,
                   minimum_price, rule_name, pricing_policy_version, breakdown,
                   expires_at, consumed_booking_id
            FROM website_quote_previews WHERE id = %s FOR UPDATE;
            """,
            (request.quote_id,),
        )
        quote = cur.fetchone()
        if quote is None:
            raise HTTPException(status_code=404, detail="Pricing quote not found")
        (
            quote_id, tour_id, tour_code, tour_name, website_tour_id, quote_date,
            adults, children, extras, currency, total, total_cost, minimum_price,
            rule_name, policy_version, breakdown, expires_at, consumed_booking_id,
        ) = quote
        if expires_at <= now:
            raise HTTPException(status_code=409, detail="Pricing quote has expired; request a new quote")
        if consumed_booking_id is not None:
            raise HTTPException(status_code=409, detail="Pricing quote was already submitted")
        if (
            quote_date != request.date or adults != request.adults or children != request.children
            or list(extras or []) != request.extras or currency != request.currency
        ):
            raise HTTPException(status_code=409, detail="Booking request does not match the pricing quote")

        email = str(request.customer.email).strip().casefold()
        cur.execute(
            "SELECT id FROM customers WHERE lower(email) = %s ORDER BY created_at LIMIT 1 FOR UPDATE;",
            (email,),
        )
        customer_row = cur.fetchone()
        if customer_row:
            customer_id = customer_row[0]
        else:
            cur.execute(
                """
                INSERT INTO customers (display_name, email, phone, preferred_language)
                VALUES (%s, %s, %s, 'EN') RETURNING id;
                """,
                (request.customer.name.strip(), email, request.customer.phone.strip()),
            )
            customer_id = cur.fetchone()[0]

        booking_code = f"TCT-WEB-{now:%Y%m%d}-{uuid4().hex[:10].upper()}"
        cur.execute(
            """
            INSERT INTO bookings (
                booking_code, status, source, customer_id, tour_id, tour_date,
                adults, children, selling_price, currency
            ) VALUES (%s, 'Inquiry', 'Website', %s, %s, %s, %s, %s, 0, %s)
            RETURNING id, booking_code, status;
            """,
            (booking_code, customer_id, tour_id, quote_date, adults, children, currency),
        )
        booking_id, booking_code, booking_status = cur.fetchone()

        quote_breakdown = dict(breakdown or {})
        quote_breakdown.update({
            "website_quote_id": str(quote_id),
            "website_tour_id": website_tour_id,
            "tour_code": tour_code,
            "tour_name": tour_name,
            "rule_name": rule_name,
            "requested_date": quote_date.isoformat(),
            "adults": adults,
            "children": children,
            "extras": extras or [],
            "currency": currency,
            "pricing_policy_version": policy_version,
        })
        cur.execute(
            """
            INSERT INTO pricing_quotes (
                booking_id, total_cost, recommended_price, minimum_price,
                final_price, breakdown, valid_until
            ) VALUES (%s, %s, %s, %s, NULL, %s, %s)
            RETURNING id;
            """,
            (booking_id, total_cost, total, minimum_price, Jsonb(quote_breakdown), expires_at.date()),
        )
        cur.execute(
            "UPDATE website_quote_previews SET consumed_booking_id = %s WHERE id = %s;",
            (booking_id, quote_id),
        )
        response_payload = {
            "booking_id": str(booking_id),
            "booking_reference": booking_code,
            "status": booking_status,
            "total": float(total),
            "currency": currency,
            "proforma_status": "not_generated",
            "replayed": False,
        }
        cur.execute(
            "UPDATE website_booking_idempotency SET booking_id = %s, response_payload = %s WHERE idempotency_key = %s;",
            (booking_id, Jsonb(response_payload), idempotency_key),
        )
    return response_payload
