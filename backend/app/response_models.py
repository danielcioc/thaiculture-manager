"""Response contracts for the V1 financial and importer-review APIs.

Extra fields remain allowed so adding these schemas documents the stable
contract without dropping legacy fields returned by the existing SQL queries.
"""

from datetime import date, datetime, time
from decimal import Decimal
from typing import Any, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ExtensibleResponse(BaseModel):
    model_config = ConfigDict(extra="allow")


class FinancialKpisResponse(ExtensibleResponse):
    unpaid: int
    depositrequested: int
    depositpaid: int
    partiallypaid: int
    paid: int
    overdue: int
    total_outstanding: Decimal


class DashboardSummaryResponse(ExtensibleResponse):
    total_bookings: int
    confirmed_bookings: int
    inquiry_bookings: int
    total_revenue: Decimal
    paid_revenue: Decimal
    pending_revenue: Decimal
    outstanding_revenue: Decimal
    total_costs: Decimal
    guide_costs: Decimal
    driver_costs: Decimal
    other_costs: Decimal
    gross_margin: Decimal
    margin_percent: Decimal
    financial_kpis: FinancialKpisResponse
    currency: str


class PaymentResponse(ExtensibleResponse):
    id: UUID
    booking_id: Optional[UUID] = None
    booking_code: Optional[str] = None
    customer_name: Optional[str] = None
    amount: Decimal
    currency: str
    method: str
    status: str
    paid_at: Optional[datetime] = None
    due_at: Optional[datetime] = None
    reference: Optional[str] = None
    notes: Optional[str] = None
    booking_currency: Optional[str] = None
    currency_matches_booking: Optional[bool] = None
    financial_error: Optional[str] = None


class PaymentFiltersResponse(ExtensibleResponse):
    status: Optional[str] = None
    sort_by: str
    sort_order: str


class PaymentListResponse(ExtensibleResponse):
    count: int
    filters: Optional[PaymentFiltersResponse] = None
    items: list[PaymentResponse]


class PaymentCurrencySummaryResponse(ExtensibleResponse):
    currency: str
    draft_count: int
    requested_count: int
    pending_count: int
    paid_count: int
    partiallypaid_count: int
    overdue_count: int
    cancelled_count: int
    currency_mismatch_count: int
    collected_amount: Decimal


class PaymentsSummaryResponse(ExtensibleResponse):
    currencies: list[PaymentCurrencySummaryResponse]


class BookingListItemResponse(ExtensibleResponse):
    id: UUID
    booking_code: str
    status: str
    source: Optional[str] = None
    customer_name: Optional[str] = None
    tour_id: Optional[UUID] = None
    tour_name: Optional[str] = None
    tour_date: Optional[date] = None
    pickup_time: Optional[time] = None
    adults: Optional[int] = None
    children: Optional[int] = None
    infants: Optional[int] = None
    total_guests: Optional[int] = None
    guide_language: Optional[str] = None
    selling_price: Decimal
    deposit_amount: Optional[Decimal] = None
    currency: str
    imported_raw_tour_name: Optional[str] = None
    mapping_status: Optional[Literal["confirmed", "probable_manual_review", "unmapped"]] = None
    needs_manual_review: Optional[bool] = None
    created_at: Optional[datetime] = None
    booking_financial_status: Optional[Literal[
        "unpaid", "depositrequested", "depositpaid", "partiallypaid", "paid", "overdue"
    ]] = None
    paid_amount: Optional[Decimal] = None
    pending_amount: Optional[Decimal] = None
    balance_due: Optional[Decimal] = None


class BookingListResponse(ExtensibleResponse):
    count: int
    items: list[BookingListItemResponse]


class BookingPaymentSummaryResponse(ExtensibleResponse):
    selling_price: Decimal
    total_amount: Decimal
    deposit_amount: Optional[Decimal] = None
    deposit_paid_amount: Optional[Decimal] = None
    paid_amount: Decimal
    pending_amount: Decimal
    requested_amount: Decimal
    outstanding_amount: Decimal
    balance_due: Decimal
    remaining_unrequested_amount: Decimal
    payment_status: str
    booking_financial_status: Literal[
        "unpaid", "depositrequested", "depositpaid", "partiallypaid", "paid", "overdue"
    ]
    currency: str


class BookingOperationsSummaryResponse(ExtensibleResponse):
    selling_price: Decimal
    revenue_ex_vat: Decimal
    vat_amount: Decimal
    guide_cost: Optional[Decimal] = None
    driver_cost: Optional[Decimal] = None
    other_cost: Optional[Decimal] = None
    total_cost: Optional[Decimal] = None
    gross_margin: Optional[Decimal] = None
    margin_percent: Optional[Decimal] = None
    currency: str
    cost_status: Optional[str] = None
    pricing_use: Optional[str] = None
    direct_cost_is_known: Optional[bool] = None
    cost_source: Optional[str] = None


class BookingFullDetailResponse(ExtensibleResponse):
    booking: BookingListItemResponse
    payments: list[PaymentResponse]
    payment_summary: BookingPaymentSummaryResponse
    assignments: list[dict[str, Any]]
    operations_summary: BookingOperationsSummaryResponse


class ImportReviewDecisionResponse(ExtensibleResponse):
    booking_id: UUID
    booking_code: str
    status: str
    imported_raw_tour_name: Optional[str] = None
    mapping_status: Literal["confirmed", "probable_manual_review", "unmapped"]
    needs_manual_review: bool
    tour_id: Optional[UUID] = None
    tour_name: Optional[str] = None
    review_event_id: UUID
    replayed: bool


API_ERROR_RESPONSES = {
    400: {"description": "Request is invalid or explicit confirmation is missing."},
    401: {"description": "Authentication is missing or invalid."},
    403: {"description": "The authenticated user lacks the required permission."},
    404: {"description": "The requested booking or resource was not found."},
    409: {"description": "The request conflicts with current state or an idempotency key."},
    422: {"description": "Request validation failed."},
}
