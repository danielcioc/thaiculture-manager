import csv
import json
import uuid
from pathlib import Path

import psycopg

import os
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://tct_admin:tct_local_password@localhost:5433/thaiculture_manager")

ROOT = Path(__file__).resolve().parent.parent
IMPORTS = ROOT / "data" / "imports"

BOOKINGS_CSV = IMPORTS / "bookings.csv"
PAYMENTS_CSV = IMPORTS / "payments.csv"
INVOICES_CSV = IMPORTS / "invoices.csv"

STATUS_MAP = {
    "Confirmat / Efectuat": "Confirmed",
    "Facturat / Efectuat": "Confirmed",
    "Cerere (fără răspuns)": "Pending",
    "Refuzat (buget)": "Cancelled",
}

LANG_MAP = {"RO": "RO", "EN": "EN", "FR": "FR"}

def booking_code(idx: int) -> str:
    return f"TCT-IMP-2026-{idx:04d}"

def split_name(display_name: str):
    if not display_name:
        return None, None, "Unknown"
    parts = display_name.strip().split()
    if len(parts) == 1:
        return None, parts[0], display_name
    return " ".join(parts[:-1]), parts[-1], display_name

def get_or_create_location(cur, name: str):
    if not name:
        return None
    cur.execute(
        "SELECT id FROM locations WHERE lower(name) = lower(%s) LIMIT 1",
        (name,),
    )
    row = cur.fetchone()
    if row:
        return row[0]
    loc_id = str(uuid.uuid4())
    cur.execute(
        """
        INSERT INTO locations (id, name, city, country)
        VALUES (%s, %s, %s, %s)
        """,
        (loc_id, name, name, "Thailand"),
    )
    return loc_id

def get_or_create_customer(cur, display_name: str, email: str, language: str, notes: str):
    if email:
        cur.execute(
            "SELECT id FROM customers WHERE lower(email) = lower(%s) LIMIT 1",
            (email,),
        )
        row = cur.fetchone()
        if row:
            return row[0]
    cur.execute(
        "SELECT id FROM customers WHERE display_name = %s LIMIT 1",
        (display_name,),
    )
    row = cur.fetchone()
    if row:
        return row[0]

    first_name, last_name, display = split_name(display_name)
    customer_id = str(uuid.uuid4())
    cur.execute(
        """
        INSERT INTO customers (
            id, first_name, last_name, display_name, email,
            preferred_language, notes
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """,
        (
            customer_id,
            first_name,
            last_name,
            display,
            email or None,
            LANG_MAP.get(language or "EN", "EN"),
            notes or None,
        ),
    )
    return customer_id

def pick_tour(cur, booking_tour_name: str):
    cur.execute(
        """
        SELECT id, name, tour_code
        FROM tours
        WHERE lower(name) LIKE lower(%s)
        ORDER BY name
        LIMIT 1
        """,
        (f"%{booking_tour_name.split('–')[0].split('(')[0].strip()}%",),
    )
    row = cur.fetchone()
    return row[0] if row else None

def existing_booking(cur, customer_id, tour_date, pickup_location_id):
    cur.execute(
        """
        SELECT id, booking_code
        FROM bookings
        WHERE customer_id = %s
          AND tour_date IS NOT DISTINCT FROM %s
          AND pickup_location_id IS NOT DISTINCT FROM %s
        LIMIT 1
        """,
        (customer_id, tour_date or None, pickup_location_id),
    )
    return cur.fetchone()

def import_bookings(cur):
    inserted = []
    with BOOKINGS_CSV.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for idx, row in enumerate(reader, start=1):
            customer_id = get_or_create_customer(
                cur,
                row["customer_name"],
                row["email"],
                row["language"],
                row["notes"],
            )
            pickup_location_id = get_or_create_location(cur, row["hotel_location"])
            tour_id = pick_tour(cur, row["tour"])

            tour_date = row["tour_date"].strip() if row["tour_date"] and not row["tour_date"].startswith("~") else None
            people_raw = (row["people"] or "").strip()
            adults = 0
            children = 0
            infants = 0
            if people_raw.isdigit():
                adults = int(people_raw)
            elif "copil" in people_raw.lower():
                adults = 4
                children = 1

            found = existing_booking(cur, customer_id, tour_date, pickup_location_id)
            if found:
                inserted.append((found[0], found[1], "existing"))
                continue

            bid = str(uuid.uuid4())
            bcode = booking_code(idx)
            cur.execute(
                """
                INSERT INTO bookings (
                    id, booking_code, status, source, customer_id, tour_id,
                    tour_date, pickup_location_id, adults, children, infants,
                    guide_language, selling_price, currency
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    bid,
                    bcode,
                    STATUS_MAP.get(row["status"], "Pending"),
                    "Imported Excel",
                    customer_id,
                    tour_id,
                    tour_date or None,
                    pickup_location_id,
                    adults,
                    children,
                    infants,
                    LANG_MAP.get(row["language"] or "EN", "EN"),
                    float(row["price_thb"]) if row["price_thb"] else 0,
                    "THB",
                ),
            )
            inserted.append((bid, bcode, "inserted"))
    return inserted

def import_payments(cur, booking_map):
    if not PAYMENTS_CSV.exists():
        return 0
    count = 0
    with PAYMENTS_CSV.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        invoice_booking = {
            "TCT-TH-2026-0206-001": "Catalina Popa",
            "TCT-TH-2026-HH-002": "Andreea",
        }
        for row in reader:
            customer_hint = invoice_booking.get(row["invoice_no"])
            booking_id = None
            if customer_hint:
                for bid, meta in booking_map.items():
                    if meta["customer_name"] == customer_hint:
                        booking_id = bid
                        break
            if not booking_id:
                continue
            cur.execute(
                """
                INSERT INTO payments (id, booking_id, amount, currency, method, status, reference)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    str(uuid.uuid4()),
                    booking_id,
                    0,
                    "THB",
                    row["method"],
                    row["status"],
                    f"Imported from {row['invoice_no']}",
                ),
            )
            count += 1
    return count

def import_invoices(cur, booking_map):
    if not INVOICES_CSV.exists():
        return 0
    count = 0
    with INVOICES_CSV.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        invoice_booking = {
            "TCT-TH-2026-0206-001": "Catalina Popa",
            "TCT-TH-2026-HH-002": "Andreea",
        }
        for row in reader:
            customer_hint = invoice_booking.get(row["invoice_no"])
            booking_id = None
            if customer_hint:
                for bid, meta in booking_map.items():
                    if meta["customer_name"] == customer_hint:
                        booking_id = bid
                        break
            if not booking_id:
                continue
            cur.execute(
                """
                INSERT INTO invoices (id, booking_id, invoice_no, invoice_type, amount, status)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (invoice_no) DO NOTHING
                """,
                (
                    str(uuid.uuid4()),
                    booking_id,
                    row["invoice_no"],
                    "customer",
                    float(row["total"]) if row["total"] else 0,
                    row["status"].lower(),
                ),
            )
            count += 1
    return count

def main():
    if not BOOKINGS_CSV.exists():
        raise SystemExit(f"Missing file: {BOOKINGS_CSV}")

    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            inserted = import_bookings(cur)

            booking_map = {}
            for bid, bcode, _ in inserted:
                cur.execute(
                    """
                    SELECT b.id, b.booking_code, c.display_name
                    FROM bookings b
                    JOIN customers c ON c.id = b.customer_id
                    WHERE b.id = %s
                    """,
                    (bid,),
                )
                row = cur.fetchone()
                if row:
                    booking_map[row[0]] = {
                        "booking_code": row[1],
                        "customer_name": row[2],
                    }

            payments_count = import_payments(cur, booking_map)
            invoices_count = 0  # TEMP: skip broken invoice CSV parsing
        conn.commit()

    print("Import complete")
    print(json.dumps({
        "bookings_processed": len(inserted),
        "payments_inserted": payments_count,
        "invoices_inserted": invoices_count
    }, indent=2))

if __name__ == "__main__":
    main()
