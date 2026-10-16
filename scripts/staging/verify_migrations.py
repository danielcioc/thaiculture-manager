#!/usr/bin/env python3
import argparse
import subprocess
from pathlib import Path

from common import ROOT, _clean_compose_env, compose_command, run_preflight, staging_runtime_problems
from migration_contract import EXPECTED_COLUMNS, EXPECTED_INDEXES, MIGRATIONS, schema_gaps


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify additive staging schema; optional backed-up migration apply")
    parser.add_argument("--apply-missing", action="store_true", help="apply the configured additive migrations after backup validation")
    parser.add_argument("--backup", type=Path, help="readable pre-change pg_dump custom-format backup")
    args = parser.parse_args()

    report = run_preflight(check_docker_conflicts=False)
    if not report.ok:
        print("BLOCKED: staging configuration is invalid; details suppressed")
        return 2
    runtime_problems = staging_runtime_problems()
    if runtime_problems:
        print("BLOCKED: isolated staging resources are not verified; no database command run")
        for problem in runtime_problems:
            print("reason:", problem)
        return 2
    if args.apply_missing:
        if not args.backup or not args.backup.is_file():
            print("BLOCKED: --apply-missing requires an existing backup file")
            return 2
        with args.backup.open("rb") as backup:
            verified = subprocess.run(
                compose_command("exec", "-T", "postgres", "pg_restore", "--list"),
                cwd=ROOT, stdin=backup, stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL, env=_clean_compose_env(),
            )
        if verified.returncode:
            print("BLOCKED: backup is not readable")
            return 2
        for migration in MIGRATIONS:
            applied = subprocess.run(
                compose_command("exec", "-T", "postgres", "psql", "-X", "-v", "ON_ERROR_STOP=1", "-U", "tct_admin", "-d", "thaiculture_manager_staging_test"),
                cwd=ROOT, input=migration.read_text(encoding="utf-8"),
                text=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                env=_clean_compose_env(),
            )
            if applied.returncode:
                print("BLOCKED: an additive staging migration failed; raw output suppressed")
                return 3

    sql = """
    SELECT table_name || '.' || column_name || '|' || data_type || '|' || is_nullable
    FROM information_schema.columns
    WHERE table_schema='public' AND (
      (table_name='bookings' AND column_name IN ('imported_raw_tour_name','mapping_status','needs_manual_review','deposit_amount')) OR
      (table_name='audit_log' AND column_name IN ('request_id','request_payload_hash','actor_email_snapshot','actor_name_snapshot','reason')) OR
      table_name IN ('website_quote_previews','website_booking_idempotency')
    )
    ORDER BY table_name, ordinal_position;
    SELECT 'INDEX|' || tablename || '|' || indexname || '|' || indexdef
    FROM pg_indexes
    WHERE schemaname='public' AND (
      (tablename='audit_log' AND indexname='uq_audit_log_user_request_id') OR
      (tablename='website_quote_previews' AND indexname='idx_website_quote_previews_expires_at')
    );
    """
    checked = subprocess.run(
        compose_command("exec", "-T", "postgres", "psql", "-X", "-A", "-t", "-v", "ON_ERROR_STOP=1", "-U", "tct_admin", "-d", "thaiculture_manager_staging_test", "-c", sql),
        cwd=ROOT, capture_output=True, text=True,
        env=_clean_compose_env(),
    )
    if checked.returncode:
        print("BLOCKED: staging schema inspection failed; details suppressed")
        return 4

    lines = [line.strip() for line in checked.stdout.splitlines() if line.strip()]
    missing_columns, missing_indexes = schema_gaps(lines)
    for column in sorted(EXPECTED_COLUMNS):
        name = column.split("|", 1)[0]
        print(f"{'MISSING' if column in missing_columns else 'PASS'}: {name}")
    for index_name in sorted(EXPECTED_INDEXES):
        print(f"{'MISSING' if index_name in missing_indexes else 'PASS'}: {index_name}")
    return 5 if missing_columns or missing_indexes else 0


if __name__ == "__main__":
    raise SystemExit(main())
