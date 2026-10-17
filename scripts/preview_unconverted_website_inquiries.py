#!/usr/bin/env python3
"""Backward-compatible read-only entrypoint for website Inquiry preview."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.cleanup_website_retention import main as cleanup_main


def main(argv: list[str] | None = None) -> int:
    forwarded = list(sys.argv[1:] if argv is None else argv)
    if "--cutoff-days" in forwarded:
        position = forwarded.index("--cutoff-days")
        value = forwarded[position + 1] if position + 1 < len(forwarded) else ""
        if value != "30":
            print("cutoff is fixed at 30 days", file=sys.stderr)
            return 2
        del forwarded[position : position + 2]
    return cleanup_main(["--job", "inquiries", "--mode", "preview", *forwarded])


if __name__ == "__main__":
    raise SystemExit(main())
