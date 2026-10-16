import unittest
from unittest.mock import patch

from app.routers import bookings


LIST_COLUMNS = [
    "id", "booking_code", "status", "source", "customer_name", "customer_email",
    "customer_country", "tour_id", "tour_code", "tour_name", "tour_category",
    "tour_duration_hours", "pickup_location_name", "pickup_location_address",
    "pickup_google_maps_url", "dropoff_location_name", "dropoff_location_address",
    "dropoff_google_maps_url", "tour_date", "pickup_time", "adults", "children",
    "infants", "total_guests", "guide_language", "selling_price", "deposit_amount", "currency",
    "imported_raw_tour_name", "mapping_status", "needs_manual_review", "created_at",
    "paid_amount", "pending_amount", "requested_amount", "has_overdue", "assignment_guide_cost",
    "assignment_driver_cost", "assignment_other_cost", "assignment_total_cost",
    "quote_breakdown",
]

DETAIL_COLUMNS = [
    "id", "booking_code", "status", "source", "customer_id", "customer_name",
    "customer_email", "customer_phone", "customer_whatsapp", "customer_country",
    "customer_nationality", "customer_preferred_language", "tour_id", "tour_code",
    "tour_name", "tour_category", "tour_duration_hours", "tour_website_url",
    "pickup_location_id", "pickup_location_name", "pickup_location_address",
    "pickup_google_maps_url", "dropoff_location_id", "dropoff_location_name",
    "dropoff_location_address", "dropoff_google_maps_url", "tour_date", "pickup_time",
    "adults", "children", "infants", "total_guests", "guide_language", "selling_price",
    "currency", "imported_raw_tour_name", "mapping_status", "needs_manual_review",
    "created_at", "deposit_amount",
]


class ReadOnlyBookingCursor:
    def __init__(self, booking, mode):
        self.booking = booking
        self.mode = mode
        self.query = ""
        self.description = []
        self.columns = []
        self.result = None

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def execute(self, query, _params=None):
        self.query = query
        if self.mode == "list":
            self.columns = LIST_COLUMNS
            self.result = self.booking
        elif "FROM bookings b" in query and "LEFT JOIN payments" not in query:
            self.columns = DETAIL_COLUMNS
            self.result = self.booking
        elif "FROM payments" in query and "ORDER BY paid_at" in query:
            self.columns = ["id", "amount", "currency", "method", "status", "paid_at", "due_at", "reference", "notes"]
            self.result = []
        elif "FROM payments" in query:
            self.columns = ["paid_amount", "pending_amount", "requested_amount", "has_overdue"]
            self.result = (0, 0, 0, False)
        elif "LEFT JOIN payments" in query:
            self.columns = ["paid_amount", "pending_amount", "requested_amount", "has_overdue"]
            self.result = (0, 0, 0, False)
        elif "FROM assignments a" in query:
            self.columns = [
                "id", "assignment_type", "guide_name", "guide_languages", "guide_phone",
                "guide_line_id", "driver_name", "driver_phone", "driver_line_id", "cost",
                "status", "notes",
            ]
            self.result = []
        elif "FROM assignments" in query:
            self.columns = ["guide_cost", "driver_cost", "other_cost", "total_cost"]
            self.result = (0, 0, 0, 0)
        elif "FROM pricing_quotes" in query:
            self.columns = ["breakdown"]
            self.result = None
        else:
            raise AssertionError(f"Unexpected read-only query: {query}")
        self.description = [(column,) for column in self.columns]

    def fetchall(self):
        if self.mode == "list":
            return [tuple(self.result.get(column) for column in self.columns)]
        return self.result

    def fetchone(self):
        if self.mode == "list":
            return None
        if isinstance(self.result, dict):
            return tuple(self.result.get(column) for column in self.columns)
        return self.result


class ReadOnlyBookingConnection:
    def __init__(self, booking, mode):
        self.cursor_instance = ReadOnlyBookingCursor(booking, mode)

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def cursor(self):
        return self.cursor_instance


def booking_fixture(
    *, status, tour_id, tour_name, raw_label, mapping_status, needs_manual_review
):
    return {
        "id": "booking-uuid",
        "booking_code": "TCT-REVIEW-TEST-001",
        "status": status,
        "source": "test",
        "customer_id": "customer-uuid",
        "customer_name": "Review Test Customer",
        "customer_email": None,
        "customer_phone": None,
        "customer_whatsapp": None,
        "customer_country": None,
        "customer_nationality": None,
        "customer_preferred_language": "EN",
        "tour_id": tour_id,
        "tour_code": "TST-001" if tour_id else None,
        "tour_name": tour_name,
        "tour_category": None,
        "tour_duration_hours": None,
        "tour_website_url": None,
        "pickup_location_id": None,
        "pickup_location_name": None,
        "pickup_location_address": None,
        "pickup_google_maps_url": None,
        "dropoff_location_id": None,
        "dropoff_location_name": None,
        "dropoff_location_address": None,
        "dropoff_google_maps_url": None,
        "tour_date": None,
        "pickup_time": None,
        "adults": 1,
        "children": 0,
        "infants": 0,
        "total_guests": 1,
        "guide_language": "EN",
        "selling_price": 1000,
        "deposit_amount": None,
        "currency": "THB",
        "imported_raw_tour_name": raw_label,
        "mapping_status": mapping_status,
        "needs_manual_review": needs_manual_review,
        "created_at": None,
        "paid_amount": 0,
        "pending_amount": 0,
        "requested_amount": 0,
        "has_overdue": False,
        "assignment_guide_cost": 0,
        "assignment_driver_cost": 0,
        "assignment_other_cost": 0,
        "assignment_total_cost": 0,
        "quote_breakdown": None,
    }


class BookingReviewVisibilityTests(unittest.TestCase):
    CASES = (
        booking_fixture(
            status="Confirmed",
            tour_id="tour-uuid",
            tour_name="Canonical Tour",
            raw_label="Approved source label",
            mapping_status="confirmed",
            needs_manual_review=False,
        ),
        booking_fixture(
            status="Confirmed",
            tour_id=None,
            tour_name=None,
            raw_label="Probable source label",
            mapping_status="probable_manual_review",
            needs_manual_review=True,
        ),
        booking_fixture(
            status="Inquiry",
            tour_id=None,
            tour_name=None,
            raw_label="Unknown source label",
            mapping_status="unmapped",
            needs_manual_review=True,
        ),
        booking_fixture(
            status="Awaiting Confirmation",
            tour_id="existing-tour-uuid",
            tour_name="Existing Tour",
            raw_label=None,
            mapping_status=None,
            needs_manual_review=None,
        ),
    )

    def test_booking_list_and_detail_expose_read_only_review_metadata(self):
        for source in self.CASES:
            with self.subTest(mapping_status=source["mapping_status"]):
                list_connection = ReadOnlyBookingConnection(source, "list")
                with patch.object(bookings, "get_connection", return_value=list_connection):
                    listed = bookings.list_bookings()["items"][0]

                detail_connection = ReadOnlyBookingConnection(source, "full")
                with patch.object(bookings, "get_connection", return_value=detail_connection):
                    detailed = bookings.get_booking_full_detail(source["booking_code"])["booking"]

                for response in (listed, detailed):
                    self.assertEqual(response["booking_code"], source["booking_code"])
                    self.assertEqual(response["customer_name"], source["customer_name"])
                    self.assertEqual(response["status"], source["status"])
                    self.assertEqual(response["tour_id"], source["tour_id"])
                    self.assertEqual(response["tour_name"], source["tour_name"])
                    self.assertEqual(response["imported_raw_tour_name"], source["imported_raw_tour_name"])
                    self.assertEqual(response["mapping_status"], source["mapping_status"])
                    self.assertEqual(response["needs_manual_review"], source["needs_manual_review"])

                self.assertIn("b.imported_raw_tour_name", list_connection.cursor_instance.query)
                self.assertIn("b.mapping_status", list_connection.cursor_instance.query)
                self.assertIn("b.needs_manual_review", list_connection.cursor_instance.query)
                self.assertIn("t.id AS tour_id", list_connection.cursor_instance.query)


if __name__ == "__main__":
    unittest.main()
