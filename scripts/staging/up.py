#!/usr/bin/env python3
import subprocess

from common import compose_command, print_preflight, run_preflight


report = run_preflight()
print_preflight(report)
if not report.ok:
    raise SystemExit(2)
result = subprocess.run(
    compose_command("up", "-d", "--build"),
    cwd=__import__("common").ROOT,
    env=__import__("common")._clean_compose_env(),
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL,
)
if result.returncode:
    print("BLOCKED: Compose startup failed; raw output suppressed")
    raise SystemExit(result.returncode)
print("staging stack started:", ", ".join(report.resources["containers"]))
