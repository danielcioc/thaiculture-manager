# ThaiCulture Manager — Project Status

Last updated: 2026-07-24

## Project purpose

ThaiCulture Manager is the internal operations system for ThaiCulture Tours.

Its role is to become the single source of truth for:
- customers
- bookings
- tours
- assignments
- guides
- drivers
- locations
- payments
- invoices
- operational and financial summaries

The final business goal is to integrate this internal system with the public website `thaiculture.tours`, so that website activity and internal operations are connected through one coherent data model.

## Final objective

The final objective is to build a stable, coherent back-office platform that:
- manages the full booking lifecycle from inquiry to completion
- links each booking to the correct customer, tour, payment records, assignments, and invoices
- supports operational tracking for guides, drivers, pickup/drop-off, and costs
- supports financial tracking for deposit, balance, payment status, and invoice logic
- becomes the internal foundation for future website integration with `thaiculture.tours`

## Original project direction

The project started from a functional and operational perspective, not from UI alone.

The original direction included:
- a Functional Specification document
- a Master Booking Database
- a Database Schema draft in PostgreSQL
- booking status flow
- booking ID standard
- document rules
- payment workflow logic
- invoice / proforma logic
- website integration planning

This means the system must be developed around real business workflows, not just lists and screens.

## Current state

The repository currently contains a full-stack project structure with:
- `backend/`
- `frontend/`
- `database/`
- `docs/`
- `scripts/`
- `docker-compose.yml`

The backend already has routers for:
- bookings
- customers
- dashboard
- tours
- assignments
- payments
- guides
- drivers
- locations
- invoices

The frontend already has a React application with:
- dashboard view
- list views for the main modules
- booking detail view
- invoice detail view
- API service layer
- shared types and utilities

Recent repair completed on 2026-07-24:
- invoices loading was restored in the frontend
- invoice navigation from the KPI card was restored
- local and remote git state are synced on `main`

## Confirmed working modules

As of 2026-07-24, the following areas were manually confirmed as working in the UI:
- Dashboard
- Bookings
- Booking detail
- Payments
- Invoices
- Invoice detail

This confirmation means the current build is usable as a working internal prototype.

## Core product model

The central model of the system should be:

**Booking = master operational record**

Each booking should connect, directly or indirectly, to:
- one customer
- one tour or service package
- payment records
- invoice / proforma records
- guide and driver assignments
- operational costs
- margin and summary data
- future website-originated booking data

This model must remain the reference point for all future development.

## Main gaps

The main gaps are not basic project setup anymore.

The current gaps are:
- a clearly written source-of-truth project status inside the repo
- a formal roadmap with milestones
- validation that all modules follow one consistent business model
- clarification of the financial workflow: deposit, balance, pending, paid, invoice, proforma
- clarification of the integration boundary with `thaiculture.tours`
- confirmation of what remains read-only and what must become editable

## Working principles from now on

From this point forward, work on the project should follow these principles:
- work coherently from the product model, not module by module without context
- save important decisions in the repository
- keep progress traceable through git and project docs
- define each milestone before implementation
- avoid fragmented fixes without updating project status
- treat website integration as a planned target, not as a separate unrelated project

## Active milestone

Current active milestone:

**Project alignment and product baseline**

Goal of this milestone:
- define where the project currently stands
- confirm the final objective
- confirm the core product model
- define the next correct implementation order

## Next implementation order

Recommended order from this point:

1. Create and maintain project status documentation
2. Define the canonical booking workflow
3. Define the canonical financial workflow
4. Audit each existing module against the core model
5. Fix missing or inconsistent data relationships
6. Define the future integration contract with `thaiculture.tours`
7. Only then expand features or public-facing integrations

## Immediate next milestone

The next concrete milestone after this document is:

**Booking Financial Workflow v1**

This milestone should define clearly:
- total amount
- deposit requested
- deposit paid
- balance due
- payment method
- payment status
- proforma generation moment
- invoice generation moment
- relationship between booking, payment, and invoice

## Current branch status

Current development branch: `main`

Status on 2026-07-24:
- local repository clean
- remote repository synced
- latest confirmed commit includes restored invoices loading and KPI navigation

## Rule for future work

Every meaningful development step should update at least one of the following:
- project status
- roadmap / milestone notes
- implementation code
- git history

This project should now be treated as a structured product build, not as isolated fixes.
