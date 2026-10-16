import unittest

from app.main import app


class FinancialAndReviewOpenApiContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.schema = app.openapi()

    def _response_schema(self, path, method="get"):
        schema = (
            self.schema["paths"][path][method]["responses"]["200"]
            ["content"]["application/json"]["schema"]
        )
        if "$ref" in schema:
            name = schema["$ref"].rsplit("/", 1)[-1]
            return self.schema["components"]["schemas"][name]
        return schema

    def _properties(self, schema):
        return schema.get("properties", {})

    def test_financial_routes_document_response_fields(self):
        dashboard = self._properties(self._response_schema("/dashboard/summary"))
        self.assertIn("financial_kpis", dashboard)
        dashboard_ref = dashboard["financial_kpis"]["$ref"].rsplit("/", 1)[-1]
        kpis = self.schema["components"]["schemas"][dashboard_ref]["properties"]
        self.assertTrue({"unpaid", "depositrequested", "depositpaid", "partiallypaid", "paid", "overdue", "total_outstanding"} <= set(kpis))

        payments_list = self._properties(self._response_schema("/payments"))
        self.assertTrue({"count", "filters", "items"} <= set(payments_list))
        payments_summary = self._properties(self._response_schema("/payments/summary"))
        self.assertIn("currencies", payments_summary)

        booking_list = self._properties(self._response_schema("/bookings"))
        self.assertIn("items", booking_list)
        item_ref = booking_list["items"]["items"]["$ref"].rsplit("/", 1)[-1]
        item_fields = self.schema["components"]["schemas"][item_ref]["properties"]
        self.assertTrue({"booking_financial_status", "paid_amount", "pending_amount", "balance_due"} <= set(item_fields))

        full = self._properties(self._response_schema("/bookings/{booking_code}/full"))
        self.assertIn("payment_summary", full)
        summary_ref = full["payment_summary"]["$ref"].rsplit("/", 1)[-1]
        summary_fields = self.schema["components"]["schemas"][summary_ref]["properties"]
        self.assertTrue({"total_amount", "deposit_amount", "paid_amount", "pending_amount", "balance_due", "booking_financial_status"} <= set(summary_fields))

    def test_review_queue_and_decision_paths_and_error_codes_are_documented(self):
        queue = self.schema["paths"]["/bookings"]["get"]
        query_params = {item["name"] for item in queue.get("parameters", [])}
        self.assertIn("needs_manual_review", query_params)

        decision = self.schema["paths"]["/bookings/{booking_code}/import-review/decision"]["post"]
        self.assertTrue({"200", "400", "401", "403", "404", "409", "422"} <= set(decision["responses"]))
        self.assertIn("security", decision)

        for path, method, expected in (
            ("/payments", "get", {"200", "422"}),
            ("/payments", "post", {"200", "400", "404", "422"}),
            ("/bookings/{booking_code}/full", "get", {"200", "404"}),
        ):
            self.assertTrue(expected <= set(self.schema["paths"][path][method]["responses"]))


if __name__ == "__main__":
    unittest.main()
