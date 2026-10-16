#!/usr/bin/env python3
from common import inspect_runtime_inventory, print_preflight, run_static_preflight


report = run_static_preflight()
print_preflight(report)
if not report.ok:
    raise SystemExit(2)

inventory = inspect_runtime_inventory(report.resources)
print("RUNTIME INVENTORY:", inventory.status)
for service, status in inventory.services.items():
    print(f"service {service}: {status}")
for volume, status in inventory.volumes.items():
    print(f"volume {volume}: {status}")
for network, status in inventory.networks.items():
    print(f"network {network}: {status}")
for problem in inventory.problems:
    print("runtime reason:", problem)
raise SystemExit(0 if inventory.ok else 3)
