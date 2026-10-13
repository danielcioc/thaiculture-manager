# Pricing Status — 2026-10-13

## Current state

The database contains 28 active tours and 7 active pricing rules.

## Pricing usage

- WEB-007 is confirmed and approved for quote.
- WEB-021, WEB-022, and WEB-023 have available direct costs but remain estimated.
- WEB-006, WEB-027, and WEB-028 are reference-only with incomplete direct costs.
- Estimated or incomplete rules require manual review.

## Business rule

Only pricing rules with:

- `confidence_status = confirmed`
- `pricing_use = approved_for_quote`
- `cost_status = available`
- `requires_manual_review = false`

may be used for automatic quoting.

Historical booking prices remain stored on the booking and must not be overwritten by catalog pricing changes.
