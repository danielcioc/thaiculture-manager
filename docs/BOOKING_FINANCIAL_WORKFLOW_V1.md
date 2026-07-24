# ThaiCulture Manager — Booking Financial Workflow v1

Last updated: 2026-07-24

## Purpose

This document defines the canonical financial workflow for a booking inside ThaiCulture Manager.

Its goal is to establish one clear business logic for:
- booking total
- deposit request
- deposit payment
- balance due
- payment status
- proforma logic
- invoice logic
- relationship between booking, payment, and invoice

This document is the reference point for future backend, frontend, and website integration work.

## Core principle

**Booking = master operational and financial record**

The booking is the parent record.

Payments, proformas, and invoices must always belong to a booking, either directly or through a controlled business relationship.

No financial document should exist without a valid booking context.

## Financial entities

The financial workflow is built around these entities:

### Booking

The booking contains the commercial agreement with the customer.

At minimum, it should define:
- booking code
- customer
- tour / service
- travel date
- number of guests
- agreed selling price
- currency
- booking status

### Payment

A payment record tracks money requested or received in relation to a booking.

A payment may represent:
- deposit request
- deposit payment
- full payment
- balance payment
- refund, if introduced later

Each payment record must be linked to one booking.

### Proforma

A proforma is a payment request document issued before final tax invoice logic.

It is used to request money from the customer based on the booking agreement.

A proforma should normally reflect:
- booking reference
- customer details
- service description
- amount requested
- payment instructions
- issue date
- due date
- payment reference or QR / transfer context

### Invoice

An invoice is the formal billing document associated with the booking.

It may be generated:
- after payment
- after service confirmation
- after service completion

The exact operational rule must be controlled centrally and not handled differently per booking without a written exception.

## Canonical amounts

Each booking must support the following financial values:

- total amount
- deposit requested
- deposit paid
- balance due
- total paid
- remaining amount

### Definitions

**Total amount**  
The full agreed customer price for the booking.

**Deposit requested**  
The amount requested from the customer before the tour or before final confirmation, according to the business rule.

**Deposit paid**  
The amount already received and matched to the booking.

**Balance due**  
The amount still due after subtracting paid amounts from the total.

**Total paid**  
The sum of all confirmed incoming payments linked to the booking.

**Remaining amount**  
The unpaid portion still outstanding on the booking.

## Calculation rules

The standard financial logic should be:

- total paid = sum of confirmed paid payment records
- remaining amount = total amount - total paid
- balance due = total amount - deposit paid, unless full payment already exists
- deposit outstanding = deposit requested - deposit paid

If partial or multiple payments exist, calculations must always be derived from payment records, not handwritten assumptions.

## Payment methods

The system should support at minimum:

- bank transfer
- Thai QR payment
- cash
- card, if introduced later
- other manual method, if explicitly recorded

Every payment record should store:
- method
- amount
- currency
- reference
- status
- paid at
- notes

## Payment statuses

At minimum, the workflow should support these statuses:

- draft
- requested
- pending
- paid
- partially_paid
- overdue
- cancelled

### Status meaning

**draft**  
Created internally but not yet sent to the customer.

**requested**  
Payment request exists and has been sent or prepared for sending.

**pending**  
Waiting for customer transfer or confirmation.

**paid**  
Payment fully received and confirmed.

**partially_paid**  
Only part of the expected amount has been received.

**overdue**  
Payment due date passed and money not received.

**cancelled**  
Payment request was cancelled or replaced.

## Booking-level financial statuses

In addition to payment-level statuses, each booking should expose a financial summary status.

Recommended booking financial statuses:
- unpaid
- deposit_requested
- deposit_paid
- partially_paid
- paid
- overdue

These should be computed from the underlying payment records and due dates.

## Proforma generation rule

A proforma should be generated when:
- the booking is confirmed or ready for payment request
- money needs to be requested before service delivery
- the team wants to issue a formal payment request to the customer

A proforma should not be treated as final proof of payment.

It is a request document, not the payment itself.

## Invoice generation rule

The invoice rule must be explicit and consistent.

Version 1 recommendation:
- proforma is generated when requesting payment
- invoice is generated after payment is confirmed, or according to final accounting policy
- invoice must always remain traceable back to the booking and customer

If accounting rules later require a different timing, that rule must be updated here first before implementation changes.

## Standard workflow

Recommended standard flow:

1. Booking is created.
2. Total amount is agreed.
3. Deposit amount is defined, if required.
4. Proforma is generated for deposit or full amount.
5. Payment request is sent to customer.
6. Payment is received and recorded.
7. Booking financial summary is updated.
8. Balance is requested later, if applicable.
9. Final invoice is generated according to the accounting rule.
10. Booking reaches paid status when total paid matches total amount.

## Example case

Example based on the original business logic discussed in the project:

- total amount: 14,900 THB
- deposit requested: 3,000 THB
- balance due after deposit: 11,900 THB
- payment method: transfer or Thai QR
- payment status: pending until confirmed, then paid

This kind of rule should be implemented through structured payment records, not informal notes.

## Relationship model

The intended relationship model is:

- one booking can have many payment records
- one booking can have one or more proforma records over time, if versioning is needed later
- one booking can have one or more invoice records, depending on final business and accounting needs
- every invoice and proforma must always reference the booking
- every payment record must always reference the booking

No orphan financial records should exist.

## Backend implications

Backend implementation should support:
- booking financial summary fields or computed summary response
- payment records linked to booking
- proforma and invoice endpoints linked to booking
- status calculation logic based on stored payment records
- consistent currency handling
- traceable references for transfer and QR payments

## Frontend implications

Frontend implementation should support:
- booking-level financial summary
- visible total / paid / remaining values
- payment history per booking
- payment status badges
- proforma and invoice visibility from the booking detail
- clear difference between requested, pending, and paid states

## Website integration implications

For future integration with `thaiculture.tours`, this workflow means:

- a website booking must eventually create or map to one booking record in ThaiCulture Manager
- payment requests triggered from website-originated bookings must still follow the same internal payment logic
- proforma and invoice generation rules must remain centralized in ThaiCulture Manager
- the website should not invent a second financial logic outside the manager

ThaiCulture Manager remains the source of truth.

## Out of scope for v1

The following may be added later, but are not part of v1:
- refunds
- credit notes
- split invoices by legal entity
- multi-currency accounting logic
- automated accounting exports
- automated payment gateway reconciliation

## v1 decisions to confirm next

The next confirmation step after this document should be:

- whether deposit is mandatory, optional, or conditional
- when invoice is generated in the real business process
- whether proforma numbering needs its own series
- whether invoices are one per booking or can be multiple
- whether the website will create bookings directly or send leads first

## Rule for implementation

No backend or frontend financial implementation should be considered final unless it follows this document.

If business rules change, this document must be updated before code changes are treated as canonical.
