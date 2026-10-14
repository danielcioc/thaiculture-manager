# ThaiCulture Manager — Session Checkpoint

Date: 2026-10-12 22:44:16 CEST

## Verified work today
- Created database dump: `backups/thaiculture_manager_20261012_224416.dump`.
- Dump was non-empty and readable by `pg_restore --list`; its archive list includes booking and payment data.
- Booking `TCT-IMP-2026-0001` is Alexis Chen + Holger Roessner.
- Daniel confirmed Alexis paid 6,500 THB cash directly to the guide on 2025-12-18.
- Payment was inserted and committed with reference `TCT-TH-2025-1218-001`, method Cash, status Paid, and paid_at 2025-12-18 12:00 UTC+07.
- A follow-up SELECT returned exactly one matching payment. PostgreSQL displayed the timestamp as 2025-12-18 05:00:00+00.
- Do not insert this payment again.

## Git state before checkpoint
Branch: main.
Untracked before this checkpoint: `backend/import_rules.py`, `backend/tests/`, and `backups/`.
These backend files were inspected and must be preserved. No Git staging, commit, or push was authorized for this checkpoint.

## Current project next step
Existing `docs/HANDOFF.md` and `docs/NEXT_STEPS.md` say the next task is persistent importer review metadata:
`imported_raw_tour_name`, `mapping_status`, and `needs_manual_review`.
Preserve raw tour labels; use confirmed/probable_manual_review/unmapped statuses; do not silently fuzzy-match unknown labels or automatically create tours.
Inspect the untracked importer rules and tests before deciding implementation changes.

## Resume instructions
Work terminal-only and provide exact commands. Start by checking `git status --short` and reading this checkpoint plus `docs/HANDOFF.md` and `docs/NEXT_STEPS.md`. Do not reinsert the Alexis payment. Do not claim Git commit/push unless terminal output confirms it.
