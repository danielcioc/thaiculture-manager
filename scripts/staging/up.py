#!/usr/bin/env python3
import subprocess

from common import (
    compose_command,
    inspect_runtime_inventory,
    print_preflight,
    run_static_preflight,
)


report = run_static_preflight()
print_preflight(report)
if not report.ok:
    raise SystemExit(2)
inventory = inspect_runtime_inventory(report.resources)
print("RUNTIME INVENTORY:", inventory.status)
for problem in inventory.problems:
    print("runtime reason:", problem)
if not inventory.ok:
    print("BLOCKED: runtime inventory must be available and conflict-free before startup")
    raise SystemExit(3)
result = subprocess.run(
    compose_command("up", "-d", "--build", "--wait"),
    cwd=__import__("common").ROOT,
    env=__import__("common")._clean_compose_env(),
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL,
)
if result.returncode:
    print("BLOCKED: Compose startup failed; raw output suppressed")
    raise SystemExit(result.returncode)
print("staging stack started:", ", ".join(report.resources["containers"].values()))
