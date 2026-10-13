STATUS_MAP = {
    "Confirmat / Efectuat": "Confirmed",
    "Facturat / Efectuat": "Confirmed",
    "Cerere (fără răspuns)": "Inquiry",
    "Refuzat (buget)": "Cancelled",
}

LANG_MAP = {"RO": "RO", "EN": "EN", "FR": "FR"}

TOUR_NAME_MAP = {
    "Evening Ayutthaya UNESCO Temples Tour (privat)": "Evening in Ayutthaya",
    "Whale Tour": "Whale Safari",
    "Whale Tour (nespecificat)": "Whale Safari",
    "Hua Hin Temple Tour – Cultural Day Trip": "Hua Hin Temple Tour",
    "Hua Hin – Bangkok Day Trip": "1-Day Trip – Hua Hin → Bangkok",
    "Kui Buri National Park – Elephant Watching": "Elephant Watching in Kui Buri National Park",
    "Classic Bangkok": "Classic Bangkok",
    "Mystic Bangkok": "Mystic Bangkok",
    "Uthai Thani / Sacred River": "Uthai Thani Sacred River & Hidden Heritage",
    "Ayutthaya 5 Highlights": "Ayutthaya: 5 Essential Sights",
    "Ayutthaya UNESCO Full Day Tour (grup)": "Ayutthaya: 5 Essential Sights",
    "Ayutthaya Tour (privat – GetYourGuide)": "Ayutthaya: 5 Essential Sights",
    "Amphawa Floating Market": "Amphawa: The City on Water",
    "Amphawa Extended Tour + Wat Samphran (privat)": "Amphawa: The City on Water",
    "Khao Yai National Park – Full Day (grup)": "Khao Yai National Park – Full Day",
    "Kanchanaburi – River Kwai + Erawan Falls (grup)": "Kanchanaburi: River Kwai & Erawan Falls",
}

REVIEW_REQUIRED_TOURS = {
    "Whale Tour",
    "Whale Tour (nespecificat)",
    "Uthai Thani / Sacred River",
    "Ayutthaya 5 Highlights",
    "Ayutthaya UNESCO Full Day Tour (grup)",
    "Amphawa Floating Market",
    "Amphawa Extended Tour + Wat Samphran (privat)",
}

def resolve_tour_mapping(booking_tour_name: str):
    raw_name = (booking_tour_name or "").strip()
    canonical_name = TOUR_NAME_MAP.get(raw_name)

    if raw_name in REVIEW_REQUIRED_TOURS:
        return canonical_name, "probable_manual_review", True

    if canonical_name is not None:
        return canonical_name, "confirmed", False

    return None, "unmapped", True

def booking_status(raw_status: str) -> str:
    return STATUS_MAP.get(raw_status, "Inquiry")
