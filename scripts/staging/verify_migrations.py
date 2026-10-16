#!/usr/bin/env python3
import argparse
import subprocess
from pathlib import Path

from common import ROOT, compose_command, run_preflight, staging_runtime_problems


MIGRATIONS = (
    ROOT / "database/migrations/20261015_add_booking_import_review_metadata.sql",
    ROOT / "database/migrations/20261015_add_audit_log_idempotency_fields.sql",
    ROOT / "database/migrations/20261016_add_booking_deposit_amount.sql",
)

parser = argparse.ArgumentParser(description="Verify staging review/audit schema; optional backed-up additive migration apply")
parser.add_argument("--apply-missing", action="store_true", help="apply both idempotent additive migrations after backup validation")
parser.add_argument("--backup", type=Path, help="readable pre-change pg_dump custom-format backup")
args = parser.parse_args()

report = run_preflight(check_docker_conflicts=False)
if not report.ok:
    print("BLOCKED: staging configuration is invalid; details suppressed")
    raise SystemExit(2)
runtime_problems = staging_runtime_problems()
if runtime_problems:
    print("BLOCKED: isolated staging resources are not verified; no database command run")
    for problem in runtime_problems:
        print("reason:", problem)
    raise SystemExit(2)
if args.apply_missing:
    if not args.backup or not args.backup.is_file():
        print("BLOCKED: --apply-missing requires an existing backup file")
        raise SystemExit(2)
    with args.backup.open("rb") as backup:
        verified = subprocess.run(
            compose_command("exec", "-T", "postgres", "pg_restore", "--list"),
            cwd=ROOT, stdin=backup, stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL, env=__import__("common")._clean_compose_env(),
        )
    if verified.returncode:
        print("BLOCKED: backup is not readable")
        raise SystemExit(2)
    for migration in MIGRATIONS:
        applied = subprocess.run(
            compose_command("exec", "-T", "postgres", "psql", "-X", "-v", "ON_ERROR_STOP=1", "-U", "tct_admin", "-d", "thaiculture_manager_staging_test"),
            cwd=ROOT, input=migration.read_text(encoding="utf-8"),
            text=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            env=__import__("common")._clean_compose_env(),
        )
        if applied.returncode:
            print("BLOCKED: an additive staging migration failed; raw output suppressed")
            raise SystemExit(3)

sql = """
SELECT table_name || '.' || column_name || '|' || data_type || '|' || is_nullable
FROM information_schema.columns
WHERE table_schema='public' AND (
  (table_name='bookings' AND column_name IN ('imported_raw_tour_name','mapping_status','needs_manual_review')) OR
  (table_name='bookings' AND column_name='deposit_amount') OR
  (table_name='audit_log' AND column_name IN ('request_id','request_payload_hash','actor_email_snapshot','actor_name_snapshot','reason'))
)
ORDER BY table_name, ordinal_position;
SELECT 'INDEX|' || indexname || '|' || indexdef
FROM pg_indexes
WHERE schemaname='public' AND tablename='audit_log' AND indexname='uq_audit_log_user_request_id';
"""
checked = subprocess.run(
    compose_command("exec", "-T", "postgres", "psql", "-X", "-A", "-t", "-v", "ON_ERROR_STOP=1", "-U", "tct_admin", "-d", "thaiculture_manager_staging_test", "-c", sql),
    cwd=ROOT, capture_output=True, text=True,
    env=__import__("common")._clean_compose_env(),
)
if checked.returncode:
    print("BLOCKED: staging schema inspection failed; details suppressed")
    raise SystemExit(4)
lines = [line.strip() for line in checked.stdout.splitlines() if line.strip()]
expected = {
    "bookings.imported_raw_tour_name|text|YES",
    "bookings.mapping_status|character varying|YES",
    "bookings.needs_manual_review|boolean|YES",
    "bookings.deposit_amount|numeric|YES",
    "audit_log.request_id|uuid|YES",
    "audit_log.request_payload_hash|character varying|YES",
    "audit_log.actor_email_snapshot|text|YES",
    "audit_log.actor_name_snapshot|text|YES",
    "audit_log.reason|text|YES",
}
columns = {line for line in lines if not line.startswith("INDEX|")}
index_ok = any(
    line.startswith("INDEX|uq_audit_log_user_request_id|")
    and "(user_id, request_id)" in line
    and "request_id IS NOT NULL" in line
    for line in lines
)
for name in sorted(expected):
    print(f"{'PASS' if name in columns else 'MISSING'}: {name.split('|')[0]}")
print("PASS: partial unique index" if index_ok else "MISSING: partial unique index")
raise SystemExit(0 if expected.issubset(columns) and index_ok else 5)
