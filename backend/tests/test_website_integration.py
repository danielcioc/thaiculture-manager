import unittest
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import patch

from fastapi import HTTPException

from app.routers import website
from app.routers.website import WebsiteBookingRequest, WebsiteCustomer, WebsitePricingRequest


class WebsiteIntegrationContractTests(unittest.TestCase):
    def test_feature_is_disabled_by_default(self):
        with patch.object(website.settings, "website_integration_enabled", False):
            with self.assertRaises(HTTPException) as error:
                website._ensure_enabled()
        self.assertEqual(error.exception.status_code, 404)

    def test_slug_maps_from_website_url(self):
        self.assertEqual(website._slug("https://example.test/en/hua-hin-temple-tour.html"), "hua-hin-temple-tour.html")
        self.assertEqual(website._slug("hua-hin-temple-tour.html"), "hua-hin-temple-tour.html")

    def test_money_rounding_uses_half_up(self):
        self.assertEqual(website._money(Decimal("1.005")), Decimal("1.01"))

    def test_equivalent_booking_payloads_have_same_hash(self):
        from uuid import UUID
        request = WebsiteBookingRequest(
            quote_id=UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"),
            date=date.today() + timedelta(days=30), adults=3, children=2,
            currency="THB", customer=WebsiteCustomer(name=" Test Guest ", email="GUEST@example.com", phone=" +100 "),
            notes="  window seats  ",
        )
        normalized = website._normalized_booking_payload(request)
        second = dict(reversed(list(normalized.items())))
        self.assertEqual(website._canonical_payload_hash(normalized), website._canonical_payload_hash(second))
        first = normalized
        second["adults"] = 4
        self.assertNotEqual(website._canonical_payload_hash(first), website._canonical_payload_hash(second))

    def test_phone_is_optional_and_legacy_hash_shape_is_preserved(self):
        from uuid import UUID
        common = dict(
            quote_id=UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"),
            date=date.today() + timedelta(days=30), adults=1, currency="THB",
            customer=WebsiteCustomer(name="Guest", email="guest@example.com"),
        )
        without_phone = WebsiteBookingRequest(**common)
        legacy = WebsiteBookingRequest(
            **{**common, "customer": WebsiteCustomer(name="Guest", email="guest@example.com", phone=" +100 ")}
        )
        customer_schema = WebsiteCustomer.model_json_schema()
        phone_schema = customer_schema["properties"]["phone"]
        new_payload = website._normalized_booking_payload(without_phone)
        legacy_payload = website._normalized_booking_payload(legacy)
        self.assertTrue(phone_schema["deprecated"])
        self.assertNotIn("phone", customer_schema.get("required", []))
        self.assertNotIn("phone", new_payload["customer"])
        self.assertEqual(legacy_payload["customer"]["phone"], "+100")
        self.assertNotEqual(
            website._canonical_payload_hash(new_payload),
            website._canonical_payload_hash(legacy_payload),
        )

    def test_new_website_customer_is_created_without_persisting_legacy_phone(self):
        from uuid import UUID

        quote_id = UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")
        tour_id = UUID("cccccccc-cccc-4ccc-8ccc-cccccccccccc")
        booking_id = UUID("dddddddd-dddd-4ddd-8ddd-dddddddddddd")
        customer_id = UUID("eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee")
        quote_row = (
            quote_id, tour_id, "TEST", "Test Tour", "test-tour",
            date.today() + timedelta(days=30), 1, 0, [], "THB",
            Decimal("100.00"), Decimal("30.00"), Decimal("90.00"),
            "test-rule", "minimum-margin-30-v1", {},
            website.datetime.now(website.timezone.utc) + timedelta(days=1), None,
        )

        class Cursor:
            def __init__(self):
                self.rows = [
                    (UUID("bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"),),
                    quote_row,
                    None,
                    (customer_id,),
                    (booking_id, "TCT-WEB-TEST", "Inquiry"),
                    (UUID("ffffffff-ffff-4fff-8fff-ffffffffffff"),),
                ]
                self.executed = []

            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            def execute(self, query, params=None):
                self.executed.append((query, params))

            def fetchone(self):
                return self.rows.pop(0)

        cursor = Cursor()

        class Connection:
            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            def cursor(self):
                return cursor

        for phone in (None, "legacy-only"):
            with self.subTest(phone_supplied=phone is not None):
                cursor = Cursor()
                request = WebsiteBookingRequest(
                    quote_id=quote_id, date=quote_row[5], adults=1, currency="THB",
                    customer=WebsiteCustomer(name="Guest", email="guest@example.com", phone=phone),
                )
                with patch.object(website.settings, "website_integration_enabled", True), patch.object(
                    website, "_website_connection", return_value=Connection()
                ):
                    response = website.create_website_booking(
                        request, UUID("bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb")
                    )

                customer_insert = next(
                    (query, params) for query, params in cursor.executed if "INSERT INTO customers" in query
                )
                self.assertNotIn("phone", customer_insert[0])
                self.assertEqual(customer_insert[1], ("Guest", "guest@example.com"))
                self.assertEqual(response["status"], "Inquiry")
                idempotency_insert = next(
                    (query, params) for query, params in cursor.executed
                    if "INSERT INTO website_booking_idempotency" in query
                )
                self.assertIn("created_at <= %s", idempotency_insert[0])
                self.assertIn("created_at = now()", idempotency_insert[0])
                self.assertIn("response_payload = NULL", idempotency_insert[0])
                self.assertEqual(idempotency_insert[1][0], UUID("bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"))
                cutoff = idempotency_insert[1][2]
                self.assertIsInstance(cutoff, datetime)
                self.assertLessEqual(cutoff, datetime.now(timezone.utc) - website.WEBSITE_BOOKING_IDEMPOTENCY_TTL)
                self.assertGreater(cutoff, datetime.now(timezone.utc) - website.WEBSITE_BOOKING_IDEMPOTENCY_TTL - timedelta(seconds=2))

    def test_manager_policy_calculates_private_group_quote(self):
        request = WebsitePricingRequest(
            website_tour_id="hua-hin-temple-tour.html",
            date=date.today() + timedelta(days=30),
            adults=3,
            children=2,
            extras=[],
            currency="THB",
        )
        conditions = {
            "currency": "THB", "min_guests": 5, "max_guests": 5,
            "group_size_basis": "per_booking",
        }
        calculation = {
            "vat_rate": 0.07, "direct_cost_total": 5000,
            "selling_price_gross": 8900, "pricing_use": "approved_for_quote",
        }
        total, total_cost, minimum_gross, breakdown = website._calculate_public_price(
            conditions, calculation, request,
        )
        self.assertEqual(total, Decimal("8900.00"))
        self.assertEqual(total_cost, Decimal("5000.00"))
        self.assertEqual(minimum_gross, Decimal("7642.86"))
        self.assertEqual(breakdown["pricing_policy_version"], "minimum-margin-30-v1")

    def test_reference_only_rule_is_rejected(self):
        request = WebsitePricingRequest(
            website_tour_id="hua-hin-temple-tour.html",
            date=date.today() + timedelta(days=30), adults=3, children=2, currency="THB",
        )
        with self.assertRaises(HTTPException) as error:
            website._calculate_public_price(
                {"currency": "THB", "min_guests": 5, "max_guests": 5, "group_size_basis": "per_booking"},
                {"vat_rate": 0.07, "direct_cost_total": 5000, "selling_price_gross": 8900, "pricing_use": "reference_only"},
                request,
            )
        self.assertEqual(error.exception.status_code, 422)

    def test_extras_currency_guest_count_and_missing_vat_are_rejected(self):
        base = dict(
            website_tour_id="hua-hin-temple-tour.html",
            date=date.today() + timedelta(days=30), adults=3, children=2, currency="THB",
        )
        with self.assertRaises(ValueError):
            WebsitePricingRequest(**base, extras=["extra-stop"])
        with self.assertRaises(HTTPException) as error:
            website._calculate_public_price(
                {"currency": "THB", "min_guests": 5, "max_guests": 5, "group_size_basis": "per_booking"},
                {"selling_price_gross": 8900, "direct_cost_total": 5000},
                WebsitePricingRequest(**base),
            )
        self.assertEqual(error.exception.status_code, 422)


if __name__ == "__main__":
    unittest.main()
