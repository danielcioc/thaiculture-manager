import unittest
from datetime import date, timedelta
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
