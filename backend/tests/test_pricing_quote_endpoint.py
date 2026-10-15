import unittest
from datetime import date
from decimal import Decimal
import sys
from unittest.mock import patch

from fastapi import HTTPException

# test_importer installs a lightweight psycopg stub for its own import. Restore
# the installed driver package before importing the API router under discovery.
if not hasattr(sys.modules.get("psycopg"), "__path__"):
    sys.modules.pop("psycopg", None)

from app.routers import pricing
from app.routers.pricing import GeneratePricingQuoteRequest


QUOTE_COLUMNS = [
    ("booking_id",),
    ("booking_code",),
    ("tour_date",),
    ("total_cost",),
    ("recommended_price",),
    ("minimum_price",),
    ("final_price",),
    ("breakdown",),
    ("valid_until",),
    ("tour_id",),
    ("tour_code",),
    ("tour_name",),
]


class FakeCursor:
    def __init__(self, booking_status="Inquiry", calculation=None):
        self.booking_status = booking_status
        self.calculation = calculation or {
            "vat_rate": 0.07,
            "direct_cost_total": 7350,
            "direct_cost_is_known": True,
            "selling_price_gross": 10500,
            "pricing_use": "approved_for_quote",
            "cost_status": "available",
        }
        self.description = None
        self.row = None
        self.insert_values = None
        self.queries = []

    def execute(self, query, params=None):
        self.queries.append((query, params))
        if "FROM bookings" in query and "FOR UPDATE" in query:
            self.row = ("booking-uuid", self.booking_status, "tour-uuid")
        elif "FROM pricing_rules" in query:
            self.row = ("active-rule-v1", {"confidence_status": "confirmed"}, self.calculation)
        elif "INSERT INTO pricing_quotes" in query:
            self.insert_values = params
        elif "FROM pricing_quotes pq" in query:
            values = self.insert_values
            breakdown = values[5].obj
            self.description = QUOTE_COLUMNS
            self.row = (
                "booking-uuid",
                "BOOKING-1",
                date(2026, 11, 1),
                values[1],
                values[2],
                values[3],
                values[4],
                breakdown,
                None,
                "tour-uuid",
                "TOUR-1",
                "Tour One",
            )

    def fetchone(self):
        return self.row


class FakeConnection:
    def __init__(self, cursor):
        self.fake_cursor = cursor
        self.exit_exception = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.exit_exception = exc_type

    def cursor(self):
        return FakeCursorContext(self.fake_cursor)


class FakeCursorContext:
    def __init__(self, cursor):
        self.cursor = cursor

    def __enter__(self):
        return self.cursor

    def __exit__(self, exc_type, exc_value, traceback):
        return False


class PricingQuoteEndpointTests(unittest.TestCase):
    def test_explicit_generation_inserts_new_gross_price_quote(self):
        cursor = FakeCursor()
        connection = FakeConnection(cursor)
        with patch.object(pricing, "get_connection", return_value=connection):
            quote = pricing.generate_pricing_quote("BOOKING-1", GeneratePricingQuoteRequest())

        self.assertEqual(cursor.insert_values[1], Decimal("7350.00"))
        self.assertEqual(cursor.insert_values[2], Decimal("11235.00"))
        self.assertEqual(cursor.insert_values[3], Decimal("11235.00"))
        self.assertIsNone(cursor.insert_values[4])
        self.assertEqual(quote.minimum_price_net, 10500.0)
        self.assertEqual(quote.margin_verdict, "meets_margin")
        self.assertTrue(any("FOR UPDATE" in query for query, _ in cursor.queries))

    def test_all_allowed_booking_statuses_generate_quotes(self):
        for status in ("Inquiry", "Offer Prepared", "Awaiting Confirmation"):
            with self.subTest(status=status):
                cursor = FakeCursor(booking_status=status)
                connection = FakeConnection(cursor)
                with patch.object(pricing, "get_connection", return_value=connection):
                    quote = pricing.generate_pricing_quote(
                        "BOOKING-1", GeneratePricingQuoteRequest()
                    )
                self.assertEqual(quote.booking_code, "BOOKING-1")
                self.assertTrue(
                    any("INSERT INTO pricing_quotes" in query for query, _ in cursor.queries)
                )

    def test_eligible_status_normalization_trims_and_ignores_case(self):
        for status in (" inquiry ", "OFFER PREPARED", "  Awaiting   Confirmation  "):
            with self.subTest(status=status):
                cursor = FakeCursor(booking_status=status)
                connection = FakeConnection(cursor)
                with patch.object(pricing, "get_connection", return_value=connection):
                    pricing.generate_pricing_quote("BOOKING-1", GeneratePricingQuoteRequest())
                self.assertTrue(
                    any("INSERT INTO pricing_quotes" in query for query, _ in cursor.queries)
                )

    def test_ineligible_and_unknown_statuses_are_refused_before_rule_or_insert(self):
        for status in (
            "Confirmed",
            "Cancelled",
            "Deposit Requested",
            "Unexpected Status",
            None,
        ):
            with self.subTest(status=status):
                cursor = FakeCursor(booking_status=status)
                connection = FakeConnection(cursor)
                with patch.object(pricing, "get_connection", return_value=connection):
                    with self.assertRaises(HTTPException) as error:
                        pricing.generate_pricing_quote(
                            "BOOKING-1", GeneratePricingQuoteRequest()
                        )

                self.assertEqual(error.exception.status_code, 409)
                self.assertIn(
                    "Inquiry, Offer Prepared, or Awaiting Confirmation",
                    error.exception.detail,
                )
                self.assertFalse(
                    any("FROM pricing_rules" in query for query, _ in cursor.queries)
                )
                self.assertFalse(
                    any("INSERT INTO pricing_quotes" in query for query, _ in cursor.queries)
                )

    def test_missing_vat_rejects_without_insert(self):
        calculation = {"direct_cost_total": 7350, "selling_price_gross": 10500}
        cursor = FakeCursor(calculation=calculation)
        connection = FakeConnection(cursor)
        with patch.object(pricing, "get_connection", return_value=connection):
            with self.assertRaises(HTTPException) as error:
                pricing.generate_pricing_quote("BOOKING-1", GeneratePricingQuoteRequest())

        self.assertEqual(error.exception.status_code, 422)
        self.assertFalse(any("INSERT INTO pricing_quotes" in query for query, _ in cursor.queries))


if __name__ == "__main__":
    unittest.main()
