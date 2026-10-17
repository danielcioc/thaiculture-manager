import asyncio
import unittest
from datetime import date, timedelta
from unittest.mock import patch
from uuid import UUID

from pydantic import ValidationError

from app import database
from app.config import Settings
from app.routers import website
from app.routers.website import WebsiteBookingRequest, WebsiteCustomer, WebsitePricingRequest
from app.website_security import WebsiteProtectionMiddleware, website_rate_limits


class WebsiteRequestValidationTests(unittest.TestCase):
    def test_customer_fields_have_server_side_length_limits(self):
        with self.assertRaises(ValidationError):
            WebsiteCustomer(name="N" * 256, email="guest@example.com", phone="1")
        with self.assertRaises(ValidationError):
            WebsiteCustomer(name="Guest", email="guest@example.com", phone="1" * 51)
        with self.assertRaises(ValidationError):
            WebsiteBookingRequest(
                quote_id=UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"),
                date=date.today() + timedelta(days=30), adults=1, currency="THB",
                customer=WebsiteCustomer(name="Guest", email="guest@example.com"),
                notes="N" * 2001,
            )

    def test_extras_count_is_bounded(self):
        with self.assertRaises(ValidationError):
            WebsitePricingRequest(
                website_tour_id="tour", date=date.today() + timedelta(days=30),
                adults=1, currency="THB", extras=[f"x{i}" for i in range(21)],
            )

    def test_website_protection_limits_are_configurable(self):
        settings = Settings(
            _env_file=None,
            database_url="synthetic-dsn",
            website_catalog_requests_per_minute=44,
            website_pricing_requests_per_minute=12,
            website_bookings_requests_per_minute=3,
            website_max_body_bytes=8192,
        )
        self.assertEqual(website_rate_limits(settings), {"catalog": 44, "pricing": 12, "bookings": 3})
        self.assertEqual(settings.website_max_body_bytes, 8192)


class WebsiteProtectionMiddlewareTests(unittest.TestCase):
    def run_request(self, middleware, *, method="POST", path="/api/website/pricing", body=b"{}", headers=None, response_status=200):
        sent = []
        incoming = [{"type": "http.request", "body": body, "more_body": False}]

        async def receive():
            return incoming.pop(0) if incoming else {"type": "http.disconnect"}

        async def send(message):
            sent.append(message)

        async def app(scope, receive, send):
            if method == "POST":
                request = await receive()
                self.assertEqual(request.get("body", b""), body)
            await send({"type": "http.response.start", "status": response_status, "headers": []})
            await send({"type": "http.response.body", "body": b"{}", "more_body": False})

        scope = {
            "type": "http", "method": method, "path": path,
            "headers": headers if headers is not None else [(b"content-length", str(len(body)).encode())],
            "client": ("198.51.100.24", 12345),
        }
        asyncio.run(middleware(scope, receive, send))
        start = next(item for item in sent if item["type"] == "http.response.start")
        return start, b"".join(item.get("body", b"") for item in sent if item["type"] == "http.response.body")

    def make_middleware(self, *, limit=10, body_limit=128, response_status=200):
        async def app(scope, receive, send):
            await send({"type": "http.response.start", "status": response_status, "headers": []})
            await send({"type": "http.response.body", "body": b"{}", "more_body": False})

        return WebsiteProtectionMiddleware(
            app,
            body_limit_bytes=body_limit,
            requests_per_minute={"catalog": limit, "pricing": limit, "bookings": limit},
        )

    def test_oversized_body_returns_413_before_handler(self):
        routes = (
            ("GET", "/api/website/catalog"),
            ("POST", "/api/website/pricing"),
            ("POST", "/api/website/bookings"),
        )
        for method, path in routes:
            with self.subTest(path=path):
                middleware = self.make_middleware(body_limit=8)
                start, body = self.run_request(
                    middleware, method=method, path=path, body=b"x" * 9
                )
                self.assertEqual(start["status"], 413)
                self.assertIn(b"exceeds the allowed size", body)

                middleware = self.make_middleware(body_limit=8)
                start, _ = self.run_request(middleware, method=method, path=path, body=b"x" * 9, headers=[])
                self.assertEqual(start["status"], 413)

    def test_rate_limit_returns_429_and_retry_after(self):
        routes = (
            ("GET", "/api/website/catalog"),
            ("POST", "/api/website/pricing"),
            ("POST", "/api/website/bookings"),
        )
        for method, path in routes:
            with self.subTest(path=path):
                middleware = self.make_middleware(limit=1)
                self.run_request(middleware, method=method, path=path)
                start, body = self.run_request(middleware, method=method, path=path)
                self.assertEqual(start["status"], 429)
                self.assertTrue(any(name.lower() == b"retry-after" and int(value) >= 1 for name, value in start["headers"]))
                self.assertNotIn(b"198.51.100.24", body)

    def test_logs_for_rejections_and_backend_errors_are_sanitized(self):
        middleware = self.make_middleware(response_status=422)
        with self.assertLogs("app.website.security", level="WARNING") as captured:
            self.run_request(middleware, path="/api/website/bookings", response_status=422)
        logs = " ".join(captured.output)
        for sensitive in ("guest@example.com", "fixture-marker", "full-request-body"):
            self.assertNotIn(sensitive, logs)
        self.assertIn("event=bookings_rejected", logs)

        middleware = self.make_middleware(response_status=422)
        with self.assertLogs("app.website.security", level="WARNING") as captured:
            self.run_request(middleware, path="/api/website/pricing", response_status=422)
        self.assertIn("event=pricing_rejected", " ".join(captured.output))

        middleware = self.make_middleware(response_status=500)
        with self.assertLogs("app.website.security", level="WARNING") as captured:
            self.run_request(middleware, path="/api/website/pricing", response_status=500)
        self.assertIn("event=backend_error", " ".join(captured.output))

        async def failing_app(_scope, _receive, _send):
            raise RuntimeError("guest@example.com fixture-marker")

        failing = WebsiteProtectionMiddleware(
            failing_app,
            body_limit_bytes=128,
            requests_per_minute={"catalog": 10, "pricing": 10, "bookings": 10},
        )
        with self.assertLogs("app.website.security", level="ERROR") as captured:
            with self.assertRaises(RuntimeError):
                self.run_request(failing)
        logs = " ".join(captured.output)
        self.assertIn("event=backend_error", logs)
        for sensitive in ("guest@example.com", "fixture-marker"):
            self.assertNotIn(sensitive, logs)


class WebsiteIdempotencyRegressionTests(unittest.TestCase):
    def test_existing_idempotent_retry_returns_saved_response_without_duplicate_callback(self):
        request = WebsiteBookingRequest(
            quote_id=UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"),
            date=date.today() + timedelta(days=30), adults=1, currency="THB",
            customer=WebsiteCustomer(name="Guest", email="guest@example.com", phone="123"),
        )
        normalized = website._normalized_booking_payload(request)
        saved_response = {"booking_reference": "TCT-WEB-TEST", "replayed": False}

        class Cursor:
            def __init__(self):
                self.rows = [None, (website._canonical_payload_hash(normalized), saved_response)]
                self.calls = 0

            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            def execute(self, *_args, **_kwargs):
                self.calls += 1

            def fetchone(self):
                return self.rows.pop(0)

        cursor = Cursor()

        class Connection:
            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            def cursor(self):
                return cursor

        with patch.object(website.settings, "website_integration_enabled", True), patch.object(
            website, "_website_connection", return_value=Connection()
        ):
            result = website.create_website_booking(
                request, UUID("bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb")
            )

        self.assertEqual(result["booking_reference"], "TCT-WEB-TEST")
        self.assertTrue(result["replayed"])
        self.assertEqual(cursor.calls, 2)

    def test_legacy_retry_hash_matches_existing_phone_including_request(self):
        request = WebsiteBookingRequest(
            quote_id=UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"),
            date=date.today() + timedelta(days=30), adults=1, currency="THB",
            customer=WebsiteCustomer(name="Guest", email="guest@example.com", phone="123"),
        )
        normalized = website._normalized_booking_payload(request)
        saved_response = {"booking_reference": "TCT-WEB-LEGACY", "replayed": False}

        class Cursor:
            def __init__(self):
                self.rows = [None, (website._canonical_payload_hash(normalized), saved_response)]
                self.calls = 0

            def __enter__(self): return self
            def __exit__(self, *_args): return False
            def execute(self, *_args, **_kwargs): self.calls += 1
            def fetchone(self): return self.rows.pop(0)

        cursor = Cursor()

        class Connection:
            def __enter__(self): return self
            def __exit__(self, *_args): return False
            def cursor(self): return cursor

        with patch.object(website.settings, "website_integration_enabled", True), patch.object(
            website, "_website_connection", return_value=Connection()
        ):
            result = website.create_website_booking(request, UUID("bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"))

        self.assertEqual(result["booking_reference"], "TCT-WEB-LEGACY")
        self.assertTrue(result["replayed"])
        self.assertEqual(cursor.calls, 2)

    def test_retry_without_phone_matches_new_canonical_payload(self):
        request = WebsiteBookingRequest(
            quote_id=UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"),
            date=date.today() + timedelta(days=30), adults=1, currency="THB",
            customer=WebsiteCustomer(name="Guest", email="guest@example.com"),
        )
        normalized = website._normalized_booking_payload(request)
        saved_response = {"booking_reference": "TCT-WEB-NO-PHONE", "replayed": False}

        class Cursor:
            def __init__(self):
                self.rows = [None, (website._canonical_payload_hash(normalized), saved_response)]
                self.calls = 0

            def __enter__(self): return self
            def __exit__(self, *_args): return False
            def execute(self, *_args, **_kwargs): self.calls += 1
            def fetchone(self): return self.rows.pop(0)

        cursor = Cursor()

        class Connection:
            def __enter__(self): return self
            def __exit__(self, *_args): return False
            def cursor(self): return cursor

        with patch.object(website.settings, "website_integration_enabled", True), patch.object(
            website, "_website_connection", return_value=Connection()
        ):
            result = website.create_website_booking(request, UUID("bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"))

        self.assertEqual(result["booking_reference"], "TCT-WEB-NO-PHONE")
        self.assertTrue(result["replayed"])
        self.assertEqual(cursor.calls, 2)

    def test_phone_shape_change_under_same_idempotency_key_is_a_conflict(self):
        quote_id = UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")
        legacy = WebsiteBookingRequest(
            quote_id=quote_id, date=date.today() + timedelta(days=30), adults=1, currency="THB",
            customer=WebsiteCustomer(name="Guest", email="guest@example.com", phone="123"),
        )
        current = WebsiteBookingRequest(
            quote_id=quote_id, date=legacy.date, adults=1, currency="THB",
            customer=WebsiteCustomer(name="Guest", email="guest@example.com"),
        )
        legacy_hash = website._canonical_payload_hash(website._normalized_booking_payload(legacy))

        class Cursor:
            def __init__(self): self.rows = [None, (legacy_hash, {"booking_reference": "hidden"})]
            def __enter__(self): return self
            def __exit__(self, *_args): return False
            def execute(self, *_args, **_kwargs): pass
            def fetchone(self): return self.rows.pop(0)

        class Connection:
            def __enter__(self): return self
            def __exit__(self, *_args): return False
            def cursor(self): return Cursor()

        with patch.object(website.settings, "website_integration_enabled", True), patch.object(
            website, "_website_connection", return_value=Connection()
        ):
            with self.assertRaises(website.HTTPException) as error:
                website.create_website_booking(current, UUID("bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"))
        self.assertEqual(error.exception.status_code, 409)

    def test_existing_idempotency_key_with_different_payload_logs_safe_conflict(self):
        request = WebsiteBookingRequest(
            quote_id=UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"),
            date=date.today() + timedelta(days=30), adults=1, currency="THB",
            customer=WebsiteCustomer(name="Private Guest", email="guest@example.com", phone="123"),
        )
        class Cursor:
            def __init__(self):
                self.rows = [None, ("different-payload-hash", {"booking_reference": "hidden"})]

            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            def execute(self, *_args, **_kwargs):
                pass

            def fetchone(self):
                return self.rows.pop(0)

        class Connection:
            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            def cursor(self):
                return Cursor()

        with patch.object(website.settings, "website_integration_enabled", True), patch.object(
            website, "_website_connection", return_value=Connection()
        ):
            with self.assertLogs("app.website", level="WARNING") as captured:
                with self.assertRaises(website.HTTPException) as error:
                    website.create_website_booking(
                        request, UUID("bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb")
                    )
        self.assertEqual(error.exception.status_code, 409)
        logs = " ".join(captured.output)
        self.assertIn("event=idempotency_conflict", logs)
        for sensitive in ("guest@example.com", "Private Guest", "123", "hidden"):
            self.assertNotIn(sensitive, logs)


class WebsiteDatabaseTimeoutTests(unittest.TestCase):
    def test_website_db_timeouts_are_passed_to_psycopg(self):
        with patch.object(database.settings, "database_url", "synthetic-dsn"), patch(
            "app.database.psycopg.connect", return_value="connection"
        ) as connect:
            result = database.get_connection(connect_timeout=4, statement_timeout_ms=2500)
        self.assertEqual(result, "connection")
        connect.assert_called_once_with(
            "synthetic-dsn", connect_timeout=4, options="-c statement_timeout=2500"
        )


if __name__ == "__main__":
    unittest.main()
