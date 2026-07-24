# ThaiCulture Manager — Website Integration Scope v1

Last updated: 2026-07-24

## Purpose

This document defines the integration scope between the public website `thaiculture.tours` and the internal system ThaiCulture Manager.

Its purpose is to establish one clear boundary between:
- public website behavior
- internal back-office behavior
- shared data
- booking creation logic
- financial workflow ownership
- future API integration rules

This document is the reference point for all future website integration work.

## Core principle

**ThaiCulture Manager is the source of truth.**

The website `thaiculture.tours` is the public-facing layer.

ThaiCulture Manager is the internal operational and financial system.

The website may collect, display, or trigger data, but the canonical operational record must live inside ThaiCulture Manager.

The website must not create a second independent business logic for bookings, customers, payments, or invoices.

## System roles

### Website role

The public website should handle:
- tour presentation
- public content pages
- inquiry forms
- booking request forms
- lead capture
- customer-facing information
- limited customer journey steps, if introduced later

The website exists to attract, inform, and initiate contact or booking intent.

### ThaiCulture Manager role

ThaiCulture Manager should handle:
- internal booking records
- customer records
- booking status lifecycle
- payment tracking
- proforma logic
- invoice logic
- assignments
- operational readiness
- internal notes and business control
- financial and operational summaries

ThaiCulture Manager exists to operate the business after lead or booking intent is received.

## Integration objective

The integration objective is not to merge website and manager into one unclear system.

The objective is to connect them cleanly so that:
- website-originated requests become structured internal records
- the internal team can continue work inside ThaiCulture Manager
- the business uses one coherent booking and payment logic
- future automation can be added without duplicating workflows

## Supported entry paths

The product should support two valid booking entry paths:

### 1. Website-originated path

A customer interacts with `thaiculture.tours`.

Typical sequence:
1. Customer reads the website.
2. Customer submits an inquiry or booking request.
3. Website captures the submitted data.
4. ThaiCulture Manager receives or creates the booking context.
5. Internal team continues the operational workflow inside ThaiCulture Manager.

### 2. Internal path

A customer contacts the team directly.

Typical sequence:
1. Customer contacts ThaiCulture Tours via WhatsApp, email, phone, or direct message.
2. Internal team creates the booking manually in ThaiCulture Manager.
3. Workflow continues in the same booking system.

Both paths must converge into the same central booking model.

## Canonical ownership of data

The following ownership model should apply.

### Website-owned concerns

The website may own:
- public content
- tour descriptions shown publicly
- marketing pages
- SEO content
- website form UI
- temporary session state, if introduced later

### Manager-owned concerns

ThaiCulture Manager must own:
- final booking record
- booking status
- customer master record
- financial records
- proformas
- invoices
- assignments
- operational summaries
- internal notes
- final source-of-truth reporting

### Shared concerns

Some data may be shared between website and manager, but ownership still needs to be explicit.

Examples of shared data:
- tour information
- customer identity data submitted via forms
- booking request details
- travel date and guest count
- service preferences

Shared does not mean duplicated business logic.

## Booking creation model

Version 1 recommendation:

A website submission should not directly create a fully confirmed booking by default.

Instead, it should create one of these:
- an inquiry record that becomes a booking in ThaiCulture Manager
- a draft booking / booking request record
- a lead that the internal team validates before final booking confirmation

This protects data quality and avoids bad or incomplete public input becoming operational truth without review.

## Recommended v1 rule

Recommended v1 operational rule:

- website creates inquiry or booking-request data
- ThaiCulture Manager creates or confirms the canonical booking record
- booking status transitions happen in ThaiCulture Manager
- financial workflow begins only after internal confirmation or controlled acceptance

This is safer than allowing the public website to generate final operational states directly.

## Customer creation rule

When customer data arrives from the website:
- the system should create or match a customer record
- duplicate customer creation should be minimized
- the internal manager should remain the place where customer truth is reviewed and maintained

The website may collect customer data, but ThaiCulture Manager should hold the authoritative customer record.

## Tour data rule

Tour content may appear on the public website, but operational booking usage must align with the manager's internal model.

This means:
- public tour pages may be marketing-oriented
- ThaiCulture Manager must still map the selected service to a structured internal tour or service definition
- custom trips must still be represented in a structured way internally

## Financial ownership rule

The website must not own the financial logic.

ThaiCulture Manager must remain responsible for:
- deposit logic
- payment request logic
- payment status
- proforma generation
- invoice generation
- balance due logic

If the website later shows payment-related information, it should display manager-derived state, not invent a separate financial workflow.

## Payment collection rule

Version 1 recommendation:

The website may eventually display payment instructions or trigger payment steps, but actual payment state must still be recorded and controlled in ThaiCulture Manager.

This means:
- the website can be an entry point or customer-facing view
- ThaiCulture Manager remains the record of what was requested, paid, pending, or overdue

## Status ownership rule

Booking status must be controlled by ThaiCulture Manager.

The website may show simplified customer-facing states later, but it should not become the canonical controller of:
- confirmed
- deposit requested
- deposit paid
- operations ready
- fully paid
- completed
- cancelled

These are internal operational states and must remain centralized.

## Document ownership rule

The website must not generate independent document logic outside the manager.

ThaiCulture Manager should remain responsible for:
- proforma records
- invoice records
- final traceability of documents to bookings

The website may later expose customer-facing download or viewing functionality, but the document source must remain the manager.

## Website-to-manager data flow

The website should be able to send at minimum:
- customer name
- customer contact details
- selected tour or requested service
- travel date
- guest counts
- pickup preference, if collected
- language preference, if collected
- notes or special requests
- source metadata indicating website origin

This data should enter ThaiCulture Manager in a controlled format.

## Manager-to-website data flow

ThaiCulture Manager may later provide the website with:
- available structured tour data
- booking-request acknowledgement status
- limited customer-facing booking state
- payment request visibility, if approved later
- document availability, if approved later

Any website display of business-critical information should come from manager-owned data.

## Integration boundary for v1

For version 1, the integration boundary should stay conservative.

Recommended v1:
- website sends inquiry / booking request data into ThaiCulture Manager
- ThaiCulture Manager performs validation and operational continuation
- no public website editing of internal booking lifecycle
- no public website ownership of payment or invoice logic

This keeps the first integration stable and low-risk.

## API direction

The integration should eventually be implemented through explicit API contracts.

Likely categories:
- website -> manager inquiry / booking request endpoint
- manager -> website structured tour data endpoint, if needed
- manager -> website customer-facing status endpoint, only if later approved
- manager -> website document visibility endpoint, only if later approved

API design should follow the ownership rules in this document.

## Security and control principles

The website is public. ThaiCulture Manager is internal.

This means:
- internal records must not be exposed automatically
- customer-facing access must be limited and intentional
- manager-side validation must exist for website-originated data
- sensitive financial and internal operational data should remain protected by default

## Out of scope for v1

The following are not required for v1:
- full customer portal
- self-service booking editing by customers
- self-service invoice management
- automatic payment gateway reconciliation
- full bidirectional real-time sync
- website-controlled booking lifecycle changes

## v1 decisions to confirm next

The next decisions to confirm after this document should be:
- whether website submissions create inquiries or draft bookings
- whether the website should expose any customer-facing booking status at all in v1
- whether tour inventory or availability will be managed manually or from manager data
- whether website payment steps are included in v1 or postponed
- what authentication model would be used later for any customer-facing booking view

## Rule for implementation

No website integration work should be considered final unless it follows this document and remains aligned with:
- `PROJECT_STATUS.md`
- `BOOKING_WORKFLOW_V1.md`
- `BOOKING_FINANCIAL_WORKFLOW_V1.md`

If the integration model changes, this document must be updated before implementation is treated as canonical.
