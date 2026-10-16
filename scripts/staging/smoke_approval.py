#!/usr/bin/env python3
"""Run the isolated PostgreSQL approval endpoint smoke suite."""

import os
import subprocess
import sys
from urllib.parse import quote, urlsplit, urlunsplit

from common import ROOT, TEST_DATABASE, parse_env_file, run_preflight, staging_runtime_problems


report = run_preflight(check_docker_conflicts=False)
if not report.ok:
    print("BLOCKED: staging configuration is invalid; smoke tests not run")
    for problem in report.problems:
        print("reason:", problem)
    raise SystemExit(2)
runtime_problems = staging_runtime_problems()
if runtime_problems:
    print("BLOCKED: isolated staging resources are not verified; smoke tests not run")
    for problem in runtime_problems:
        print("reason:", problem)
    raise SystemExit(2)
values = parse_env_file()
parts = urlsplit(values["DATABASE_URL"])
test_url = urlunsplit((
    parts.scheme,
    f"{quote(parts.username or '', safe='')}:{quote(parts.password or '', safe='')}@127.0.0.1:55441",
    "/" + TEST_DATABASE,
    parts.query,
    "",
))
env = os.environ.copy()
env.update(values)
env["DATABASE_URL"] = test_url
env["TCT_TEST_DATABASE_URL"] = test_url
result = subprocess.run(
    [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-p", "test_import_review_approval.py", "-v"],
    cwd=ROOT / "backend", env=env, capture_output=True, text=True,
)
output = result.stdout + result.stderr
summary = next((line.strip() for line in reversed(output.splitlines()) if line.strip().startswith(("Ran ", "OK", "FAILED"))), "no unittest summary")
print("approval smoke suite:", summary)
if result.returncode:
    print("failure details suppressed")
raise SystemExit(result.returncode)
