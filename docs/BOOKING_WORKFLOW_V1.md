# ThaiCulture Manager — Booking Workflow v1

Last updated: 2026-07-24

## Purpose

This document defines the canonical operational workflow of a booking inside ThaiCulture Manager.

Its role is to establish one consistent business process for how a booking moves from first contact to final completion.

This document is the reference point for:
- backend logic
- frontend behavior
- booking statuses
- required operational data
- relationship between booking, customer, operations, payments, and documents
- future integration with `thaiculture.tours`

## Core principle

**Booking = master operational record**

The booking is the central object of the system.

Everything else must connect to the booking:
- customer
- tour or service
- payments
- proformas
- invoices
- assignments
- operational costs
- status history
- future website-originated activity

No operational workflow should bypass the booking record.

## Booking purpose in the system

A booking represents the commercial and operational commitment between ThaiCulture Tours and the customer.

The booking must become the single place from which the team can understand:
- who the customer is
- what service was sold
- when the tour takes place
- how many guests are included
- what the financial status is
- which guide and driver are assigned
- whether required documents were generated
- whether the service is completed

## Booking lifecycle overview

Recommended lifecycle:

1. Inquiry
2. Offer Prepared
3. Awaiting Confirmation
4. Confirmed
5. Deposit Requested
6. Deposit Paid
7. Operations Ready
8. Balance Pending
9. Fully Paid
10. Tour Completed
11. Closed
12. Cancelled

This lifecycle may evolve later, but all implementations should stay aligned with one central status model.

## Canonical booking statuses

### Inquiry

A booking starts as an inquiry when the customer has shown interest but no confirmed agreement exists yet.

Typical state:
- customer identified or partially identified
- tour request known
- date may be tentative
- no final operational commitment yet
- no payment request yet

### Offer Prepared

The requested service has been priced and prepared internally.

Typical state:
- offer logic or draft proposal exists
- total amount is known or close to final
- internal review possible
- still not yet customer-confirmed

### Awaiting Confirmation

The offer has been shared and the team is waiting for customer confirmation.

Typical state:
- commercial terms are known
- customer response pending
- operational resources should not yet be fully locked unless necessary

### Confirmed

The customer has confirmed the booking.

Typical state:
- service scope accepted
- booking becomes active
- payment workflow may start
- operational preparation begins

### Deposit Requested

A payment request has been issued for the deposit or required advance payment.

Typical state:
- proforma may exist
- payment instructions sent
- booking remains confirmed but not yet financially secured

### Deposit Paid

The deposit has been received and matched to the booking.

Typical state:
- part of the financial commitment is secured
- operations may proceed with more confidence
- remaining balance may still be due later

### Operations Ready

The booking is operationally prepared.

Typical state:
- guide assigned or assignment path defined
- driver assigned if needed
- pickup / drop-off data confirmed
- core service logistics ready

### Balance Pending

The tour is confirmed and operationally active, but the remaining amount is still due.

Typical state:
- deposit may already be paid
- remaining balance not yet settled
- invoice or final payment request may still be pending

### Fully Paid

All expected customer payments have been received and confirmed.

Typical state:
- booking has no remaining balance
- invoice logic may be completed depending on policy
- operations may still be upcoming or already completed

### Tour Completed

The service has been delivered.

Typical state:
- tour date passed
- operational service completed
- final review or closing actions may remain

### Closed

The booking is fully completed from business perspective.

Typical state:
- service completed
- financial records completed
- documents completed
- no active pending action remains

### Cancelled

The booking will not proceed.

Typical state:
- service cancelled before completion
- payment and refund logic may need separate handling
- booking remains historically visible but inactive

## Status transition rules

A status must not be changed only by intuition.

Every transition should be based on a clear business condition.

Recommended logic:

- Inquiry -> Offer Prepared when the requested service is priced internally
- Offer Prepared -> Awaiting Confirmation when the offer is shared with the customer
- Awaiting Confirmation -> Confirmed when the customer explicitly accepts
- Confirmed -> Deposit Requested when advance payment must be collected
- Deposit Requested -> Deposit Paid when payment is confirmed
- Confirmed or Deposit Paid -> Operations Ready when required tour logistics are secured
- Deposit Paid or Operations Ready -> Balance Pending when remaining amount is still unpaid
- Balance Pending -> Fully Paid when total due is received
- Operations Ready or Fully Paid -> Tour Completed when the service is delivered
- Tour Completed -> Closed when all operational and financial follow-up is complete
- Any active state -> Cancelled when the booking is officially cancelled

## Required data at booking level

At minimum, each booking should support these fields:

- booking code
- booking status
- customer reference
- source
- tour / service reference
- travel date
- pickup time
- adults
- children
- infants
- total guests
- language
- selling price
- currency
- created at
- updated at

## Required relationships

Every valid booking should connect, directly or indirectly, to:

- one customer
- one tour or one custom service definition
- zero or more payments
- zero or more proformas
- zero or more invoices
- zero or more guide assignments
- zero or more driver assignments
- pickup and drop-off context when relevant

If a related entity does not yet exist, the booking should still remain the reference point where the missing relation is visible.

## Customer rule

A booking should never become a fully operational booking without a customer context.

At minimum, a valid operational customer context should include:
- display name
- reachable contact detail
- country, when relevant
- communication context if needed later

For website-generated workflows, the customer record should be created or matched as early as possible.

## Tour rule

A booking should always point to a tour, service package, or clearly defined custom trip.

If the service is custom, the booking still needs a structured service description and not only free-text notes.

## Assignment rule

Guide and driver assignments belong to the booking workflow, not outside it.

The system should allow:
- no assignment yet
- partial assignment
- fully assigned operations

Operational readiness should depend on whether the necessary assignments are completed for that booking type.

## Financial relationship rule

The booking workflow must remain aligned with the financial workflow document.

Operational status and financial status are related, but they are not the same thing.

Example:
- a booking can be operationally confirmed but financially pending
- a booking can be fully paid before the tour date
- a booking can be completed operationally while invoice follow-up is still pending

This is why financial logic must remain linked to the booking, but tracked separately.

## Document relationship rule

Documents must be connected to the booking.

This includes:
- proforma
- invoice
- customer-facing confirmations, if formalized later
- internal support documents, if added later

No document should exist without clear booking traceability.

## Website integration implications

For future integration with `thaiculture.tours`, the booking workflow should support two entry paths:

### Website-originated booking

The booking starts from the public website.

Typical path:
- website inquiry or booking request received
- customer and service data captured
- booking created in ThaiCulture Manager
- internal workflow continues from there

### Internal booking

The booking is created manually by the team.

Typical path:
- direct customer contact
- WhatsApp / email / phone booking
- manual entry into ThaiCulture Manager
- internal workflow continues in the same central system

Both paths must converge into the same booking model.

The website must not create a separate second workflow.

## Read-only vs editable logic

Not everything should be editable at all times.

Recommended principle:

- identity and source fields should be controlled
- operational notes may remain editable
- financial results should be derived from proper records, not overwritten manually
- status changes should follow workflow rules, not arbitrary edits

Detailed field-level permissions may be defined later, but the booking model should already be designed with controlled updates in mind.

## Backend implications

Backend implementation should support:
- a canonical booking status field
- booking detail responses that aggregate customer, payments, assignments, and documents
- controlled status transitions
- status history, if added later
- validation of required fields before key transitions
- website-originated and internal-originated booking creation paths

## Frontend implications

Frontend implementation should support:
- clear booking list with visible status
- detail page as the main operational cockpit for one booking
- visible relationship to customer, tour, payments, assignments, and invoices
- operational summary and financial summary shown separately
- clear missing-data states
- clear next-action states depending on booking stage

## Out of scope for v1

The following are not required for v1:
- full audit log
- complex approval workflows
- team-based permissions matrix
- automated rescheduling engine
- refund and credit-note workflow
- automated website self-service customer portal

## v1 decisions to confirm next

The next decisions to confirm after this document should be:
- exact final list of booking statuses
- whether Offer Prepared and Awaiting Confirmation remain separate
- whether Deposit Requested is a booking status or only a financial state
- what minimum fields are required before a booking can become Confirmed
- what minimum fields are required before a booking can become Operations Ready
- whether Closed is manual or computed

## Rule for implementation

No booking implementation should be considered final unless it follows this document and remains aligned with the financial workflow document.

If the operational business logic changes, this document must be updated before the implementation is treated as canonical.
