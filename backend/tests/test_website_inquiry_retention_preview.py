import json
import contextlib
import io
import os
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts import cleanup_website_retention as cleanup


NOW = datetime(2026, 10, 17, 12, 0, tzinfo=timezone.utc)
CUTOFF = NOW - timedelta(days=30)


class Transaction:
    def __init__(self, connection):
        self.connection = connection

    def __enter__(self):
        self.connection.transaction_started += 1
        return self

    def __exit__(self, exc_type, _exc, _tb):
        if exc_type:
            self.connection.rollbacks += 1
        else:
            self.connection.commits += 1
        return False


class FakeConnection:
    def __init__(self, *, customer_id="customer-test", fail_on=None, customer_deleted=False):
        self.customer_id = customer_id
        self.fail_on = fail_on
        self.customer_deleted = customer_deleted
        self.booking_present = True
        self.statements = []
        self.transaction_started = self.commits = self.rollbacks = 0

    def transaction(self):
        return Transaction(self)

    def execute(self, query, params=None):
        compact = " ".join(query.split())
        self.statements.append((compact, params))
        if self.fail_on and self.fail_on in compact:
            raise RuntimeError("synthetic database failure")
        if compact.startswith("SELECT customer_id FROM bookings"):
            return Result((self.customer_id,) if self.booking_present else None)
        if compact.startswith("DELETE FROM bookings"):
            self.booking_present = False
            return Result(("booking-test",))
        if compact.startswith("DELETE FROM customers") and self.customer_deleted:
            return Result((self.customer_id,))
        return Result(None)


class Result:
    def __init__(self, row):
        self.row = row
        self.rowcount = 1 if row else 0

    def fetchone(self):
        return self.row

    def fetchall(self):
        return [self.row] if self.row else []


class WebsiteRetentionCleanupTests(unittest.TestCase):
    def test_inquiry_preview_reports_candidate_shared_and_dependent_counts(self):
        class PreviewConnection:
            def __init__(self):
                self.calls = 0

            def execute(self, query, params):
                self.calls += 1
                compact = " ".join(query.split())
                if compact.startswith("SELECT count(*),"):
                    return Result((5, 0, 1))
                if compact.startswith("SELECT count(*) FROM receipts"):
                    return Result((2,))
                return Result((1,))

        report = cleanup._preview_inquiries(PreviewConnection(), CUTOFF)
        self.assertEqual(report["candidates"], 5)
        self.assertEqual(report["related_counts"]["missing_customer"], 0)
        self.assertEqual(report["related_counts"]["shared_customer_preserved"], 1)
        self.assertEqual(report["related_counts"]["dependent_receipts"], 2)
        self.assertEqual(report["related_counts"]["dependent_website_quote_previews"], 1)

    def test_policy_cutoffs_are_24_hours_and_30_days(self):
        self.assertEqual(cleanup.IDEMPOTENCY_HOURS, 24)
        self.assertEqual(cleanup.INQUIRY_DAYS, 30)

    def test_idempotency_prune_is_bounded_and_uses_24h_cutoff(self):
        conn = FakeConnection()
        deleted = cleanup._delete_idempotency_batch(conn, NOW - timedelta(hours=24), 50)
        self.assertEqual(deleted, 0)
        statement, params = conn.statements[0]
        self.assertIn("created_at < %s", statement)
        self.assertIn("FOR UPDATE SKIP LOCKED", statement)
        self.assertIn("LIMIT %s", statement)
        self.assertEqual(params, (NOW - timedelta(hours=24), 50))
        self.assertEqual(conn.commits, 1)

    def test_inquiry_candidate_query_excludes_converted_and_is_bounded(self):
        class CandidateConnection:
            def __init__(self):
                self.statement = None

            def execute(self, query, params):
                self.statement = " ".join(query.split())
                self.params = params
                return Result(None)

        conn = CandidateConnection()
        cleanup._inquiry_batch_ids(conn, CUTOFF, 25)
        self.assertIn("source='Website'", conn.statement)
        self.assertIn("status='Inquiry'", conn.statement)
        self.assertIn("created_at < %s", conn.statement)
        self.assertIn("LIMIT %s", conn.statement)
        self.assertEqual(conn.params, (CUTOFF, 25))

    def test_deletion_order_clears_receipts_then_children_then_booking(self):
        conn = FakeConnection(customer_deleted=True)
        deleted, customer_deleted = cleanup._delete_one_inquiry(conn, "booking-test", CUTOFF)
        statements = [statement for statement, _ in conn.statements]
        self.assertTrue(deleted)
        self.assertTrue(customer_deleted)
        self.assertEqual(conn.commits, 1)
        self.assertEqual(conn.rollbacks, 0)
        receipt_index = next(i for i, sql in enumerate(statements) if sql.startswith("DELETE FROM receipts"))
        booking_index = next(i for i, sql in enumerate(statements) if sql.startswith("DELETE FROM bookings"))
        customer_index = next(i for i, sql in enumerate(statements) if sql.startswith("DELETE FROM customers"))
        child_indexes = [
            next(i for i, sql in enumerate(statements) if sql.startswith(f"DELETE FROM {table} "))
            for table in cleanup.BOOKING_CHILD_TABLES
        ]
        self.assertLess(receipt_index, min(child_indexes))
        self.assertLess(max(child_indexes), booking_index)
        self.assertLess(booking_index, customer_index)
        self.assertTrue(any("NOT EXISTS (SELECT 1 FROM bookings" in sql for sql in statements))
        self.assertFalse(any(sql.startswith("DELETE FROM audit_log") for sql in statements))

    def test_shared_customer_is_preserved_by_not_exists_guard(self):
        conn = FakeConnection(customer_deleted=False)
        deleted, customer_deleted = cleanup._delete_one_inquiry(conn, "booking-test", CUTOFF)
        self.assertTrue(deleted)
        self.assertFalse(customer_deleted)
        customer_delete = next(sql for sql, _ in conn.statements if sql.startswith("DELETE FROM customers"))
        self.assertIn("NOT EXISTS", customer_delete)

    def test_converted_booking_is_preserved(self):
        class ConvertedConnection(FakeConnection):
            def execute(self, query, params=None):
                compact = " ".join(query.split())
                self.statements.append((compact, params))
                return Result(None)

        conn = ConvertedConnection()
        deleted, customer_deleted = cleanup._delete_one_inquiry(conn, "converted-booking", CUTOFF)
        self.assertFalse(deleted)
        self.assertFalse(customer_deleted)
        self.assertEqual(len(conn.statements), 1)
        self.assertEqual(conn.commits, 1)

    def test_dependency_error_rolls_back_candidate_without_booking_delete(self):
        conn = FakeConnection(fail_on="DELETE FROM payments")
        with self.assertRaises(RuntimeError):
            cleanup._delete_one_inquiry(conn, "booking-test", CUTOFF)
        self.assertEqual(conn.rollbacks, 1)
        self.assertFalse(any(sql.startswith("DELETE FROM bookings") for sql, _ in conn.statements))

    def test_repeated_inquiry_cleanup_is_safe_and_does_not_repeat_deletes(self):
        conn = FakeConnection()
        self.assertEqual(cleanup._delete_one_inquiry(conn, "booking-test", CUTOFF), (True, False))
        statement_count = len(conn.statements)
        self.assertEqual(cleanup._delete_one_inquiry(conn, "booking-test", CUTOFF), (False, False))
        self.assertEqual(len(conn.statements), statement_count + 1)
        self.assertEqual(conn.commits, 2)

    def test_log_report_is_aggregate_only_and_contains_no_pii(self):
        args = cleanup.parse_args([
            "--job", "inquiries", "--mode", "preview", "--operator", "Test Operator",
            "--target-label", "synthetic-test", "--expected-host", "127.0.0.1",
            "--expected-port", "55441", "--expected-database", "synthetic_db",
        ])
        report = cleanup._report_base(args, NOW, "run-test")
        report.update(status="COMPLETE", counts={"candidates": 1, "skipped": 0, "blocked": 0, "deleted": 0})
        output = json.dumps(report)
        for marker in ("private@example.invalid", "Private Customer", "+66000000000", "booking-uuid-marker"):
            self.assertNotIn(marker, output)
        self.assertIn("timestamp", report)
        self.assertIn("operator", report)
        self.assertIn("target_label", report)
        self.assertIn("cutoff", report)

    def test_target_mismatch_blocks_before_connection_without_echoing_dsn(self):
        args = cleanup.parse_args([
            "--job", "inquiries", "--operator", "Operator", "--target-label", "local-test",
            "--expected-host", "127.0.0.1", "--expected-port", "55441",
            "--expected-database", "synthetic_db",
        ])
        dsn = "postgresql://private-user:private-password@localhost:5432/other_db"
        connect = Mock(side_effect=AssertionError("must not connect"))
        with patch.dict(os.environ, {"DATABASE_URL": dsn}):
            report = cleanup.run(args, now=NOW, connect=connect)
        self.assertEqual(report["status"], "BLOCKED_TARGET_MISMATCH")
        connect.assert_not_called()
        self.assertNotIn("private-password", json.dumps(report))

    def test_apply_requires_backup_reference_and_defaults_to_preview(self):
        base = ["--job", "inquiries", "--operator", "Operator", "--target-label", "test",
                "--expected-host", "localhost", "--expected-port", "5432", "--expected-database", "test_db"]
        self.assertEqual(cleanup.parse_args(base).mode, "preview")
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            cleanup.parse_args([*base, "--mode", "apply"])
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            cleanup.parse_args([*base, "--mode", "apply", "--backup-reference", "backup-001"])
        apply_args = cleanup.parse_args([
            *base, "--mode", "apply", "--backup-reference", "backup-001", "--backup-verified"
        ])
        self.assertEqual(apply_args.mode, "apply")
        self.assertTrue(apply_args.backup_verified)


if __name__ == "__main__":
    unittest.main()
