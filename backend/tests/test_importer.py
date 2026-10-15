import sys
import types
import unittest
from unittest.mock import MagicMock, call, mock_open, patch

# Stub psycopg so importing helpers never requires a DB dependency or connection.
sys.modules.setdefault("psycopg", types.SimpleNamespace(connect=None))

import import_thaiculture_data as importer
from import_rules import booking_status, resolve_tour_mapping


class ImportRulesTests(unittest.TestCase):
    def test_marina_is_inquiry_and_reviewable(self):
        self.assertEqual(booking_status("Cerere (fără răspuns)"), "Inquiry")
        self.assertEqual(
            resolve_tour_mapping("Whale Tour (nespecificat)"),
            ("Whale Safari", "probable_manual_review", True),
        )

    def test_approved_mapping_is_confirmed(self):
        self.assertEqual(
            resolve_tour_mapping("Evening Ayutthaya UNESCO Temples Tour (privat)"),
            ("Evening in Ayutthaya", "confirmed", False),
        )

    def test_unknown_tour_is_unmapped(self):
        self.assertEqual(
            resolve_tour_mapping("Unknown custom tour"),
            (None, "unmapped", True),
        )


class ImporterSafetyTests(unittest.TestCase):
    def test_import_booking_uses_canonical_mapping_and_only_links_confirmed_tours(self):
        cases = (
            (
                "Evening Ayutthaya UNESCO Temples Tour (privat)",
                ("Evening in Ayutthaya", "confirmed", False),
                "tour-confirmed",
                "Evening in Ayutthaya",
            ),
            (
                " Whale Tour (nespecificat) ",
                ("Whale Safari", "probable_manual_review", True),
                None,
                None,
            ),
            (
                "Unknown custom tour",
                (None, "unmapped", True),
                None,
                None,
            ),
        )

        for raw_tour_name, expected_mapping, expected_tour_id, expected_lookup in cases:
            with self.subTest(mapping_status=expected_mapping[1]):
                row = {
                    "customer_name": "Importer Test",
                    "email": "importer@example.test",
                    "language": "EN",
                    "notes": "test",
                    "hotel_location": "",
                    "tour": raw_tour_name,
                    "tour_date": "2026-11-01",
                    "people": "2",
                    "status": "Confirmat / Efectuat",
                    "price_thb": "1000",
                    "booking_code": "TCT-IMP-TEST-0001",
                }
                cursor = MagicMock()
                cursor.fetchone.return_value = (expected_tour_id, "Canonical tour", "TEST")

                with patch("pathlib.Path.open", mock_open(read_data="header\nrow\n")), patch.object(
                    importer.csv, "DictReader", return_value=[row]
                ), patch.object(
                    importer, "get_or_create_customer", return_value="customer-1"
                ), patch.object(
                    importer, "get_or_create_location", return_value=None
                ), patch.object(
                    importer, "existing_booking", return_value=None
                ), patch.object(
                    importer,
                    "resolve_tour_mapping",
                    wraps=resolve_tour_mapping,
                ) as resolver:
                    importer.import_bookings(cursor)

                resolver.assert_called_once_with(raw_tour_name)
                booking_insert = next(
                    call for call in cursor.execute.call_args_list
                    if "INSERT INTO bookings" in call.args[0]
                )
                inserted_values = booking_insert.args[1]
                self.assertEqual(inserted_values[5], expected_tour_id)
                self.assertEqual(inserted_values[14], raw_tour_name)
                self.assertEqual(inserted_values[15:17], expected_mapping[1:])

                tour_lookups = [
                    call for call in cursor.execute.call_args_list
                    if "FROM tours" in call.args[0]
                ]
                if expected_lookup is None:
                    self.assertEqual(tour_lookups, [])
                else:
                    self.assertEqual(len(tour_lookups), 1)
                    self.assertEqual(tour_lookups[0].args[1], (expected_lookup,))

    @patch.object(importer, "get_or_create_customer", return_value="customer-1")
    @patch.object(importer, "get_or_create_location", return_value=None)
    @patch.object(
        importer,
        "existing_booking",
        return_value=("booking-existing", "TCT-IMP-2026-0002"),
    )
    def test_existing_booking_is_not_reinserted(
        self, existing_booking, get_location, get_customer
    ):
        row = {
            "customer_name": "Marina",
            "email": "marina@example.test",
            "language": "EN",
            "notes": "Inquiry",
            "hotel_location": "",
            "tour": "Whale Tour (nespecificat)",
            "tour_date": "",
            "people": "4 adults + 1 copil (7 ani)",
            "status": "Cerere (fără răspuns)",
            "price_thb": "",
            "booking_code": "TCT-IMP-2026-0002",
        }
        cursor = MagicMock()
        fake_csv = "header\nrow\n"
        with patch("pathlib.Path.open", mock_open(read_data=fake_csv)), patch.object(
            importer.csv, "DictReader", return_value=[row]
        ):
            result = importer.import_bookings(cursor)
        self.assertEqual(
            result,
            [("booking-existing", "TCT-IMP-2026-0002", "existing")],
        )
        insert_calls = [
            c for c in cursor.execute.call_args_list
            if "INSERT INTO bookings" in c.args[0]
        ]
        self.assertEqual(insert_calls, [])

    def test_current_payment_import_inserts_row(self):
        csv_data = (
            "invoice_no,method,account_name,account_no,bank,swift,branch,status\n"
            "TCT-TH-2026-0206-001,Bank transfer,Pimnipa Buachum,6161212177,"
            "Bank of Ayudhya (Krungsri),AYUDTHBK,"
            "\"0616 Khao Ta Lo Soi Branch, Pattaya\",Pending confirmation\n"
        )
        cursor = MagicMock()
        booking_map = {
            "booking-1": {
                "booking_code": "TCT-IMP-2026-0006",
                "customer_name": "Catalina Popa",
            }
        }

        with patch("pathlib.Path.exists", return_value=True), patch(
            "pathlib.Path.open", mock_open(read_data=csv_data)
        ), patch.object(cursor, "fetchone", return_value=("booking-1",)):
            count = importer.import_payments(cursor, booking_map)

        self.assertEqual(count, 1)
        payment_inserts = [
            c for c in cursor.execute.call_args_list
            if "INSERT INTO payments" in c.args[0]
        ]
        self.assertEqual(len(payment_inserts), 1)


if __name__ == "__main__":
    unittest.main()
