# ThaiCulture Manager — Imported Tour Mapping v1

Last updated: 2026-07-26

## Purpose

This document defines how historical imported booking tour labels must map to the canonical public tour catalog published on thaiculture.tours.

The website catalog is the canonical source of truth for public tours.
Imported CSV labels are historical operational inputs and must not be treated as the canonical catalog.

## Mapping Principles

- Match imported labels to canonical website tours whenever a clear product equivalence exists.
- Preserve imported raw labels for traceability.
- Do not create duplicate internal tour products from legacy CSV wording.
- If a historical label is ambiguous, mark it for manual review instead of forcing a wrong automatic mapping.
- Future website-originated bookings should reference canonical website tour identifiers directly.

## Confirmed Canonical Target

Canonical reference document:
- docs/WEBSITE_TOURS_CANONICAL_V1.md

## Imported Label Mapping

1. Imported label: Evening Ayutthaya UNESCO Temples Tour (privat)
   Canonical website tour: Evening in Ayutthaya
   Canonical link: evening-in-ayutthaya.html
   Mapping status: confirmed
   Notes: Strong semantic match.

2. Imported label: Hua Hin – Bangkok Day Trip
   Canonical website tour: 1-Day Trip – Hua Hin → Bangkok
   Canonical link: hua-hin-bangkok-day-trip.html
   Mapping status: confirmed
   Notes: Same route/product family.

3. Imported label: Kui Buri National Park – Elephant Watching
   Canonical website tour: Elephant Watching in Kui Buri National Park
   Canonical link: kui-buri-elephant-watching.html
   Mapping status: confirmed
   Notes: Same destination and activity.

4. Imported label: Hua Hin Temple Tour – Cultural Day Trip
   Canonical website tour: Hua Hin Temple Tour
   Canonical link: hua-hin-temple-tour.html
   Mapping status: confirmed
   Notes: Same core product.

5. Imported label: Whale Tour
   Canonical website tour: Whale Safari
   Canonical link: whale-safari-tour.html
   Mapping status: probable_manual_review
   Notes: Likely match, but wording is less exact and should remain reviewable.

6. Imported label: Classic Bangkok
   Canonical website tour: Classic Bangkok
   Canonical link: classic-bangkok-tour.html
   Mapping status: confirmed
   Notes: Exact title match.

7. Imported label: Mystic Bangkok
   Canonical website tour: Mystic Bangkok
   Canonical link: mystic-bangkok-tour.html
   Mapping status: confirmed
   Notes: Exact title match.

8. Imported label: Uthai Thani / Sacred River
   Canonical website tour: Uthai Thani Sacred River & Hidden Heritage
   Canonical link: uthai-thani-sacred-river-hidden-heritage.html
   Mapping status: probable_manual_review
   Notes: Strong match but shortened imported wording.

9. Imported label: Ayutthaya 5 Highlights
   Canonical website tour: Ayutthaya: 5 Essential Sights
   Canonical link: ayutthaya-5-sights-tour.html
   Mapping status: probable_manual_review
   Notes: Same likely product, but wording differs.

10. Imported label: Amphawa Floating Market
    Canonical website tour: Amphawa: The City on Water
    Canonical link: amphawa-extended-tour.html
    Mapping status: probable_manual_review
    Notes: Likely related, but imported wording may reference only one component of the website product.

## Operational Rule

Historical imports may continue storing:
- imported_raw_tour_name

But canonical internal referencing should move toward:
- website_tour_id
- website_link
- canonical_english_title

## Implementation Direction

Importer logic should eventually:
1. preserve the raw imported label;
2. attempt deterministic mapping to a canonical website tour;
3. flag ambiguous matches for review;
4. avoid creating duplicate tour records from historical wording.

No importer implementation should be treated as final until it follows this mapping model.
