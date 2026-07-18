#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
import os
import re
from pathlib import Path
from datetime import datetime
from decimal import Decimal

import psycopg

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data" / "imports"
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://tct_admin:tct_local_password@localhost:5433/thaiculture_manager",
)
BOOKINGS_CSV = DATA_DIR / "bookings.csv"
SEED_JSON = DATA_DIR / "thaiculture_seed.json"

STATUS_MAP = {
    "Confirmat / Efectuat": "Confirmed",
    "Facturat / Efectuat": "Confirmed",
    "Refuzat (buget)": "Cancelled",
    "Cerere (fără răspuns)": "Pending",
}


def parse_date(value: str | None):
    if not value:
        return None
    value = value.strip()
    if value.startswith("~"):
        value = value[1:]
    return datetime.strptime(value, "%Y-%m-%d").date()


def people_to_counts(value: str | None):
    text = (value or "").strip().lower()
    adults = children = infants = 0
    if not text:
        return adults, children, infants
    m = re.fullmatch(r"\d+", text)
    if m:
        return int(text), 0, 0
    for n, label in re.findall(r"(\d+)\s*([^,+]+)", text):
        n = int(n)
        label = label.strip()
        if "copil" in label or "child" in label:
            children += n
        elif "infant" in label or "beb" in label:
            infants += n
        else:
            adults += n
    if adults == children == infants == 0:
        nums = re.findall(r"\d+", text)
        if nums:
            adults = int(nums[0])
    return adults, children, infants


def load_csv(path: Path):
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def load_seed():
    with SEED_JSON.open(encoding="utf-8") as f:
        return json.load(f)


def split_name(full_name: str | None):
    parts = (full_name or "").strip().split()
    if not parts:
        return None, None
    if len(parts) == 1:
        return parts[0], None
    return parts[0], " ".join(parts[1:])


def slug(value: str):
    return re.sub(r"[^A-Z0-9]+", "", value.upper())[:6] or "BOOK"


def build_booking_code(index: int, row: dict):
    date_part = row.get("tour_date") or "undated"
    date_part = re.sub(r"[^0-9]", "", date_part)[:8] or "00000000"
    name_part = slug(row.get("customer_name") or "BOOK")
    return f"IMP-{date_part}-{name_part}-{index:03d}"


def ensure_location(cur, location_ids, name: str | None):
    if not name:
        return None
    name = name.strip()
    if not name:
        return None
    if name in location_ids:
        return location_ids[name]
    cur.execute(
        "INSERT INTO locations (name, address, city, country) VALUES (%s, %s, %s, %s) RETURNING id",
        (name, name, None, "Thailand"),
    )
    lid = cur.fetchone()[0]
    location_ids[name] = lid
    return lid


def ensure_tour(cur, tour_ids, tour_name: str | None):
    if not tour_name:
        return None
    cur.execute("SELECT id FROM tours WHERE name = %s", (tour_name,))
    row = cur.fetchone()
    if row:
        return row[0]
    code = slug(tour_name)
    base = code
    i = 1
    while code in tour_ids:
        i += 1
        code = f"{base}{i}"
    cur.execute(
        "INSERT INTO tours (tour_code, name, category, default_duration_hours, is_active) VALUES (%s, %s, %s, %s, %s) RETURNING id",
        (code, tour_name, "Imported Tour", None, True),
    )
    tid = cur.fetchone()[0]
    tour_ids[code] = tid
    return tid


def main():
    for p in [BOOKINGS_CSV, SEED_JSON]:
        if not p.exists():
            raise SystemExit(f"Missing file: {p}")

    bookings_rows = load_csv(BOOKINGS_CSV)
    seed = load_seed()

    payments_by_customer = {}
    for p in seed.get("payments", []):
        code = p.get("booking_code")
        if code:
            payments_by_customer.setdefault(code, []).append(p)

    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            customer_ids = {}
            cur.execute("SELECT id, email, display_name FROM customers")
            for cid, email, display_name in cur.fetchall():
                if email:
                    customer_ids[email.lower()] = cid
                if display_name:
                    customer_ids[display_name.lower()] = cid

            tour_ids = {}
            cur.execute("SELECT id, tour_code FROM tours")
            for tid, code in cur.fetchall():
                if code:
                    tour_ids[code] = tid

            location_ids = {}
            cur.execute("SELECT id, name FROM locations")
            for lid, name in cur.fetchall():
                if name:
                    location_ids[name] = lid

            existing_booking_codes = set()
            cur.execute("SELECT booking_code FROM bookings")
            for (code,) in cur.fetchall():
                existing_booking_codes.add(code)

            existing_payment_keys = set()
            cur.execute("SELECT booking_id, amount, method, COALESCE(reference, '') FROM payments")
            for booking_id, amount, method, reference in cur.fetchall():
                existing_payment_keys.add((str(booking_id), str(amount), method or '', reference or ''))

            inserted_customers = 0
            inserted_tours = 0
            inserted_locations = 0
            inserted_bookings = 0
            inserted_payments = 0
            skipped_bookings = 0
            skipped_payments = 0

            for row in seed.get("customers", []):
                email = (row.get("email") or "").strip().lower()
                display_name = row.get("display_name") or row.get("name") or f"{row.get('first_name','')} {row.get('last_name','')}".strip()
                if not display_name:
                    continue
                key = email or display_name.lower()
                if key in customer_ids:
                    continue
                first_name, last_name = split_name(display_name)
                cur.execute(
                    """
                    INSERT INTO customers (
                        first_name, last_name, display_name, email, phone, whatsapp,
                        country, nationality, preferred_language, notes
                    ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    RETURNING id
                    """,
                    (
                        row.get("first_name") or first_name,
                        row.get("last_name") or last_name,
                        display_name,
                        row.get("email"),
                        row.get("phone"),
                        row.get("whatsapp"),
                        row.get("country"),
                        row.get("nationality"),
                        row.get("preferred_language") or row.get("language") or "EN",
                        row.get("notes"),
                    ),
                )
                cid = cur.fetchone()[0]
                customer_ids[key] = cid
                if email:
                    customer_ids[email] = cid
                customer_ids[display_name.lower()] = cid
                inserted_customers += 1

            for i, row in enumerate(bookings_rows, start=1):
                booking_code = build_booking_code(i, row)
                if booking_code in existing_booking_codes:
                    skipped_bookings += 1
                    continue

                customer_email = (row.get("email") or "").strip().lower()
                customer_name = (row.get("customer_name") or "").strip()
                customer_key = customer_email or customer_name.lower()
                customer_id = customer_ids.get(customer_key)
                if not customer_id and customer_name:
                    first_name, last_name = split_name(customer_name)
                    cur.execute(
                        """
                        INSERT INTO customers (
                            first_name, last_name, display_name, email, preferred_language, notes
                        ) VALUES (%s,%s,%s,%s,%s,%s)
                        RETURNING id
                        """,
                        (
                            first_name,
                            last_name,
                            customer_name,
                            row.get("email"),
                            row.get("language") or "EN",
                            row.get("notes"),
                        ),
                    )
                    customer_id = cur.fetchone()[0]
                    customer_ids[customer_key] = customer_id
                    if customer_email:
                        customer_ids[customer_email] = customer_id
                    customer_ids[customer_name.lower()] = customer_id
                    inserted_customers += 1

                before_tours = len(tour_ids)
                tour_id = ensure_tour(cur, tour_ids, row.get("tour"))
                if len(tour_ids) > before_tours:
                    inserted_tours += 1

                before_locations = len(location_ids)
                pickup_id = ensure_location(cur, location_ids, row.get("hotel_location"))
                if len(location_ids) > before_locations:
                    inserted_locations += 1

                adults, children, infants = people_to_counts(row.get("people"))
                status = STATUS_MAP.get(row.get("status"), row.get("status") or "Pending")

                cur.execute(
                    """
                    INSERT INTO bookings (
                        booking_code, status, source, customer_id, tour_id,
                        tour_date, pickup_time, pickup_location_id, dropoff_location_id,
                        adults, children, infants, guide_language, selling_price, currency
                    ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    RETURNING id
                    """,
                    (
                        booking_code,
                        status,
                        "Imported CSV",
                        customer_id,
                        tour_id,
                        parse_date(row.get("tour_date")) if row.get("tour_date") else None,
                        None,
                        pickup_id,
                        None,
                        adults,
                        children,
                        infants,
                        row.get("language") or "EN",
                        Decimal(str(row.get("price_thb") or "0")) if row.get("price_thb") else Decimal("0"),
                        "THB",
                    ),
                )
                booking_id = cur.fetchone()[0]
                existing_booking_codes.add(booking_code)
                inserted_bookings += 1

                for p in seed.get("payments", []):
                    if (p.get("booking_code") or "").strip() != booking_code:
                        continue
                    payment_key = (
                        str(booking_id),
                        str(Decimal(str(p.get("amount") or "0"))),
                        p.get("method") or "",
                        p.get("reference") or "",
                    )
                    if payment_key in existing_payment_keys:
                        skipped_payments += 1
                        continue
                    cur.execute(
                        """
                        INSERT INTO payments (
                            booking_id, amount, currency, method, status, paid_at, reference
                        ) VALUES (%s,%s,%s,%s,%s,%s,%s)
                        """,
                        (
                            booking_id,
                            Decimal(str(p.get("amount") or "0")),
                            p.get("currency") or "THB",
                            p.get("method") or "Cash",
                            p.get("status") or "Pending",
                            None,
                            p.get("reference"),
                        ),
                    )
                    existing_payment_keys.add(payment_key)
                    inserted_payments += 1

            conn.commit()

    print(json.dumps({
        "inserted_customers": inserted_customers,
        "inserted_tours": inserted_tours,
        "inserted_locations": inserted_locations,
        "inserted_bookings": inserted_bookings,
        "inserted_payments": inserted_payments,
        "skipped_existing_bookings": skipped_bookings,
        "skipped_existing_payments": skipped_payments,
        "database_url": DATABASE_URL,
    }, indent=2, default=str))


if __name__ == "__main__":
    main()
