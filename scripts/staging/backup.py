#!/usr/bin/env python3
from datetime import datetime, timezone
import subprocess
import tempfile
from pathlib import Path

from common import ROOT, compose_command, run_preflight, staging_runtime_problems


report = run_preflight(check_docker_conflicts=False)
if not report.ok:
    print("BLOCKED: staging configuration is invalid; no database command run")
    for problem in report.problems:
        print("reason:", problem)
    raise SystemExit(2)
runtime_problems = staging_runtime_problems()
if runtime_problems:
    print("BLOCKED: isolated staging resources are not verified; no database command run")
    for problem in runtime_problems:
        print("reason:", problem)
    raise SystemExit(2)

destination = Path(tempfile.gettempdir()) / (
    "thaiculture-staging-approval-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + ".dump"
)
command = compose_command(
    "exec", "-T", "postgres", "pg_dump", "--format=custom", "--no-owner",
    "--no-privileges", "-U", "tct_admin", "-d", "thaiculture_manager_staging_test",
)
try:
    with destination.open("wb") as backup:
        destination.chmod(0o600)
        result = subprocess.run(command, cwd=ROOT, stdout=backup, stderr=subprocess.DEVNULL, env=__import__("common")._clean_compose_env())
except OSError:
    print("BLOCKED: staging backup could not be created; details suppressed")
    raise SystemExit(3)
if result.returncode or not destination.is_file() or destination.stat().st_size == 0:
    destination.unlink(missing_ok=True)
    print("BLOCKED: staging backup failed; details suppressed")
    raise SystemExit(3)

with destination.open("rb") as backup:
    verify = subprocess.run(
        compose_command("exec", "-T", "postgres", "pg_restore", "--list"),
        cwd=ROOT,
        stdin=backup,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        env=__import__("common")._clean_compose_env(),
    )
if verify.returncode:
    destination.unlink(missing_ok=True)
    print("BLOCKED: backup was created but pg_restore could not read it")
    raise SystemExit(4)
print("PASS: staging custom-format backup created and readable")
print("backup file:", destination)
