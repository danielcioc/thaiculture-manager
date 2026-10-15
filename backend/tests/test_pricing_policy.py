import unittest
from decimal import Decimal

from app.pricing_policy import (
    POLICY_VERSION,
    PricingPolicyInputError,
    calculate_quote,
)


class PricingPolicyTests(unittest.TestCase):
    def test_minimum_and_recommended_prices_keep_vat_separate(self):
        quote = calculate_quote(
            vat_rate="0.07",
            direct_cost="7350.00",
            rule_price_gross="10500.00",
        )

        self.assertEqual(POLICY_VERSION, "minimum-margin-30-v1")
        self.assertEqual(quote.minimum_price_net, Decimal("10500.00"))
        self.assertEqual(quote.minimum_price_gross, Decimal("11235.00"))
        self.assertEqual(quote.recommended_price_net, Decimal("10500.00"))
        self.assertEqual(quote.recommended_price_gross, Decimal("11235.00"))
        self.assertIsNone(quote.final_price_gross)
        self.assertEqual(quote.margin_verdict, "meets_margin")
        self.assertEqual(quote.approval_status, "not_required")

    def test_existing_rule_gross_price_is_preserved_when_above_minimum(self):
        quote = calculate_quote(
            vat_rate="0.07",
            direct_cost="7000",
            rule_price_gross="12000",
        )

        self.assertEqual(quote.minimum_price_net, Decimal("10000.00"))
        self.assertEqual(quote.minimum_price_gross, Decimal("10700.00"))
        self.assertEqual(quote.recommended_price_gross, Decimal("12000.00"))
        self.assertEqual(quote.recommended_price_net, Decimal("11214.95"))

    def test_below_margin_chosen_final_price_requires_manual_override(self):
        quote = calculate_quote(
            vat_rate="0.07",
            direct_cost="7350",
            rule_price_gross="10500",
            final_price_gross="10700",
        )

        self.assertEqual(quote.final_price_gross, Decimal("10700.00"))
        self.assertEqual(quote.final_price_net, Decimal("10000.00"))
        self.assertEqual(quote.margin_verdict, "below_margin")
        self.assertEqual(quote.approval_status, "manual_override_required")

    def test_unknown_direct_cost_has_explicit_verdict_and_no_minimum(self):
        quote = calculate_quote(
            vat_rate="0.07",
            direct_cost=None,
            rule_price_gross="10500",
        )

        self.assertFalse(quote.direct_cost_is_known)
        self.assertIsNone(quote.minimum_price_net)
        self.assertEqual(quote.margin_verdict, "direct_cost_unknown")
        self.assertEqual(quote.approval_status, "not_required")

    def test_invalid_vat_is_rejected(self):
        for vat_rate in (None, "NaN", "-0.01", "1.01"):
            with self.subTest(vat_rate=vat_rate):
                with self.assertRaises(PricingPolicyInputError):
                    calculate_quote(
                        vat_rate=vat_rate,
                        direct_cost="100",
                        rule_price_gross="150",
                    )


if __name__ == "__main__":
    unittest.main()
