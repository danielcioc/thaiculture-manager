"""PostgreSQL-backed regression coverage for website retention.

Only runs when TCT_TEST_DATABASE_URL identifies a dedicated local test database.
Each test uses and drops its own schema; it never targets an application database.
"""

from __future__ import annotations

import os
import sys
import unittest
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlparse
from uuid import uuid4
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts import cleanup_website_retention as cleanup


TEST_DATABASE_URL = os.getenv("TCT_TEST_DATABASE_URL")
_parsed_url = urlparse(TEST_DATABASE_URL) if TEST_DATABASE_URL else None
_safe_test_database = bool(
    _parsed_url
    and "test" in _parsed_url.path.lower()
    and _parsed_url.hostname in {"localhost", "127.0.0.1", "postgres-test"}
    and _parsed_url.port is not None
    and _parsed_url.port >= 50000
)


@unittest.skipUnless(_safe_test_database, "requires a dedicated local TCT_TEST_DATABASE_URL")
class WebsiteRetentionPostgresTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import psycopg

        cls.psycopg = psycopg
        cls.schema = f"website_retention_test_{uuid4().hex[:12]}"
        cls.schema_options = f"-csearch_path={cls.schema},public -cstatement_timeout=5000"
        cls.parsed_url = _parsed_url

        with psycopg.connect(TEST_DATABASE_URL, autocommit=True) as admin:
            admin.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto WITH SCHEMA public")
            admin.execute(f'CREATE SCHEMA "{cls.schema}"')

        root = Path(__file__).resolve().parents[2]
        schema_sql = (root / "database/init/001_schema.sql").read_text(encoding="utf-8")
        schema_sql = "\n".join(
            line for line in schema_sql.splitlines()
            if not line.lstrip().startswith("--")
            and not line.strip().upper().startswith("CREATE EXTENSION")
        )
        migration_sql = (root / "database/migrations/20261016_add_website_quote_idempotency.sql").read_text(
            encoding="utf-8"
        )
        with cls.connect(autocommit=True) as conn:
            for statement in (schema_sql + "\n" + migration_sql).split(";"):
                if statement.strip() and statement.strip().upper() not in {"BEGIN", "COMMIT"}:
                    conn.execute(statement)

    @classmethod
    def tearDownClass(cls):
        with cls.psycopg.connect(TEST_DATABASE_URL, autocommit=True) as admin:
            admin.execute(f'DROP SCHEMA IF EXISTS "{cls.schema}" CASCADE')

    @classmethod
    def connect(cls, *, autocommit=False):
        return cls.psycopg.connect(TEST_DATABASE_URL, options=cls.schema_options, autocommit=autocommit)

    def setUp(self):
        with self.connect(autocommit=True) as conn:
            tables = conn.execute(
                "SELECT tablename FROM pg_tables WHERE schemaname=%s ORDER BY tablename",
                (self.schema,),
            ).fetchall()
            qualified = ", ".join(f'"{self.schema}"."{row[0]}"' for row in tables)
            conn.execute(f"TRUNCATE TABLE {qualified} CASCADE")
            self.tour_id = uuid4()
            conn.execute(
                "INSERT INTO tours (id,tour_code,name,website_url) VALUES (%s,%s,%s,%s)",
                (self.tour_id, f"RET-{uuid4().hex[:8]}", "Synthetic Retention Tour", "https://example.com/tour"),
            )

    def _customer(self):
        with self.connect() as conn:
            row = conn.execute(
                "INSERT INTO customers (display_name,email) VALUES (%s,%s) RETURNING id",
                (f"Synthetic Customer {uuid4().hex[:6]}", f"{uuid4().hex}@example.com"),
            ).fetchone()
            return row[0]

    def _booking(self, code, *, status="Inquiry", age_days=45, customer_id=None):
        customer_id = customer_id or self._customer()
        booking_id = uuid4()
        with self.connect() as conn:
            conn.execute(
                """INSERT INTO bookings (id,booking_code,status,source,customer_id,created_at)
                   VALUES (%s,%s,%s,'Website',%s,%s)""",
                (booking_id, code, status, customer_id, datetime.now(timezone.utc) - timedelta(days=age_days)),
            )
        return booking_id, customer_id

    def _retention_run(self, job, mode, *, now=None, batch_size=10):
        args = cleanup.parse_args([
            "--job", job, "--mode", mode, "--operator", "Synthetic Test Operator",
            "--target-label", "isolated-postgres-test", "--expected-host", self.parsed_url.hostname,
            "--expected-port", str(self.parsed_url.port), "--expected-database", self.parsed_url.path.lstrip("/"),
            "--batch-size", str(batch_size),
            *( ["--backup-reference", "synthetic-backup-ref", "--backup-verified"] if mode == "apply" else [] ),
        ])

        def connect(_dsn, **kwargs):
            kwargs.pop("options", None)
            return self.psycopg.connect(TEST_DATABASE_URL, options=self.schema_options, **kwargs)

        with patch.dict(os.environ, {"DATABASE_URL": TEST_DATABASE_URL}):
            return cleanup.run(args, now=now or datetime.now(timezone.utc), connect=connect)

    def _add_dependents(self, booking_id, suffix):
        payment_id, document_id = uuid4(), uuid4()
        with self.connect() as conn:
            conn.execute("INSERT INTO booking_guests (booking_id,full_name) VALUES (%s,%s)", (booking_id, "Synthetic Guest"))
            conn.execute("INSERT INTO assignments (booking_id,assignment_type) VALUES (%s,'other')", (booking_id,))
            conn.execute(
                "INSERT INTO pricing_quotes (booking_id,total_cost,recommended_price,minimum_price,breakdown) VALUES (%s,1,2,1,'{}')",
                (booking_id,),
            )
            conn.execute(
                "INSERT INTO payments (id,booking_id,amount,method,status) VALUES (%s,%s,1,'test','paid')",
                (payment_id, booking_id),
            )
            conn.execute("INSERT INTO costs (booking_id,cost_type,amount) VALUES (%s,'test',1)", (booking_id,))
            conn.execute(
                "INSERT INTO documents (id,booking_id,document_type) VALUES (%s,%s,'test')",
                (document_id, booking_id),
            )
            conn.execute(
                "INSERT INTO invoices (booking_id,invoice_no,invoice_type,amount) VALUES (%s,%s,'invoice',1)",
                (booking_id, f"RET-{suffix}-{uuid4().hex[:8]}"),
            )
            conn.execute(
                "INSERT INTO emails (booking_id,to_email,subject) VALUES (%s,%s,'synthetic')",
                (booking_id, f"{uuid4().hex}@example.com"),
            )
            conn.execute("INSERT INTO reviews (booking_id,platform) VALUES (%s,'synthetic')", (booking_id,))
            conn.execute("INSERT INTO notifications (booking_id,title) VALUES (%s,'synthetic')", (booking_id,))
            conn.execute(
                """INSERT INTO website_quote_previews
                   (tour_id,tour_code,tour_name,website_tour_id,tour_date,adults,children,extras,currency,total,
                    total_cost,minimum_price,rule_name,pricing_policy_version,breakdown,expires_at,consumed_booking_id)
                   VALUES (%s,'SYN','Synthetic Tour','synthetic-tour',current_date,1,0,'[]','THB',1,1,1,
                           'synthetic','v1','{}',now()+interval '1 day',%s)""",
                (self.tour_id, booking_id),
            )
            conn.execute(
                """INSERT INTO website_booking_idempotency (idempotency_key,payload_hash,booking_id,response_payload)
                   VALUES (%s,%s,%s,'{}')""",
                (uuid4(), "a" * 64, booking_id),
            )
            conn.execute(
                "INSERT INTO receipts (payment_id,receipt_no,document_id) VALUES (%s,%s,%s)",
                (payment_id, f"RET-RCP-{suffix}-{uuid4().hex[:8]}", document_id),
            )

    def test_idempotency_ttl_and_expired_key_reuse_with_real_postgres(self):
        from app.routers import website
        from fastapi import HTTPException

        now = datetime.now(timezone.utc)
        active_key, expired_key, api_key = uuid4(), uuid4(), uuid4()
        with self.connect() as conn:
            conn.execute(
                """INSERT INTO website_booking_idempotency (idempotency_key,payload_hash,created_at)
                   VALUES (%s,%s,%s),(%s,%s,%s),(%s,%s,%s)""",
                (active_key, "a"*64, now-timedelta(hours=1), expired_key, "b"*64, now-timedelta(hours=25),
                 api_key, "c"*64, now-timedelta(hours=25)),
            )
            quote_id = uuid4()
            quote_date = date.today() + timedelta(days=7)
            conn.execute(
                """INSERT INTO website_quote_previews
                   (id,tour_id,tour_code,tour_name,website_tour_id,tour_date,adults,children,extras,currency,total,
                    total_cost,minimum_price,rule_name,pricing_policy_version,breakdown,expires_at)
                   VALUES (%s,%s,'SYN','Synthetic Tour','synthetic-tour',%s,1,0,'[]','THB',100,50,75,
                           'synthetic','minimum-margin-30-v1','{}',now()+interval '2 days')""",
                (quote_id, self.tour_id, quote_date),
            )

        request = website.WebsiteBookingRequest(
            quote_id=quote_id, date=quote_date, adults=1, children=0, currency="THB",
            customer=website.WebsiteCustomer(name="Synthetic API Customer", email="api-test@example.com"),
        )
        def schema_connection():
            return self.psycopg.connect(TEST_DATABASE_URL, options=self.schema_options)

        with patch.object(website.settings, "website_integration_enabled", True), patch.object(
            website, "_website_connection", side_effect=schema_connection
        ):
            first = website.create_website_booking(request, api_key)
            replay = website.create_website_booking(request, api_key)
            self.assertFalse(first["replayed"])
            self.assertTrue(replay["replayed"])
            with self.assertRaises(HTTPException) as conflict:
                website.create_website_booking(request.model_copy(update={"notes": "changed"}), api_key)
            self.assertEqual(conflict.exception.status_code, 409)

        preview = self._retention_run("idempotency", "preview", now=now)
        self.assertEqual(preview["status"], "COMPLETE")
        self.assertEqual(preview["counts"]["candidates"], 1)
        self.assertEqual(preview["mutations_performed"], 0)
        applied = self._retention_run("idempotency", "apply", now=now)
        self.assertEqual(applied["counts"]["deleted"], 1)
        self.assertEqual(applied["counts"]["blocked"], 0)
        rerun = self._retention_run("idempotency", "apply", now=now)
        self.assertEqual(rerun["counts"]["deleted"], 0)
        with self.connect() as conn:
            keys = {row[0] for row in conn.execute("SELECT idempotency_key FROM website_booking_idempotency").fetchall()}
            self.assertEqual(keys, {active_key, api_key})

    def test_inquiry_retention_fk_order_shared_customer_and_rollback(self):
        old_plain, old_customer = self._booking("RET-OLD-PLAIN")
        recent, recent_customer = self._booking("RET-RECENT", age_days=2)
        converted, converted_customer = self._booking("RET-CONVERTED", status="Confirmed", age_days=45)
        shared_customer = self._customer()
        shared_candidate, _ = self._booking("RET-SHARED", age_days=40, customer_id=shared_customer)
        shared_other, _ = self._booking("RET-SHARED-OTHER", status="Confirmed", age_days=45, customer_id=shared_customer)
        unshared, unshared_customer = self._booking("RET-UNSHARED")
        dependent, dependent_customer = self._booking("RET-DEPENDENT")
        rollback, rollback_customer = self._booking("RET-ROLLBACK", age_days=32)
        self._add_dependents(dependent, "DEP")
        self._add_dependents(rollback, "ROLLBACK")

        with self.connect(autocommit=True) as conn:
            conn.execute(
                f"""CREATE FUNCTION {self.schema}.retention_test_failure() RETURNS trigger
                    LANGUAGE plpgsql AS $$ BEGIN
                      IF OLD.booking_id = '{rollback}'::uuid THEN
                        RAISE EXCEPTION 'synthetic rollback fault';
                      END IF;
                      RETURN OLD;
                    END $$""",
                prepare=False,
            )
            conn.execute(
                f"CREATE TRIGGER retention_test_failure BEFORE DELETE ON {self.schema}.payments "
                f"FOR EACH ROW EXECUTE FUNCTION {self.schema}.retention_test_failure()"
            )

        now = datetime.now(timezone.utc)
        preview = self._retention_run("inquiries", "preview", now=now, batch_size=2)
        self.assertEqual(preview["counts"]["candidates"], 5)
        self.assertEqual(preview["counts"]["related_counts"]["shared_customer_preserved"], 1)
        self.assertEqual(preview["counts"]["related_counts"]["dependent_receipts"], 2)
        self.assertEqual(preview["mutations_performed"], 0)

        first = self._retention_run("inquiries", "apply", now=now, batch_size=2)
        self.assertEqual(first["counts"]["deleted"], 4)
        self.assertEqual(first["counts"]["blocked"], 1)
        self.assertEqual(first["counts"]["errors"], 1)
        with self.connect() as conn:
            self.assertEqual(conn.execute("SELECT count(*) FROM bookings WHERE id=%s", (rollback,)).fetchone()[0], 1)
            self.assertEqual(conn.execute("SELECT count(*) FROM receipts r JOIN payments p ON p.id=r.payment_id WHERE p.booking_id=%s", (rollback,)).fetchone()[0], 1)
            self.assertEqual(conn.execute("SELECT count(*) FROM website_booking_idempotency WHERE booking_id=%s", (rollback,)).fetchone()[0], 1)
            self.assertEqual(conn.execute("SELECT count(*) FROM website_quote_previews WHERE consumed_booking_id=%s", (rollback,)).fetchone()[0], 1)
            self.assertEqual(conn.execute("SELECT count(*) FROM customers WHERE id=%s", (old_customer,)).fetchone()[0], 0)
            self.assertEqual(conn.execute("SELECT count(*) FROM customers WHERE id=%s", (unshared_customer,)).fetchone()[0], 0)
            self.assertEqual(conn.execute("SELECT count(*) FROM customers WHERE id=%s", (dependent_customer,)).fetchone()[0], 0)
            self.assertEqual(conn.execute("SELECT count(*) FROM customers WHERE id=%s", (rollback_customer,)).fetchone()[0], 1)
            self.assertEqual(conn.execute("SELECT count(*) FROM customers WHERE id=%s", (shared_customer,)).fetchone()[0], 1)
            self.assertEqual(conn.execute("SELECT count(*) FROM bookings WHERE id IN (%s,%s)", (recent, converted)).fetchone()[0], 2)

        with self.connect(autocommit=True) as conn:
            conn.execute(f"DROP TRIGGER retention_test_failure ON {self.schema}.payments")
            conn.execute(f"DROP FUNCTION {self.schema}.retention_test_failure()")
        second = self._retention_run("inquiries", "apply", now=now, batch_size=2)
        self.assertEqual(second["counts"]["deleted"], 1)
        self.assertEqual(second["counts"]["customers_deleted"], 1)
        final = self._retention_run("inquiries", "apply", now=now, batch_size=2)
        self.assertEqual(final["counts"]["candidates"], 0)
        self.assertEqual(final["counts"]["deleted"], 0)

        with self.connect() as conn:
            self.assertEqual(conn.execute("SELECT count(*) FROM pg_constraint WHERE contype='f' AND NOT convalidated").fetchone()[0], 0)
            self.assertEqual(conn.execute(
                "SELECT count(*) FROM website_booking_idempotency i LEFT JOIN bookings b ON b.id=i.booking_id "
                "WHERE i.booking_id IS NOT NULL AND b.id IS NULL"
            ).fetchone()[0], 0)
            self.assertEqual(conn.execute(
                "SELECT count(*) FROM website_quote_previews q LEFT JOIN bookings b ON b.id=q.consumed_booking_id "
                "WHERE q.consumed_booking_id IS NOT NULL AND b.id IS NULL"
            ).fetchone()[0], 0)
            self.assertEqual(conn.execute("SELECT count(*) FROM bookings WHERE id IN (%s,%s)", (recent, converted)).fetchone()[0], 2)
            self.assertEqual(conn.execute("SELECT count(*) FROM bookings WHERE id=%s", (shared_other,)).fetchone()[0], 1)
            self.assertEqual(conn.execute("SELECT count(*) FROM customers WHERE id=%s", (shared_customer,)).fetchone()[0], 1)


if __name__ == "__main__":
    unittest.main()
