import os
import unittest
from decimal import Decimal
from urllib.parse import urlparse
from uuid import uuid4
from unittest.mock import patch

from app.financials import booking_financial_summary


class BookingFinancialSummaryTests(unittest.TestCase):
    def test_confirmed_payment_aggregation_and_statuses(self):
        cases = [
            ("10500", "10500", "0", "paid", "10500"),
            ("10500", "1200", "0", "partiallypaid", "1200"),
            ("10500", "0", "1200", "depositrequested", "1200"),
            ("10500", "0", "0", "unpaid", "0"),
        ]
        for selling, paid, pending, expected_status, expected_requested in cases:
            with self.subTest(expected_status=expected_status):
                summary = booking_financial_summary(
                    Decimal(selling), Decimal(paid), Decimal(pending)
                )
                self.assertEqual(summary["booking_financial_status"], expected_status)
                self.assertEqual(summary["requested_amount"], Decimal(expected_requested))


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
        from app.routers import bookings, invoices, payments

        cls.psycopg = psycopg
        cls.schema = f"financial_test_{uuid4().hex[:12]}"

        with psycopg.connect(TEST_DATABASE_URL, autocommit=True) as conn:
            conn.execute(f'CREATE SCHEMA "{cls.schema}"')
            conn.execute(f'SET search_path TO "{cls.schema}"')
            conn.execute("""
                CREATE TABLE customers (
                    id uuid PRIMARY KEY,
                    display_name text,
                    email text
                );
                CREATE TABLE bookings (
                    id uuid PRIMARY KEY,
                    booking_code text UNIQUE NOT NULL,
                    selling_price numeric(12,2) NOT NULL,
                    currency char(3) NOT NULL DEFAULT 'THB',
                    customer_id uuid REFERENCES customers(id),
                    status text NOT NULL DEFAULT 'Inquiry',
                    source text
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
