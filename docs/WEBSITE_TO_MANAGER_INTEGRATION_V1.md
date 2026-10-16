# Website to ThaiCulture Manager Integration V1

Updated: 2026-10-16

## Scope and operating model

The local V1 integration uses the existing static website as the presentation layer and ThaiCulture Manager as the source for tour availability, quote calculation, and inquiry records. A website submission creates a booking with operational status `Inquiry`; it does not confirm the tour, collect payment, or generate a proforma.

The integration is opt-in behind `WEBSITE_INTEGRATION_ENABLED`, which defaults to `false`. The local-only adapter in `scripts/local_website_adapter.py` serves the website from its existing directory, injects the demo form into one selected page, and proxies only the three public website API paths. It binds to loopback and forwards no authorization credentials. The static website files are not modified.

For staging, the approved topology is a same-origin reverse proxy for `/api/website/*`. The static site can therefore use relative API paths without CORS. Configure `CORS_ALLOWED_ORIGINS` as empty for this route; if the Manager staff UI is served on a separate origin, configure its exact origin separately. Keep `WEBSITE_INTEGRATION_ENABLED=false` by default, and enable it only for an approved staging validation. Production remains disabled pending a separate release decision.

## API contract

| Method and path | Purpose | Success |
| --- | --- | --- |
| `GET /api/website/catalog` | Lists active canonical tours that have an active pricing rule approved for customer quotes, with website slug and supported guest bounds. | `200` |
| `POST /api/website/pricing` | Resolves the website slug to its canonical tour and calculates the quote from the active Manager pricing rule. | `201` |
| `POST /api/website/bookings` | Consumes a matching, unexpired quote and creates a customer/booking/pricing snapshot atomically. Requires `Idempotency-Key` UUID. | `201` |

Pricing errors use `404` when no active approved rule or tour mapping exists, `409` when the mapping is ambiguous, and `422` for invalid input, unsupported guest counts/currency, missing or invalid VAT, or a rule that is not approved. Booking submission uses `404` for an unknown quote and `409` for an expired/consumed/mismatched quote, idempotency payload conflict, or in-progress original request. Pydantic request validation returns `422`.

## Pricing decisions

- The active approved Manager rule is the only price source. The website must not supply or override a price.
- `group_size_basis=per_booking` uses the configured fixed rule price once. `per_person` multiplies the same configured rule calculation by total guests; adult/child-specific rates are not invented.
- The existing `minimum-margin-30-v1` calculation and the rule's VAT rate are reused. The API rejects missing/invalid VAT and currency mismatch.
- Extras are rejected while no active configured extra-price model exists. The current site widget sends an empty extras list.
- Quote previews expire after 30 minutes and preserve a pricing-rule snapshot in `website_quote_previews`.
- The submitted booking starts with `selling_price=0`; the customer-facing quote is stored in `pricing_quotes` with `final_price=NULL`. Internal staff must review and set the booking's accepted price through the existing workflow.

## Inquiry and idempotency

Website submissions create `source=Website`, `status=Inquiry`, a canonical tour/customer link, and a pricing quote snapshot in one transaction. A request's `Idempotency-Key` is unique. Reusing the key with the same canonical payload returns the original response; reusing it with a different payload returns `409`. A consumed quote cannot create another booking.

The key is generated in browser memory for the request and retained for retry while the form remains open. Transport failures tell the customer to retry without changing the inputs. A fresh quote is required after changing quote inputs. The API remains the final duplicate guard.

## Local execution

For the current isolated E2E session, the website is served at `http://127.0.0.1:4173/` by `scripts/local_website_adapter.py`; the isolated Manager API is at `http://127.0.0.1:18082/`. The local database uses a dedicated disposable Compose project, network, volume, and host port. These are local test resources and do not identify staging or production.

Example adapter invocation:

```sh
python3 scripts/local_website_adapter.py \
  --website-root "/Users/danielcioc/Desktop/thaiculture.tours" \
  --backend-url http://127.0.0.1:18082 \
  --demo-page en/ayutthaya-5-sights-tour.html \
  --port 4173
```

The backend feature flag must be enabled explicitly for local testing. Production exposure requires a separate security/release review, suitable abuse controls, monitoring, retention policy for inquiry PII, and explicit operator configuration. Never place service secrets or JWTs in public website code, Git, or browser storage.

The tracked `frontend/.env.example` standardizes the Manager frontend's public API URL as `VITE_API_BASE_URL`; `VITE_API_BASE` remains a compatibility fallback. Vite variables are bundled into browser code and must contain public configuration only, never secrets. The static website widget uses same-origin relative paths and does not read either Vite variable.

## Known V1 limits

- The public API is not an authentication mechanism and must only be exposed intentionally.
- No extras pricing, adult/child-specific tariffs, payment collection, proforma generation, or automatic confirmation is implemented.
- The local demo widget currently uses THB and one selected page. The API catalog can return other tours with approved rules.
- Website source content may show a marketing price or text that differs from current Manager pricing. The live quote shown by this integration comes from Manager; the original static content remains unchanged.
