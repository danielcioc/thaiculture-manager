# ThaiCulture Manager — Project State

## Purpose
ThaiCulture Manager is an internal operations dashboard for managing tour bookings, customers, tours, payments, guides, drivers, assignments, and operational margins.

## Current stack
- PostgreSQL 16 in Docker
- FastAPI backend with psycopg
- React + TypeScript + Vite frontend
- Local orchestration via docker-compose

## Local runtime
- Postgres container: tct_postgres
- Backend container: tct_backend
- Postgres host port: 5433
- Backend host port: 8000
- Backend DB URL inside Docker: postgresql://tct_admin:tct_local_password@postgres:5432/thaiculture_manager
- DB init folder: database/init
- Main schema file: database/init/001_schema.sql

## Backend status
Backend is already implemented and includes routers for:
- bookings
- customers
- payments
- dashboard
- tours
- locations
- guides
- drivers
- assignments

Backend health and DB connectivity were confirmed from local terminal.

## Frontend status
Frontend is already implemented as a dark dashboard UI with:
- dashboard overview
- bookings list
- booking detail view
- customers list
- tours list
- assignments list
- payments list
- guides list
- drivers list
- locations list
- mobile navigation drawer

## Seed/demo data confirmed
Local database currently contains at least:
- 1 booking
- 1 customer
- 2 payments
- 1 tour
- 1 location
- 1 guide
- 1 driver
- 2 assignments

Primary demo booking:
- Booking code: TCT-2026-000001
- Customer: Thomas Richter
- Tour: Ayutthaya Sunset & Night Temples
- Guests: 8
- Guide language: DE
- Selling price: 14900 THB
- Payment status: Partially Paid
- Operations margin: 7900 THB
- Margin percent: 53.02%

## Current interpretation of project stage
Project is not at the schema-design stage anymore.
It is already an MVP-level internal operations product with a working local stack, real API routes, and seeded test data.

## Current validated booking detail state
The backend full booking detail endpoint was validated against the real seeded booking TCT-2026-000001.
The response currently returns booking, payments, payment_summary, assignments, and operations_summary correctly on real data.
A contract gap remains: payment_summary currently exposes payment_status but does not yet expose booking_financial_status required by the canonical financial workflow.
