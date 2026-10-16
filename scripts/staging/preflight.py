#!/usr/bin/env python3
from common import print_preflight, run_preflight


report = run_preflight()
print_preflight(report)
raise SystemExit(0 if report.ok else 2)
