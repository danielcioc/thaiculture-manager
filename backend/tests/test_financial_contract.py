import os
import unittest
from datetime import datetime, timezone
from decimal import Decimal
from urllib.parse import urlparse
from uuid import uuid4
from unittest.mock import patch

from app.financials import aggregate_payment_records, booking_financial_summary, dashboard_financial_kpis, normalize_payment_status


class BookingFinancialSummaryTests(unittest.TestCase):
    def test_confirmed_payment_aggregation_and_statuses(self):
        cases = [
            ("10500", "10500", "0", "paid", "10500"),
            ("10500", "12000", "0", "paid", "12000"),
            ("10500", "1200", "0", "partiallypaid", "1200"),
            ("10500", "0", "1200", "depositrequested", "1200"),
            ("10500", "0", "0", "unpaid", "0"),
        ]
        for selling, paid, pending, expected_status, expected_requested in cases:
            with self.subTest(expected_status=expected_status):
                summary = booking_financial_summary(
                    Decimal(selling), None, Decimal(paid), Decimal(pending)
                )
                self.assertEqual(summary["booking_financial_status"], expected_status)
                self.assertEqual(summary["requested_amount"], Decimal(expected_requested))

    def test_financial_status_cases_and_balance_never_negative(self):
        cases = [
            (None, "0", "0", False, "unpaid"),
            (None, "0", "500", False, "depositrequested"),
            ("1500", "1500", "0", False, "depositpaid"),
            (None, "500", "0", False, "partiallypaid"),
            (None, "100", "400", False, "partiallypaid"),
            (None, "10000", "0", False, "paid"),
            (None, "100", "0", True, "overdue"),
        ]
        for deposit, paid, pending, overdue, expected in cases:
            with self.subTest(expected=expected):
                summary = booking_financial_summary(
                    Decimal("10000"), Decimal(deposit) if deposit else None,
                    Decimal(paid), Decimal(pending), overdue,
                )
                self.assertEqual(summary["booking_financial_status"], expected)
                self.assertGreaterEqual(summary["balance_due"], Decimal("0.00"))

    def test_payment_records_only_count_valid_positive_same_currency_amounts(self):
        result = aggregate_payment_records([
            {"amount": "100", "currency": "THB", "status": "paid"},
            {"amount": "200", "currency": "THB", "status": "partiallypaid"},
            {"amount": "25", "currency": "THB", "status": "pending"},
            {"amount": "900", "currency": "THB", "status": "cancelled"},
            {"amount": "400", "currency": "USD", "status": "paid"},
            {"amount": "-10", "currency": "THB", "status": "paid"},
        ], "THB")
        self.assertEqual(result["paid_amount"], Decimal("300.00"))
        self.assertEqual(result["pending_amount"], Decimal("25.00"))

    def test_payment_status_contract_and_legacy_alias(self):
        for status in ("draft", "requested", "pending", "paid", "partiallypaid", "overdue", "cancelled"):
            self.assertEqual(normalize_payment_status(status), status)
        self.assertEqual(normalize_payment_status("Partially_Paid"), "partiallypaid")
        with self.assertRaises(ValueError):
            normalize_payment_status("refunded")

    def test_expired_open_payment_derives_overdue(self):
        now = datetime(2026, 10, 16, tzinfo=timezone.utc)
        result = aggregate_payment_records([
            {
                "amount": "75", "currency": "THB", "status": "pending",
                "due_at": datetime(2026, 10, 15, tzinfo=timezone.utc),
            },
        ], "THB", now=now)
        summary = booking_financial_summary(100, None, result["paid_amount"], result["pending_amount"], result["has_overdue"])
        self.assertEqual(result["pending_amount"], Decimal("75.00"))
        self.assertEqual(summary["booking_financial_status"], "overdue")

    def test_dashboard_kpis_use_canonical_status_and_outstanding_derivation(self):
        rows = [
            {"total_amount": 100, "deposit_amount": None, "paid_amount": 0, "pending_amount": 0, "has_overdue": False},
            {"total_amount": 100, "deposit_amount": None, "paid_amount": 0, "pending_amount": 20, "has_overdue": False},
            {"total_amount": 100, "deposit_amount": 50, "paid_amount": 50, "pending_amount": 0, "has_overdue": False},
            {"total_amount": 100, "deposit_amount": None, "paid_amount": 30, "pending_amount": 0, "has_overdue": False},
            {"total_amount": 100, "deposit_amount": None, "paid_amount": 100, "pending_amount": 0, "has_overdue": False},
            {"total_amount": 100, "deposit_amount": None, "paid_amount": 10, "pending_amount": 40, "has_overdue": True},
        ]
        result = dashboard_financial_kpis(rows)
        self.assertEqual(result["unpaid"], 1)
        self.assertEqual(result["depositrequested"], 1)
        self.assertEqual(result["depositpaid"], 1)
        self.assertEqual(result["partiallypaid"], 1)
        self.assertEqual(result["paid"], 1)
        self.assertEqual(result["overdue"], 1)
        self.assertEqual(result["total_outstanding"], Decimal("410.00"))


class PaymentPayloadValidationTests(unittest.TestCase):
    def test_new_payment_statuses_are_accepted_and_unknown_statuses_rejected(self):
        from pydantic import ValidationError
        from app.routers.payments import PaymentCreate

        base = {
            "booking_id": str(uuid4()), "amount": "1.00", "method": "Bank transfer",
        }
        for status in ("draft", "requested", "pending", "paid", "partiallypaid", "overdue", "cancelled"):
            with self.subTest(status=status):
                self.assertEqual(PaymentCreate(**base, status=status).status, status)
        with self.assertRaises(ValidationError):
            PaymentCreate(**base, status="refunded")

    def test_currency_requires_three_letters_and_positive_amount(self):
        from pydantic import ValidationError
        from app.routers.payments import PaymentCreate

        base = {
            "booking_id": str(uuid4()), "amount": "1.00", "method": "Cash", "status": "paid",
        }
        self.assertEqual(PaymentCreate(**base, currency="thb").currency, "THB")
        with self.assertRaises(ValidationError):
            PaymentCreate(**base, currency="   ")
        with self.assertRaises(ValidationError):
            PaymentCreate(**{**base, "amount": "0"})

    def test_booking_deposit_must_not_exceed_total(self):
        from pydantic import ValidationError
        from app.routers.bookings import BookingCreate

        base = {"booking_code": "TST-DEPOSIT", "selling_price": "1000.00"}
        self.assertEqual(BookingCreate(**base, deposit_amount="1000.00").deposit_amount, Decimal("1000.00"))
        with self.assertRaises(ValidationError):
            BookingCreate(**base, deposit_amount="1000.01")


TEST_DATABASE_URL = os.getenv("TCT_TEST_DATABASE_URL")
_parsed_test_url = urlparse(TEST_DATABASE_URL) if TEST_DATABASE_URL else None
_safe_test_database = bool(
    _parsed_test_url
    and "test" in _parsed_test_url.path.lower()
    and _parsed_test_url.hostname in {"localhost", "127.0.0.1", "postgres-test"}
)


@unittest.skipUnless(_safe_test_database, "requires isolated local TCT_TEST_DATABASE_URL")
class FinancialEndpointIntegrationTests(unittest.TestCase):
    """HTTP route tests against a dedicated PostgreSQL test database/schema."""

    @classmethod
    def setUpClass(cls):
        import psycopg
        from app.routers import bookings, dashboard, invoices, payments

        cls.psycopg = psycopg
        cls.schema = f"financial_test_{uuid4().hex[:12]}"

        with psycopg.connect(TEST_DATABASE_URL, autocommit=True) as conn:
            conn.execute(f'CREATE SCHEMA "{cls.schema}"')
            conn.execute(f'SET search_path TO "{cls.schema}"')
            conn.execute("""
                CREATE TABLE customers (
                    id uuid PRIMARY KEY,
                    display_name text,
                    email text,
                    phone text,
                    whatsapp text,
                    country text,
                    nationality text,
                    preferred_language text
                );
                CREATE TABLE bookings (
                    id uuid PRIMARY KEY,
                    booking_code text UNIQUE NOT NULL,
                    selling_price numeric(12,2) NOT NULL,
                    deposit_amount numeric(12,2),
                    currency char(3) NOT NULL DEFAULT 'THB',
                    customer_id uuid REFERENCES customers(id),
                    status text NOT NULL DEFAULT 'Inquiry',
                    source text,
                    tour_id uuid,
                    tour_date date,
                    pickup_time time,
                    pickup_location_id uuid,
                    dropoff_location_id uuid,
                    adults int DEFAULT 0,
                    children int DEFAULT 0,
                    infants int DEFAULT 0,
                    guide_language text,
                    imported_raw_tour_name text,
                    mapping_status text,
                    needs_manual_review boolean,
                    created_at timestamptz DEFAULT now()
                );
                CREATE TABLE tours (
                    id uuid PRIMARY KEY,
                    tour_code text,
                    name text,
                    category text,
                    default_duration_hours numeric,
                    website_url text
                );
                CREATE TABLE locations (
                    id uuid PRIMARY KEY,
                    name text,
                    address text,
                    google_maps_url text
                );
                CREATE TABLE payments (
                    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
                    booking_id uuid REFERENCES bookings(id),
                    amount numeric(12,2) NOT NULL,
                    currency char(3) DEFAULT 'THB',
                    method varchar(40) NOT NULL,
                    status varchar(40) NOT NULL,
                    paid_at timestamptz,
                    due_at timestamptz,
                    reference varchar(255),
                    notes text
                );
                CREATE TABLE guides (id uuid PRIMARY KEY, name text, languages jsonb, phone text, line_id text);
                CREATE TABLE drivers (id uuid PRIMARY KEY, name text, phone text, line_id text);
                CREATE TABLE assignments (
                    id uuid PRIMARY KEY DEFAULT gen_random_uuid(), booking_id uuid, assignment_type text,
                    guide_id uuid, driver_id uuid, cost numeric(12,2), status text, notes text
                );
                CREATE TABLE pricing_quotes (
                    id uuid PRIMARY KEY DEFAULT gen_random_uuid(), booking_id uuid,
                    total_cost numeric(12,2), breakdown jsonb, created_at timestamptz DEFAULT now()
                );
                CREATE TABLE invoices (
                    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
                    booking_id uuid REFERENCES bookings(id),
                    invoice_no varchar(50) UNIQUE NOT NULL,
                    invoice_type varchar(30) NOT NULL,
                    amount numeric(12,2) NOT NULL,
                    status varchar(40) DEFAULT 'draft',
                    issued_at timestamptz DEFAULT now()
                );
            """)

        def test_connection():
            return psycopg.connect(TEST_DATABASE_URL, options=f"-csearch_path={cls.schema}")

        cls.connection_factory = staticmethod(test_connection)
        cls.patches = [
            patch.object(payments, "get_connection", test_connection),
            patch.object(bookings, "get_connection", test_connection),
            patch.object(dashboard, "get_connection", test_connection),
            patch.object(invoices, "get_connection", test_connection),
        ]
        for patcher in cls.patches:
            patcher.start()

    @classmethod
    def tearDownClass(cls):
        for patcher in cls.patches:
            patcher.stop()
        with cls.psycopg.connect(TEST_DATABASE_URL, autocommit=True) as conn:
            conn.execute(f'DROP SCHEMA IF EXISTS "{cls.schema}" CASCADE')

    def setUp(self):
        self.customer_id = uuid4()
        self.booking_id = uuid4()
        self.booking_code = f"TST-FIN-{uuid4().hex[:10]}"
        with self.connection_factory() as conn:
            conn.execute("TRUNCATE payments, assignments, pricing_quotes, invoices, bookings, customers CASCADE")
            conn.execute(
                "INSERT INTO customers (id, display_name, email) VALUES (%s, %s, %s)",
                (self.customer_id, "Financial Test Customer", "test@example.invalid"),
            )
            conn.execute(
                "INSERT INTO bookings (id, booking_code, selling_price, currency, customer_id, status, source) "
                "VALUES (%s, %s, %s, 'THB', %s, 'Inquiry', 'test')",
                (self.booking_id, self.booking_code, Decimal("10500.00"), self.customer_id),
            )
            conn.commit()

    def test_post_payment_persists_all_fields_and_updates_booking_summary(self):
        from app.routers import bookings, payments
        from app.routers.payments import PaymentCreate

        payment = payments.create_payment(PaymentCreate(
            booking_id=self.booking_id,
            amount=Decimal("1200.00"),
            currency="THB",
            method="Thai QR",
            status="Paid",
            reference="receipt-test-1",
            notes="first installment",
        ))
        self.assertEqual(payment["amount"], Decimal("1200.00"))
        self.assertEqual(payment["reference"], "receipt-test-1")
        self.assertEqual(payment["notes"], "first installment")
        self.assertIn("due_at", payment)
        payments.create_payment(PaymentCreate(
            booking_id=self.booking_id,
            amount=Decimal("400.00"),
            method="Thai QR",
            status="Pending",
        ))

        summary = bookings.get_booking_payment_summary(self.booking_code)
        self.assertEqual(Decimal(str(summary["paid_amount"])), Decimal("1200.00"))
        self.assertEqual(Decimal(str(summary["pending_amount"])), Decimal("400.00"))
        self.assertEqual(Decimal(str(summary["requested_amount"])), Decimal("1600.00"))
        self.assertEqual(summary["booking_financial_status"], "partiallypaid")

    def test_booking_without_payments_returns_zero_balances(self):
        from app.routers import bookings

        summary = bookings.get_booking_payment_summary(self.booking_code)
        self.assertEqual(Decimal(str(summary["total_amount"])), Decimal("10500.00"))
        self.assertEqual(Decimal(str(summary["paid_amount"])), Decimal("0.00"))
        self.assertEqual(Decimal(str(summary["balance_due"])), Decimal("10500.00"))
        self.assertEqual(summary["booking_financial_status"], "unpaid")

    def test_payments_list_filters_and_sorts_with_explicit_currency_mismatch(self):
        from app.routers.payments import list_payments

        with self.connection_factory() as conn:
            conn.execute(
                "INSERT INTO payments (booking_id, amount, currency, method, status, paid_at, due_at) VALUES "
                "(%s, 100, 'THB', 'cash', 'paid', now(), now()), "
                "(%s, 300, 'THB', 'cash', 'cancelled', now() - interval '1 day', now()), "
                "(%s, 50, 'USD', 'cash', 'paid', now() - interval '2 days', now())",
                (self.booking_id, self.booking_id, self.booking_id),
            )
            conn.commit()

        result = list_payments(sort_by="due_at", sort_order="asc")
        self.assertEqual(result["count"], 3)
        mismatch = next(item for item in result["items"] if item["currency"] == "USD")
        self.assertFalse(mismatch["currency_matches_booking"])
        self.assertEqual(mismatch["financial_error"], "currency_mismatch")
        paid = list_payments(status="paid")
        self.assertEqual(paid["count"], 2)
        self.assertTrue(all(item["status"] == "paid" for item in paid["items"]))

    def test_payment_summary_excludes_cancelled_draft_and_currency_mismatch(self):
        from app.routers.payments import payments_summary

        with self.connection_factory() as conn:
            conn.execute(
                "INSERT INTO payments (booking_id, amount, currency, method, status) VALUES "
                "(%s, 500, 'THB', 'cash', 'paid'), "
                "(%s, 300, 'THB', 'cash', 'partiallypaid'), "
                "(%s, 250, 'THB', 'cash', 'cancelled'), "
                "(%s, 200, 'THB', 'cash', 'draft'), "
                "(%s, 100, 'USD', 'cash', 'paid')",
                (self.booking_id,) * 5,
            )
            conn.commit()

        result = payments_summary()
        thb = next(item for item in result["currencies"] if item["currency"] == "THB")
        usd = next(item for item in result["currencies"] if item["currency"] == "USD")
        self.assertEqual(thb["collected_amount"], Decimal("800.00"))
        self.assertEqual(thb["cancelled_count"], 1)
        self.assertEqual(thb["draft_count"], 1)
        self.assertEqual(usd["collected_amount"], Decimal("0.00"))
        self.assertEqual(usd["currency_mismatch_count"], 1)

    def test_invalid_payment_status_filter_returns_422_without_database_access(self):
        from fastapi import HTTPException
        from app.routers.payments import list_payments

        with self.assertRaises(HTTPException) as error:
            list_payments(status="unknown-status")
        self.assertEqual(error.exception.status_code, 422)

    def test_dashboard_financial_kpis_dont_change_operational_margin_contract(self):
        from app.routers import dashboard

        with self.connection_factory() as conn:
            conn.execute(
                "INSERT INTO assignments (booking_id, assignment_type, cost) VALUES (%s, 'guide', 6000)",
                (self.booking_id,),
            )
            conn.commit()

        summary = dashboard.dashboard_summary()
        self.assertEqual(summary["total_revenue"], Decimal("10500.00"))
        self.assertEqual(summary["total_costs"], Decimal("6000.00"))
        self.assertEqual(summary["gross_margin"], Decimal("4500.00"))
        self.assertEqual(Decimal(str(summary["margin_percent"])), Decimal("42.86"))
        self.assertEqual(summary["financial_kpis"]["unpaid"], 1)
        self.assertEqual(summary["financial_kpis"]["total_outstanding"], Decimal("10500.00"))

    def test_payment_currency_must_match_booking_currency(self):
        from fastapi import HTTPException
        from app.routers.payments import PaymentCreate, create_payment

        with self.assertRaises(HTTPException) as error:
            create_payment(PaymentCreate(
                booking_id=self.booking_id,
                amount=Decimal("10"),
                currency="USD",
                method="Bank transfer",
                status="paid",
            ))
        self.assertEqual(error.exception.status_code, 422)
        with self.connection_factory() as conn:
            count = conn.execute(
                "SELECT COUNT(*) FROM payments WHERE booking_id = %s", (self.booking_id,)
            ).fetchone()[0]
        self.assertEqual(count, 0)

    def test_full_booking_detail_returns_financial_summary_and_payment_metadata(self):
        from app.routers import bookings

        with self.connection_factory() as conn:
            conn.execute(
                "UPDATE bookings SET deposit_amount = 2000.00 WHERE id = %s", (self.booking_id,)
            )
            conn.execute(
                "INSERT INTO payments (booking_id, amount, currency, method, status, paid_at, due_at, notes) "
                "VALUES (%s, 2000.00, 'THB', 'Bank transfer', 'paid', now(), now() + interval '15 days', 'Deposit receipt'), "
                "(%s, 1000.00, 'USD', 'Bank transfer', 'paid', now(), NULL, 'Currency mismatch')",
                (self.booking_id, self.booking_id),
            )
            conn.commit()

        result = bookings.get_booking_full_detail(self.booking_code)
        summary = result["payment_summary"]
        self.assertEqual(result["booking"]["status"], "Inquiry")
        self.assertEqual(Decimal(str(summary["total_amount"])), Decimal("10500.00"))
        self.assertEqual(Decimal(str(summary["deposit_amount"])), Decimal("2000.00"))
        self.assertEqual(Decimal(str(summary["paid_amount"])), Decimal("2000.00"))
        self.assertEqual(Decimal(str(summary["balance_due"])), Decimal("8500.00"))
        self.assertEqual(summary["booking_financial_status"], "depositpaid")
        deposit_payment = next(item for item in result["payments"] if item["currency"] == "THB")
        self.assertEqual(deposit_payment["notes"], "Deposit receipt")
        self.assertIsNotNone(deposit_payment["due_at"])
        mismatch = next(item for item in result["payments"] if item["currency"] == "USD")
        self.assertFalse(mismatch["currency_matches_booking"])
        self.assertEqual(mismatch["financial_error"], "currency_mismatch")

    def test_v1_financial_response_models_accept_existing_route_payloads(self):
        from app.response_models import (
            BookingFullDetailResponse,
            BookingListResponse,
            DashboardSummaryResponse,
            PaymentListResponse,
            PaymentsSummaryResponse,
        )
        from app.routers import bookings, dashboard, payments

        DashboardSummaryResponse.model_validate(dashboard.dashboard_summary())
        PaymentListResponse.model_validate(payments.list_payments())
        PaymentsSummaryResponse.model_validate(payments.payments_summary())
        BookingListResponse.model_validate(bookings.list_bookings())
        full_detail = bookings.get_booking_full_detail(self.booking_code)
        validated = BookingFullDetailResponse.model_validate(full_detail)
        self.assertEqual(validated.payment_summary.booking_financial_status, "unpaid")
        self.assertEqual(
            validated.model_dump(exclude_unset=True)["booking"]["status"],
            full_detail["booking"]["status"],
        )

    def test_invalid_payment_amount_and_field_lengths_do_not_insert(self):
        payload = {
            "booking_id": str(self.booking_id),
            "amount": "-10.00",
            "currency": "THB",
            "method": "Thai QR",
            "status": "Pending",
        }
        from pydantic import ValidationError
        from app.routers.payments import PaymentCreate

        with self.assertRaises(ValidationError):
            PaymentCreate(**payload)
        payload["amount"] = "10.00"
        payload["status"] = "refunded"
        with self.assertRaises(ValidationError):
            PaymentCreate(**payload)
        payload["method"] = "x" * 41
        with self.assertRaises(ValidationError):
            PaymentCreate(**payload)
        payload["method"] = "Thai QR"
        payload["status"] = "x" * 41
        with self.assertRaises(ValidationError):
            PaymentCreate(**payload)
        with self.connection_factory() as conn:
            count = conn.execute(
                "SELECT COUNT(*) FROM payments WHERE booking_id = %s", (self.booking_id,)
            ).fetchone()[0]
        self.assertEqual(count, 0)

    def test_invoice_detail_returns_valid_header_without_nonexistent_items_table(self):
        invoice_no = f"INV-{uuid4().hex[:10]}"
        with self.connection_factory() as conn:
            conn.execute(
                "INSERT INTO invoices (booking_id, invoice_no, invoice_type, amount, status) "
                "VALUES (%s, %s, 'final', %s, 'issued')",
                (self.booking_id, invoice_no, Decimal("10500.00")),
            )
            conn.commit()

        from app.routers import invoices
        result = invoices.get_invoice(invoice_no)
        self.assertEqual(result["invoice"]["invoice_no"], invoice_no)
        self.assertEqual(result["invoice"]["booking_code"], self.booking_code)
        self.assertEqual(result["items"], [])


if __name__ == "__main__":
    unittest.main()
