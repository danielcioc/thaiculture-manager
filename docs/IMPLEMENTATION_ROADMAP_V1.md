# ThaiCulture Manager — Implementation Roadmap v1

Last updated: 2026-07-24

## Purpose

This document defines the implementation order for ThaiCulture Manager after the initial product baseline was established.

Its purpose is to translate the current canonical project documents into an execution sequence that is clear, realistic, and traceable.

This roadmap does not redefine product logic.

Instead, it defines the order in which the existing product logic should be validated, implemented, aligned, and extended.

## Roadmap principle

Implementation must follow the product model, not isolated module convenience.

This means:
- booking remains the master operational record
- financial logic remains linked to booking
- website integration remains a controlled future target
- implementation order follows business dependencies
- each milestone should reduce ambiguity, not add new parallel logic

## Current baseline

At the time of this roadmap:
- the project status baseline exists
- the booking workflow baseline exists
- the booking financial workflow baseline exists
- the website integration scope baseline exists
- dashboard, bookings, booking detail, payments, invoices, and invoice detail were already manually confirmed as working in the UI

This means the project already has a usable prototype and enough documented structure to move into systematic implementation alignment.

## Execution model

The roadmap should be executed in phases.

Each phase should have:
- a clear scope
- a clear completion condition
- a small number of deliverables
- a visible connection to the canonical documents

No phase should be treated as complete if it introduces behavior that contradicts the existing v1 documents.

## Phase 1 — Product baseline stabilization

### Goal

Confirm that the project now has one canonical product direction and one canonical document set.

### Deliverables

- `PROJECT_STATUS.md`
- `BOOKING_WORKFLOW_V1.md`
- `BOOKING_FINANCIAL_WORKFLOW_V1.md`
- `WEBSITE_INTEGRATION_SCOPE_V1.md`
- this roadmap document

### Completion condition

Phase 1 is complete when these documents exist, are committed, and are treated as the official reference for implementation decisions.

## Phase 2 — Booking model audit

### Goal

Verify that the current backend and frontend actually reflect the booking model defined in the canonical workflow documents.

### Scope

Audit the booking model across:
- backend schema
- API responses
- frontend detail view
- related entities
- displayed fields
- derived summaries

### Deliverables

- a checked list of current booking fields
- a checked list of missing booking fields
- confirmation of how booking relates to customer, tour, payments, invoices, assignments, and locations
- a short written audit result saved in docs or decisions notes

### Main questions

- Does the booking record already hold the required core fields?
- Are status fields coherent?
- Are customer and tour references reliable?
- Is the detail page really acting as the operational cockpit of a booking?
- Are derived totals or summaries being computed consistently?

### Completion condition

Phase 2 is complete when the current booking implementation is fully mapped against `BOOKING_WORKFLOW_V1.md` and the gaps are written down clearly.

## Phase 3 — Financial model audit

### Goal

Verify that the implemented payment and invoice behavior matches the canonical financial workflow.

### Scope

Audit:
- payment records
- amount fields
- payment statuses
- booking-level financial status
- proforma logic
- invoice logic
- relationships between booking, payment, and invoice

### Deliverables

- a gap list between current implementation and `BOOKING_FINANCIAL_WORKFLOW_V1.md`
- confirmation of which financial fields already exist
- confirmation of which fields are missing, overloaded, or ambiguous
- confirmation of whether current UI language matches the intended business logic

### Main questions

- Are total, deposit, paid, and balance represented correctly?
- Is payment status separated from booking status?
- Is invoice logic independent but linked to booking?
- Is proforma logic already represented, partially represented, or absent?
- Is the current UI showing operational and financial state separately enough?

### Completion condition

Phase 3 is complete when financial behavior is clearly mapped and all mismatches are documented.

## Phase 4 — Canonical status alignment

### Goal

Align booking and financial statuses so the system stops using unclear or overlapping state logic.

### Scope

Define and implement the canonical status structure for:
- booking lifecycle status
- payment status
- booking-level financial status

### Deliverables

- final v1 status list used in code
- mapping from any old status values to canonical values
- backend validation rules
- frontend display rules for status badges, labels, and summaries

### Main questions

- Which statuses become official in code?
- Which older statuses must be deprecated?
- Which states are computed and which are editable?
- Which transitions must be restricted?

### Completion condition

Phase 4 is complete when the codebase uses one coherent status model across backend and frontend.

## Phase 5 — Relationship integrity fixes

### Goal

Fix missing or inconsistent links between the booking record and related entities.

### Scope

Focus on:
- customer linkage
- tour linkage
- payment linkage
- invoice linkage
- assignment linkage
- location linkage
- source/origin metadata

### Deliverables

- backend model adjustments where needed
- API response alignment
- frontend relationship visibility fixes
- explicit handling for missing related data

### Main questions

- Can every booking be traced clearly to its related entities?
- Are related records reachable from booking detail?
- Are there places where data exists but is not linked cleanly?
- Are there fields that should be references but are still plain text?

### Completion condition

Phase 5 is complete when the booking record behaves as the real central reference point of the product.

## Phase 6 — Booking detail as operational cockpit

### Goal

Turn the booking detail page into the central operational screen for one booking.

### Scope

The booking detail page should clearly present:
- customer context
- booking status
- operational details
- guest and date details
- payment summary
- invoice / proforma context
- guide / driver assignment context
- next actions or missing data

### Deliverables

- improved booking detail layout and data grouping
- separate operational summary and financial summary
- clear missing-data states
- clearer progression from inquiry to completion

### Main questions

- Can the team understand the whole booking from one page?
- Are operational and financial concerns visually separated?
- Are next actions visible?
- Is the page useful even when data is incomplete?

### Completion condition

Phase 6 is complete when booking detail works as the main human-facing cockpit for operations.

## Phase 7 — Data entry and edit rules

### Goal

Clarify what users can edit, what should be derived, and what should be controlled through structured transitions.

### Scope

Define:
- editable booking fields
- controlled status fields
- derived financial fields
- internal notes vs structured fields
- rules for manual corrections

### Deliverables

- explicit editability rules
- backend validation updates
- frontend form behavior aligned with the rules
- written decision record for exceptional manual overrides

### Main questions

- Which fields should never be freely editable?
- Which values should be computed?
- Which changes require validation?
- Which internal notes remain flexible text?

### Completion condition

Phase 7 is complete when data editing supports business control instead of accidental inconsistency.

## Phase 8 — Website integration preparation

### Goal

Prepare the manager so website integration can be added without distorting the internal model.

### Scope

Prepare for:
- website-originated inquiry or booking-request input
- source metadata
- customer matching rules
- internal review flow before final confirmation
- future API contract boundaries

### Deliverables

- internal source field or source model confirmation
- booking intake model for website-originated requests
- backend endpoint planning notes
- clear separation between public input and internal confirmation

### Main questions

- Will website submissions create inquiries or draft bookings?
- How is website origin stored?
- How is customer matching handled?
- What must happen before a website-originated request becomes a real confirmed booking?

### Completion condition

Phase 8 is complete when the manager is structurally ready to receive website-originated data without duplicating business logic.

## Phase 9 — Website integration v1

### Goal

Implement the first controlled integration between `thaiculture.tours` and ThaiCulture Manager.

### Scope

Version 1 should remain conservative:
- website sends inquiry or booking-request data
- manager validates and continues the workflow
- no public ownership of booking lifecycle
- no public ownership of invoice or payment logic

### Deliverables

- first integration endpoint(s)
- validated input contract
- source tagging for website-created records
- internal workflow continuation from website-created records

### Completion condition

Phase 9 is complete when the website can create structured internal intake records safely and consistently.

## Phase 10 — Post-integration refinement

### Goal

Improve usability, automation, and visibility after the integration model is stable.

### Scope

Possible later work:
- better dashboards
- better assignment workflow
- more detailed financial summaries
- controlled customer-facing status visibility
- document visibility for customers
- automation and notifications

### Completion condition

Phase 10 starts only after the internal model and v1 website integration are stable.

## Priority order summary

Recommended practical order:

1. Confirm product baseline documents
2. Audit booking model
3. Audit financial model
4. Align statuses
5. Fix data relationships
6. Improve booking detail as cockpit
7. Define editability and validation rules
8. Prepare website intake model
9. Implement website integration v1
10. Refine and automate later

## What should not happen

The following should be avoided:
- building website integration before internal model alignment
- adding payment logic to the website independently
- introducing new statuses without updating canonical docs
- adding UI fields that have no clear product meaning
- solving module-specific issues without checking the master booking model
- creating parallel logic for manual bookings and website bookings

## Immediate next implementation step

The next practical implementation step after this roadmap should be:

**Booking model audit**

This is the correct next step because the project already has enough written direction, but still needs validation that the actual codebase matches the intended product model.

## Rule for execution

Every important implementation step should produce at least one of the following:
- code changes
- a committed document update
- a decisions note
- a small audit result
- a git checkpoint

No milestone should remain only verbal.

## Alignment requirement

This roadmap is valid only while it remains aligned with:
- `PROJECT_STATUS.md`
- `BOOKING_WORKFLOW_V1.md`
- `BOOKING_FINANCIAL_WORKFLOW_V1.md`
- `WEBSITE_INTEGRATION_SCOPE_V1.md`

If any of those documents changes materially, this roadmap must be updated as well.
