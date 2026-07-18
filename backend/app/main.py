from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import get_connection
from app.routers import (
    bookings,
    customers,
    payments,
    dashboard,
    tours,
    locations,
    guides,
    drivers,
    assignments,
    invoices,
)

app = FastAPI(title="ThaiCulture Manager API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(bookings.router)
app.include_router(customers.router)
app.include_router(payments.router)
app.include_router(dashboard.router)
app.include_router(tours.router)
app.include_router(locations.router)
app.include_router(guides.router)
app.include_router(drivers.router)
app.include_router(assignments.router)
app.include_router(invoices.router)


@app.get("/health")
def health_check():
    return {"status": "ok", "service": "ThaiCulture Manager API"}


@app.get("/db-check")
def db_check():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM bookings;")
            bookings_count = cur.fetchone()[0]

            cur.execute("SELECT COUNT(*) FROM customers;")
            customers_count = cur.fetchone()[0]

            cur.execute("SELECT COUNT(*) FROM payments;")
            payments_count = cur.fetchone()[0]

            cur.execute("SELECT COUNT(*) FROM tours;")
            tours_count = cur.fetchone()[0]

            cur.execute("SELECT COUNT(*) FROM locations;")
            locations_count = cur.fetchone()[0]

            cur.execute("SELECT COUNT(*) FROM guides;")
            guides_count = cur.fetchone()[0]

            cur.execute("SELECT COUNT(*) FROM drivers;")
            drivers_count = cur.fetchone()[0]

            cur.execute("SELECT COUNT(*) FROM assignments;")
            assignments_count = cur.fetchone()[0]

    return {
        "status": "ok",
        "database": "connected",
        "bookings_count": bookings_count,
        "customers_count": customers_count,
        "payments_count": payments_count,
        "tours_count": tours_count,
        "locations_count": locations_count,
        "guides_count": guides_count,
        "drivers_count": drivers_count,
        "assignments_count": assignments_count,
    }
