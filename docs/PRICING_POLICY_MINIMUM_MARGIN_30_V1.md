# Pricing Policy: Minimum Net Margin 30% (v1)

Policy version: `minimum-margin-30-v1`

This policy applies only when an operator explicitly generates a new quote for an unconfirmed booking. It does not recalculate historical quotes, update a booking's selling price, change payments, or apply to confirmed bookings.

## Calculation

- The minimum margin is 30% on the net price, excluding VAT.
- The active pricing rule for the booking's tour supplies `vat_rate` and the existing gross rule price.
- A missing, non-finite, negative, or greater-than-one VAT rate makes quote generation fail with HTTP 422. No VAT rate is inferred.
- `minimum_price_net = direct_cost / (1 - 0.30)`.
- Currency amounts are rounded to two decimal places with `ROUND_HALF_UP`.
- `minimum_price_gross = minimum_price_net * (1 + vat_rate)`, rounded to two decimals.
- `recommended_price` is the greater of the existing rule's gross price and the minimum gross price.
- `final_price` stays null until the operator enters a chosen gross price in the explicit action/API request.
- A chosen final price is converted to net using the rule VAT rate before margin evaluation.

For a direct cost of THB 7,350.00 and VAT at 7%:

| Value | Amount |
| --- | ---: |
| Minimum net price | THB 10,500.00 |
| Minimum gross price | THB 11,235.00 |
| Existing gross rule price | THB 10,500.00 |
| Recommended gross price | THB 11,235.00 |

If an operator explicitly chooses THB 10,700.00 gross, the net price is THB 10,000.00. The quote is `below_margin` and has `manual_override_required` approval status.

## Verdict and approval fields

New quote breakdowns contain:

- `pricing_policy_version`
- `minimum_margin_rate` and `margin_basis`
- `vat_rate`
- net and gross equivalents for minimum, recommended, and selected final prices
- `margin_verdict`: `meets_margin`, `below_margin`, or `direct_cost_unknown`
- `approval_status`: `manual_override_required` for a below-margin selected final price, otherwise `not_required`

When direct cost is unknown, the quote records `direct_cost_unknown`, stores null for `minimum_price_net`, and uses zero in the legacy non-null `minimum_price` column. Consumers must use the explicit breakdown fields and verdict for policy-aware interpretation.

## API and persistence

`POST /pricing/quotes/{booking_code}/generate` is the explicit quote-generation action. The JSON body is optional:

```json
{"final_price_gross": 10700.00}
```

An empty body creates a quote with `final_price = null`. The endpoint locks the booking row with `SELECT ... FOR UPDATE`, refuses confirmed bookings with HTTP 409, requires an active tour pricing rule, validates its VAT rate, and inserts a new `pricing_quotes` snapshot in the same database transaction. It does not update existing quote rows or booking, payment, pricing-rule, or assignment data.

No schema migration is required. Existing top-level `minimum_price`, `recommended_price`, and `final_price` values remain readable as stored; all newly generated quote values in these legacy columns are gross customer prices. Net equivalents and policy metadata are in `breakdown`. Existing rows without policy metadata continue to serialize with null policy fields and are not rewritten.

The booking list and detail action display the latest quote's margin verdict and approval status. Booking Detail's existing operational margin formula, Dashboard margin formula, and operations summary formula remain unchanged.
