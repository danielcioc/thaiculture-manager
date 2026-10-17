#!/usr/bin/env python3
"""Preview or explicitly apply website inquiry/idempotency retention cleanup.

Preview is the default. Apply requires an explicit target identity and a backup
reference. Output is aggregate-only and database failures are never echoed.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import uuid
from datetime import datetime, timedelta, timezone
from urllib.parse import urlsplit


INQUIRY_DAYS = 30
IDEMPOTENCY_HOURS = 24
BATCH_SIZE_DEFAULT = 100
OPERATOR_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 ._-]{0,99}$")
IDENTIFIER_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,99}$")
HOST_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9.-]{0,252}$")
DB_RE = re.compile(r"^[A-Za-z0-9_][A-Za-z0-9_.-]{0,62}$")
BACKUP_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,99}$")

# All direct booking foreign keys from the base schema and website migration.
BOOKING_CHILD_TABLES = (
    "booking_guests",
    "assignments",
    "pricing_quotes",
    "payments",
    "costs",
    "documents",
    "invoices",
    "emails",
    "reviews",
    "notifications",
    "website_quote_previews",
    "website_booking_idempotency",
)
REQUIRED_TABLES = (*BOOKING_CHILD_TABLES, "receipts", "bookings", "customers")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--job", required=True, choices=("idempotency", "inquiries"))
    parser.add_argument("--mode", choices=("preview", "apply"), default="preview")
    parser.add_argument("--operator", required=True)
    parser.add_argument("--target-label", required=True)
    parser.add_argument("--expected-host", required=True)
    parser.add_argument("--expected-port", required=True, type=int)
    parser.add_argument("--expected-database", required=True)
    parser.add_argument("--backup-reference")
    parser.add_argument("--backup-verified", action="store_true")
    parser.add_argument("--batch-size", type=int, default=BATCH_SIZE_DEFAULT)
    args = parser.parse_args(argv)
    checks = (
        (OPERATOR_RE, args.operator, "operator must be a plain name"),
        (IDENTIFIER_RE, args.target_label, "target label must be a non-secret identifier"),
        (HOST_RE, args.expected_host, "expected host must be a hostname or IP"),
        (DB_RE, args.expected_database, "expected database must be an identifier"),
    )
    for pattern, value, message in checks:
        if not pattern.fullmatch(value):
            parser.error(message)
    if not 1 <= args.expected_port <= 65535:
        parser.error("expected port must be between 1 and 65535")
    if args.backup_reference and not BACKUP_RE.fullmatch(args.backup_reference):
        parser.error("backup reference must be a non-secret reference token")
    if args.mode == "apply" and not args.backup_reference:
        parser.error("--backup-reference is required for apply mode")
    if args.mode == "apply" and not args.backup_verified:
        parser.error("--backup-verified is required for apply mode")
    if not 1 <= args.batch_size <= 1000:
        parser.error("batch size must be between 1 and 1000")
    return args


def _target_matches(dsn: str, host: str, port: int, database: str) -> bool:
    try:
        parsed = urlsplit(dsn)
        return (
            parsed.scheme in {"postgres", "postgresql"}
            and (parsed.hostname or "").casefold() == host.casefold()
            and (parsed.port or 5432) == port
            and parsed.path.lstrip("/") == database
        )
    except ValueError:
        return False


def _report_base(args: argparse.Namespace, now: datetime, run_id: str) -> dict:
    age = timedelta(hours=IDEMPOTENCY_HOURS) if args.job == "idempotency" else timedelta(days=INQUIRY_DAYS)
    return {
        "timestamp": now.astimezone(timezone.utc).isoformat(),
        "run_id": run_id,
        "job": f"website_{args.job}_retention",
        "operator": args.operator,
        "target_label": args.target_label,
        "target_host": args.expected_host,
        "target_port": args.expected_port,
        "database_name": args.expected_database,
        "cutoff": (now - age).isoformat(),
        "backup_reference": args.backup_reference,
        "backup_verified": args.backup_verified,
    }


def _empty_counts() -> dict:
    return {"candidates": 0, "deleted": 0, "skipped": 0, "blocked": 0, "errors": 0, "blocker_categories": {}}


def _schema_is_ready(conn) -> bool:
    rows = conn.execute(
        """
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = current_schema()
          AND table_type = 'BASE TABLE'
          AND table_name = ANY(%s);
        """,
        (list(REQUIRED_TABLES),),
    ).fetchall()
    return {row[0] for row in rows} >= set(REQUIRED_TABLES)


def _preview_idempotency(conn, cutoff: datetime) -> dict:
    row = conn.execute(
        "SELECT count(*) FROM website_booking_idempotency WHERE created_at < %s;", (cutoff,)
    ).fetchone()
    counts = _empty_counts()
    counts["candidates"] = row[0]
    return counts


def _preview_inquiries(conn, cutoff: datetime) -> dict:
    rows = conn.execute(
        """
        SELECT count(*),
               count(*) FILTER (WHERE b.customer_id IS NULL),
               count(*) FILTER (WHERE b.customer_id IS NOT NULL AND EXISTS (
                   SELECT 1 FROM bookings other
                   WHERE other.customer_id = b.customer_id AND other.id <> b.id
               ))
        FROM bookings b
        WHERE b.source = 'Website' AND b.status = 'Inquiry' AND b.created_at < %s;
        """,
        (cutoff,),
    ).fetchone()
    counts = _empty_counts()
    counts["candidates"] = rows[0]
    counts["related_counts"] = {
        "missing_customer": rows[1],
        "shared_customer_preserved": rows[2],
    }
    # Known dependent rows are removed transactionally, not treated as blockers.
    dependent_total = 0
    for table in BOOKING_CHILD_TABLES:
        fk = "consumed_booking_id" if table == "website_quote_previews" else "booking_id"
        count = conn.execute(
            f"""SELECT count(*) FROM {table} child JOIN bookings b ON b.id = child.{fk}
                WHERE b.source = 'Website' AND b.status = 'Inquiry' AND b.created_at < %s;""",
            (cutoff,),
        ).fetchone()[0]
        counts["related_counts"][f"dependent_{table}"] = count
        dependent_total += count
    receipts = conn.execute(
        """SELECT count(*) FROM receipts r
           WHERE r.payment_id IN (SELECT p.id FROM payments p JOIN bookings b ON b.id=p.booking_id
             WHERE b.source='Website' AND b.status='Inquiry' AND b.created_at < %s)
              OR r.document_id IN (SELECT d.id FROM documents d JOIN bookings b ON b.id=d.booking_id
             WHERE b.source='Website' AND b.status='Inquiry' AND b.created_at < %s);""",
        (cutoff, cutoff),
    ).fetchone()[0]
    counts["related_counts"]["dependent_receipts"] = receipts
    return counts


def _delete_idempotency_batch(conn, cutoff: datetime, batch_size: int) -> int:
    with conn.transaction():
        rows = conn.execute(
            """
            WITH expired AS (
                SELECT ctid FROM website_booking_idempotency
                WHERE created_at < %s
                ORDER BY created_at, idempotency_key
                FOR UPDATE SKIP LOCKED
                LIMIT %s
            )
            DELETE FROM website_booking_idempotency target
            USING expired WHERE target.ctid = expired.ctid
            RETURNING 1;
            """,
            (cutoff, batch_size),
        ).fetchall()
    return len(rows)


def _inquiry_batch_ids(conn, cutoff: datetime, batch_size: int, after: tuple | None = None) -> list[tuple]:
    if after is None:
        return conn.execute(
            """SELECT id, created_at FROM bookings
               WHERE source='Website' AND status='Inquiry' AND created_at < %s
               ORDER BY created_at, id LIMIT %s;""",
            (cutoff, batch_size),
        ).fetchall()
    return conn.execute(
        """SELECT id, created_at FROM bookings
           WHERE source='Website' AND status='Inquiry' AND created_at < %s
             AND (created_at, id) > (%s, %s)
           ORDER BY created_at, id LIMIT %s;""",
        (cutoff, after[0], after[1], batch_size),
    ).fetchall()


def _delete_one_inquiry(conn, booking_id, cutoff: datetime) -> tuple[bool, bool]:
    """Return (deleted, customer_deleted); all effects for one booking are atomic."""
    with conn.transaction():
        row = conn.execute(
            """SELECT customer_id FROM bookings
               WHERE id=%s AND source='Website' AND status='Inquiry' AND created_at < %s
               FOR UPDATE;""",
            (booking_id, cutoff),
        ).fetchone()
        if row is None:
            return False, False
        customer_id = row[0]

        # Receipts reference payments and documents, so they must be removed first.
        conn.execute(
            """DELETE FROM receipts
               WHERE payment_id IN (SELECT id FROM payments WHERE booking_id=%s)
                  OR document_id IN (SELECT id FROM documents WHERE booking_id=%s);""",
            (booking_id, booking_id),
        )
        # Delete every known direct FK child. Audit log is intentionally append-only
        # and has no booking FK; it is not deleted by this retention job.
        for table in BOOKING_CHILD_TABLES:
            fk = "consumed_booking_id" if table == "website_quote_previews" else "booking_id"
            conn.execute(f"DELETE FROM {table} WHERE {fk}=%s;", (booking_id,))
        deleted = conn.execute(
            """DELETE FROM bookings WHERE id=%s AND source='Website'
                 AND status='Inquiry' AND created_at < %s RETURNING id;""",
            (booking_id, cutoff),
        ).fetchone()
        if deleted is None:
            raise RuntimeError("locked inquiry unexpectedly changed")
        customer_deleted = False
        if customer_id is not None:
            customer_deleted = conn.execute(
                """DELETE FROM customers c WHERE c.id=%s
                   AND NOT EXISTS (SELECT 1 FROM bookings b WHERE b.customer_id=c.id)
                   RETURNING c.id;""",
                (customer_id,),
            ).fetchone() is not None
        return True, customer_deleted


def _apply_job(conn, args: argparse.Namespace, cutoff: datetime) -> dict:
    counts = _empty_counts()
    if args.job == "idempotency":
        while True:
            removed = _delete_idempotency_batch(conn, cutoff, args.batch_size)
            counts["candidates"] += removed
            counts["deleted"] += removed
            if removed < args.batch_size:
                break
        return counts

    after = None
    while True:
        rows = _inquiry_batch_ids(conn, cutoff, args.batch_size, after)
        if not rows:
            break
        for booking_id, created_at in rows:
            counts["candidates"] += 1
            try:
                deleted, customer_deleted = _delete_one_inquiry(conn, booking_id, cutoff)
                if deleted:
                    counts["deleted"] += 1
                    if customer_deleted:
                        counts.setdefault("customers_deleted", 0)
                        counts["customers_deleted"] += 1
                else:
                    counts["skipped"] += 1
            except Exception:
                # The per-candidate transaction rolled back. Never log DB details.
                counts["errors"] += 1
                counts["blocked"] += 1
                categories = counts["blocker_categories"]
                categories["foreign_key_or_database_error"] = categories.get("foreign_key_or_database_error", 0) + 1
        if len(rows) < args.batch_size:
            break
        # Keyset pagination lets the run continue past a blocked candidate
        # without selecting it repeatedly or starving newer inquiries.
        after = (rows[-1][1], rows[-1][0])
    return counts


def run(args: argparse.Namespace, *, now: datetime | None = None, connect=None) -> dict:
    now = now or datetime.now(timezone.utc)
    run_id = str(uuid.uuid4())
    report = _report_base(args, now, run_id)
    report["mode"] = args.mode
    report["status"] = "BLOCKED_TARGET_MISMATCH"
    report["counts"] = None
    dsn = os.environ.get("DATABASE_URL", "")
    if not dsn or not _target_matches(dsn, args.expected_host, args.expected_port, args.expected_database):
        return report
    try:
        if connect is None:
            import psycopg
            connect = psycopg.connect
        with connect(dsn, connect_timeout=5, options="-c statement_timeout=5000", autocommit=True) as conn:
            if conn.execute("SELECT current_database()").fetchone()[0] != args.expected_database:
                return report
            if not _schema_is_ready(conn):
                report["status"] = "BLOCKED_SCHEMA_NOT_READY"
                return report
            cutoff = now - (
                timedelta(hours=IDEMPOTENCY_HOURS)
                if args.job == "idempotency"
                else timedelta(days=INQUIRY_DAYS)
            )
            if args.mode == "preview":
                with conn.transaction():
                    conn.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY;")
                    counts = _preview_idempotency(conn, cutoff) if args.job == "idempotency" else _preview_inquiries(conn, cutoff)
            else:
                counts = _apply_job(conn, args, cutoff)
            report["status"] = "COMPLETE"
            report["counts"] = counts
            report["mutations_performed"] = counts["deleted"]
            return report
    except Exception:
        report["status"] = "BLOCKED_DATABASE_ERROR"
        return report


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = run(args)
    print(json.dumps(report, sort_keys=True))
    return 0 if report["status"] == "COMPLETE" else 2


if __name__ == "__main__":
    raise SystemExit(main())
