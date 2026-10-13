import unittest

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

    def test_catalina_ayutthaya_mapping_needs_review(self):
        self.assertEqual(
            resolve_tour_mapping("Ayutthaya UNESCO Full Day Tour (grup)"),
            ("Ayutthaya: 5 Essential Sights", "probable_manual_review", True),
        )

    def test_unknown_tour_is_not_fuzzy_matched(self):
        self.assertEqual(
            resolve_tour_mapping("Unknown custom tour"),
            (None, "unmapped", True),
        )

    def test_unknown_status_defaults_to_inquiry(self):
        self.assertEqual(booking_status("Unexpected legacy status"), "Inquiry")


if __name__ == "__main__":
    unittest.main()
