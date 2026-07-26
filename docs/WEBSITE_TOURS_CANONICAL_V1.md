# ThaiCulture Manager — Website Tours Canonical v1

Last updated: 2026-07-26

## Purpose

This document defines the canonical public tour catalog currently published on thaiculture.tours.
This catalog must be treated as the source of truth for website-integrated tours.
ThaiCulture Manager should align its internal tour model to these canonical website products instead of rebuilding a separate catalog from imported booking labels.

## Canonical Fields

Each canonical website tour should be represented internally with at least:
- website_tour_id
- website_link
- english_title
- pricing_mode
- base_price_display
- duration_code

## Canonical Website Tours

1. id=1 | link=9-wonders-of-capital.html | title=9 Wonders of the Capital | price=3,800 THB | duration_code=1
2. id=2 | link=orasul-lunii-safirelor.html | title=The City of Moon and Sapphires | price=4,500 THB | duration_code=1
3. id=3 | link=classic-bangkok-tour.html | title=Classic Bangkok | price=3,200 THB | duration_code=1
4. id=4 | link=mystic-bangkok-tour.html | title=Mystic Bangkok | price=3,500 THB | duration_code=1
5. id=5 | link=all-bangkok-tour.html | title=All of Bangkok (Extended Tour) | price=4,100 THB | duration_code=1
6. id=6 | link=evening-in-ayutthaya.html | title=Evening in Ayutthaya | price=3,700 THB | duration_code=1
7. id=7 | link=ayutthaya-5-sights-tour.html | title=Ayutthaya: 5 Essential Sights | price=3,000 THB | duration_code=1
8. id=8 | link=evening-in-ancient-siam.html | title=Evening in Ancient Siam | price=2,900 THB | duration_code=1
9. id=9 | link=dragons-lair-tour.html | title=Dragon's Lair | price=3,800 THB | duration_code=1
10. id=10 | link=jurassic-park-tour.html | title=Jurassic Park Tour | price=4,500 THB | duration_code=1
11. id=11 | link=wat-khun-chan-ko-kret.html | title=Wat Khun Chan & Ko Kret | price=3,100 THB | duration_code=1
12. id=12 | link=amphawa-extended-tour.html | title=Amphawa: The City on Water | price=3,400 THB | duration_code=1
13. id=13 | link=pattaya-night-tour.html | title=Pattaya Night Tour | price=2,500 THB | duration_code=0.5
14. id=14 | link=baan-sukhawadee-tour.html | title=Baan Sukhawadee | price=1,800 THB | duration_code=0.5
15. id=15 | link=treasure-of-isan-tour.html | title=Treasure of Isan | price=7,500 THB | duration_code=2
16. id=16 | link=whale-safari-tour.html | title=Whale Safari | price=9,500 THB | duration_code=2
17. id=17 | link=above-the-clouds-tour.html | title=Above The Clouds | price=7,900 THB | duration_code=2
18. id=18 | link=explorers-expedition-tour.html | title=Explorers Expedition | price=8,500 THB | duration_code=2
19. id=19 | link=amazing-thailand-ritual.html | title=Amazing Thailand + Cultural Depths | price=11,500 THB | duration_code=3
20. id=20 | link=phuket-tour.html | title=Phuket: Explorer’s Day Out | price=3,900 THB | duration_code=1
21. id=21 | link=hua-hin-bangkok-day-trip.html | title=1-Day Trip – Hua Hin → Bangkok | price=On Request | duration_code=1
22. id=22 | link=kui-buri-elephant-watching.html | title=Elephant Watching in Kui Buri National Park | price=On request | duration_code=1
23. id=23 | link=hua-hin-temple-tour.html | title=Hua Hin Temple Tour | price=On request | duration_code=1
24. id=24 | link=chiang-rai-white-blue-temples.html | title=Chiang Rai: White Temple, Blue Temple & Hill Tribe Village – day trip | price=On request | duration_code=1
25. id=25 | link=hua-hin-temples-elephants-safari.html | title=Hua Hin Temples & Elephant Safari | price=10,900 THB | duration_code=1
26. id=26 | link=uthai-thani-sacred-river-hidden-heritage.html | title=Uthai Thani Sacred River & Hidden Heritage | price=On request | duration_code=2

## Pricing Modes

The canonical catalog already implies two pricing modes:
- fixed_price: tours with explicit THB amount published on the website
- on_request: tours published without a fixed public price

This distinction must be preserved in the manager because the website booking flow will support both direct price calculation and manual quotation paths.

## Integration Direction

The website must remain the public source of truth for canonical tour products.
ThaiCulture Manager must store or reference these products in a compatible way so that:
- customers can calculate a price on the website;
- customers can create a booking request or booking from the website;
- the system can generate a proforma when the workflow requires it;
- internal operations remain linked to the same canonical website product.

No implementation should treat imported CSV labels as the canonical tour catalog.
Imported historical labels must be mapped to these website tour products.
