import os
import unittest
from pathlib import Path
from urllib.parse import urlparse
from uuid import UUID, uuid4

from app.audit import (
    AuditIdempotencyConflict,
    hash_audit_payload,
    run_idempotent_audit_event,
)


class AuditPayloadHashTests(unittest.TestCase):
    def test_semantically_equivalent_payloads_have_same_hash(self):
        payload_upper = {
            "booking_id": "42000000-0000-0000-0000-000000000001".upper(),
            "expected": {"mapping_status": "probable_manual_review", "tour_id": None},
            "target": {
                "mapping_status": "confirmed",
                "tour_id": "44000000-0000-0000-0000-000000000001".upper(),
            },
            "reason": "  Owner approved  ",
            "request_id": str(uuid4()),
        }
        payload_lower = {
            "request_id": str(uuid4()),
            "reason": "Owner approved",
            "target": {
                "tour_id": "44000000-0000-0000-0000-000000000001",
                "mapping_status": "confirmed",
            },
            "expected": {"tour_id": None, "mapping_status": "probable_manual_review"},
            "booking_id": "42000000-0000-0000-0000-000000000001",
        }

        self.assertEqual(hash_audit_payload(payload_upper), hash_audit_payload(payload_lower))

    def test_distinct_payloads_have_different_hashes(self):
        original = {"booking_id": str(uuid4()), "reason": "Owner approved"}
        changed = {**original, "reason": "Different decision"}

        self.assertNotEqual(hash_audit_payload(original), hash_audit_payload(changed))


TEST_DATABASE_URL = os.getenv("TCT_TEST_DATABASE_URL")
_parsed_test_url = urlparse(TEST_DATABASE_URL) if TEST_DATABASE_URL else None
_safe_test_database = bool(
    _parsed_test_url
    and "test" in _parsed_test_url.path.lower()
    and _parsed_test_url.hostname in {"localhost", "127.0.0.1"}
    and _parsed_test_url.port is not None
    and _parsed_test_url.port >= 50000
)


@unittest.skipUnless(_safe_test_database, "requires isolated local TCT_TEST_DATABASE_URL")
class AuditIdempotencyPostgresTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import psycopg

        cls.psycopg = psycopg
        cls.schema = f"audit_test_{uuid4().hex[:12]}"
        cls.schema_options = f"-csearch_path={cls.schema}"
        with psycopg.connect(TEST_DATABASE_URL, autocommit=True) as admin:
            admin.execute(f'CREATE SCHEMA "{cls.schema}"')

        with psycopg.connect(
            TEST_DATABASE_URL,
            options=cls.schema_options,
            autocommit=True,
        ) as conn:
            with conn.transaction():
                conn.execute(
                    """
                    CREATE TABLE users (
                        id uuid PRIMARY KEY,
                        email text NOT NULL,
                        full_name text NOT NULL
                    );
                    CREATE TABLE bookings (
                        id uuid PRIMARY KEY,
                        status text NOT NULL
                    );
                    CREATE TABLE audit_log (
                        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
                        user_id uuid REFERENCES users(id),
                        entity_type varchar(50) NOT NULL,
                        entity_id uuid NOT NULL,
                        action varchar(50) NOT NULL,
                        old_value jsonb,
                        new_value jsonb,
                        created_at timestamptz DEFAULT now()
                    );
                    """
                )
                migration_path = (
                    Path(__file__).resolve().parents[2]
                    / "database/migrations/20261015_add_audit_log_idempotency_fields.sql"
                )
                migration_sql = "\n".join(
                    line
                    for line in migration_path.read_text(encoding="utf-8").splitlines()
                    if not line.lstrip().startswith("--")
                    and line.strip().upper() not in {"BEGIN;", "COMMIT;"}
                )
                for statement in migration_sql.split(";"):
                    if statement.strip():
                        conn.execute(statement)

    @classmethod
    def tearDownClass(cls):
        with cls.psycopg.connect(TEST_DATABASE_URL, autocommit=True) as admin:
            admin.execute(f'DROP SCHEMA IF EXISTS "{cls.schema}" CASCADE')

    def setUp(self):
        self.user_id = uuid4()
        self.booking_id = uuid4()
        self.request_id = uuid4()
        self.payload = {
            "booking_id": self.booking_id,
            "expected": {"status": "Inquiry"},
            "target": {"status": "Confirmed"},
            "reason": "Owner approved",
        }
        with self.connect() as conn:
            conn.execute(
                "INSERT INTO users (id, email, full_name) VALUES (%s, %s, %s)",
                (self.user_id, "audit-test@example.invalid", "Audit Test"),
            )
            conn.execute(
                "INSERT INTO bookings (id, status) VALUES (%s, %s)",
                (self.booking_id, "Inquiry"),
            )

    def connect(self):
        return self.psycopg.connect(TEST_DATABASE_URL, options=self.schema_options)

    def run_event(self, conn, operation, payload=None):
        return run_idempotent_audit_event(
            conn,
            user_id=self.user_id,
            request_id=self.request_id,
            request_payload=payload or self.payload,
            entity_type="booking_import_review",
            entity_id=self.booking_id,
            action="import_review.approved",
            old_value={"status": "Inquiry"},
            new_value={"status": "Confirmed"},
            actor_email_snapshot="audit-test@example.invalid",
            actor_name_snapshot="Audit Test",
            reason="Owner approved",
            operation=operation,
        )

    def count_events(self):
        with self.connect() as conn:
            return conn.execute(
                "SELECT count(*) FROM audit_log WHERE user_id = %s AND request_id = %s",
                (self.user_id, self.request_id),
            ).fetchone()[0]

    def test_first_request_runs_business_operation_and_inserts_one_event(self):
        calls = []

        def operation(conn):
            calls.append("called")
            conn.execute(
                "UPDATE bookings SET status = 'Confirmed' WHERE id = %s",
                (self.booking_id,),
            )
            return "booking-updated"

        with self.connect() as conn:
            with conn.transaction():
                result = self.run_event(conn, operation)
                self.assertFalse(result.replayed)
                self.assertEqual(result.operation_result, "booking-updated")
                self.assertEqual(conn.info.transaction_status.name, "INTRANS")
                self.assertEqual(calls, ["called"])

        self.assertEqual(self.count_events(), 1)

    def test_identical_retry_returns_original_event_without_second_operation(self):
        with self.connect() as conn:
            with conn.transaction():
                first = self.run_event(conn, lambda _conn: "first")

        with self.connect() as conn:
            with conn.transaction():
                retry = self.run_event(
                    conn,
                    lambda _conn: self.fail("retry must not run business operation"),
                )

        self.assertEqual(first.event["id"], retry.event["id"])
        self.assertTrue(retry.replayed)
        self.assertIsNone(retry.operation_result)
        self.assertEqual(self.count_events(), 1)

    def test_same_actor_and_request_id_with_different_hash_is_rejected(self):
        with self.connect() as conn:
            with conn.transaction():
                self.run_event(conn, lambda _conn: None)

        conflicting_payload = {**self.payload, "reason": "Different reason"}
        with self.connect() as conn:
            with conn.transaction():
                with self.assertRaises(AuditIdempotencyConflict):
                    self.run_event(
                        conn,
                        lambda _conn: self.fail("conflicting retry must not run business operation"),
                        payload=conflicting_payload,
                    )

        self.assertEqual(self.count_events(), 1)

    def test_error_after_business_update_and_audit_insert_rolls_back_both(self):
        with self.connect() as conn:
            with self.assertRaisesRegex(RuntimeError, "injected failure"):
                with conn.transaction():
                    self.run_event(
                        conn,
                        lambda transaction: transaction.execute(
                            "UPDATE bookings SET status = 'Confirmed' WHERE id = %s",
                            (self.booking_id,),
                        ),
                    )
                    raise RuntimeError("injected failure after business and audit writes")

        with self.connect() as conn:
            status = conn.execute(
                "SELECT status FROM bookings WHERE id = %s", (self.booking_id,)
            ).fetchone()[0]
        self.assertEqual(status, "Inquiry")
        self.assertEqual(self.count_events(), 0)

    def test_business_operation_error_propagates_without_audit_insert(self):
        def failing_operation(conn):
            conn.execute(
                "UPDATE bookings SET status = 'Confirmed' WHERE id = %s",
                (self.booking_id,),
            )
            raise RuntimeError("business operation failed")

        with self.connect() as conn:
            with self.assertRaisesRegex(RuntimeError, "business operation failed"):
                with conn.transaction():
                    self.run_event(conn, failing_operation)

        with self.connect() as conn:
            status = conn.execute(
                "SELECT status FROM bookings WHERE id = %s", (self.booking_id,)
            ).fetchone()[0]
        self.assertEqual(status, "Inquiry")
        self.assertEqual(self.count_events(), 0)
