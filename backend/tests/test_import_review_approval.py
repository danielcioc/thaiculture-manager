import asyncio
import base64
import hmac
import json
import os
import inspect
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier
from urllib.parse import urlparse
from uuid import uuid4
from unittest.mock import patch

from fastapi import FastAPI
from pydantic import SecretStr
from psycopg.types.json import Jsonb

from app import auth
from app.routers import bookings


TEST_DATABASE_URL = os.getenv("TCT_TEST_DATABASE_URL")
_parsed_test_url = urlparse(TEST_DATABASE_URL) if TEST_DATABASE_URL else None
_safe_test_database = bool(
    _parsed_test_url
    and "test" in _parsed_test_url.path.lower()
    and _parsed_test_url.hostname in {"localhost", "127.0.0.1"}
    and _parsed_test_url.port is not None
    and _parsed_test_url.port >= 50000
)


def _b64url(value):
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _make_token(user_id, secret, *, issuer="approval-test-issuer", audience="approval-test-api"):
    header = _b64url(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
    claims = {
        "sub": str(user_id),
        "iss": issuer,
        "aud": audience,
        "exp": 4_102_444_800,
    }
    body = _b64url(json.dumps(claims).encode())
    signing_input = f"{header}.{body}".encode("ascii")
    signature = hmac.new(secret.encode("ascii"), signing_input, "sha256").digest()
    return f"{header}.{body}.{_b64url(signature)}"


def _asgi_request(app, method, path, *, body=None, token=None):
    request_body = json.dumps(body or {}).encode("utf-8")
    headers = [(b"content-type", b"application/json")]
    if token is not None:
        headers.append((b"authorization", f"Bearer {token}".encode("ascii")))
    messages = []
    received = False

    async def receive():
        nonlocal received
        if not received:
            received = True
            return {"type": "http.request", "body": request_body, "more_body": False}
        return {"type": "http.disconnect"}

    async def send(message):
        messages.append(message)

    scope = {
        "type": "http",
        "asgi": {"version": "3.0", "spec_version": "2.3"},
        "http_version": "1.1",
        "method": method,
        "scheme": "http",
        "path": path,
        "raw_path": path.encode("ascii"),
        "query_string": b"",
        "root_path": "",
        "headers": headers,
        "client": ("test-client", 12345),
        "server": ("test-server", 80),
    }
    try:
        asyncio.run(app(scope, receive, send))
    except Exception:
        if not any(message["type"] == "http.response.start" for message in messages):
            raise
    start = next(message for message in messages if message["type"] == "http.response.start")
    response_body = b"".join(
        message.get("body", b"")
        for message in messages
        if message["type"] == "http.response.body"
    )
    try:
        decoded_body = json.loads(response_body) if response_body else {}
    except json.JSONDecodeError:
        decoded_body = {"non_json_response": True}
    return start["status"], decoded_body


@unittest.skipUnless(_safe_test_database, "requires isolated local TCT_TEST_DATABASE_URL")
class ImportReviewApprovalPostgresTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import psycopg

        cls.psycopg = psycopg
        cls.schema = f"review_approval_{uuid4().hex[:12]}"
        cls.schema_options = f"-csearch_path={cls.schema}"
        with psycopg.connect(TEST_DATABASE_URL, autocommit=True) as admin:
            admin.execute(f'CREATE SCHEMA "{cls.schema}"')
        with cls.connect_admin() as conn:
            conn.execute(
                """
                CREATE TABLE roles (
                    id uuid PRIMARY KEY,
                    name text NOT NULL,
                    permissions jsonb NOT NULL DEFAULT '{}'::jsonb
                );
                CREATE TABLE users (
                    id uuid PRIMARY KEY,
                    email text NOT NULL,
                    full_name text NOT NULL,
                    is_active boolean NOT NULL DEFAULT true,
                    role_id uuid REFERENCES roles(id)
                );
                CREATE TABLE tours (
                    id uuid PRIMARY KEY,
                    name text NOT NULL,
                    is_active boolean NOT NULL DEFAULT true
                );
                CREATE TABLE bookings (
                    id uuid PRIMARY KEY,
                    booking_code varchar(30) UNIQUE NOT NULL,
                    status varchar(40) NOT NULL,
                    imported_raw_tour_name text,
                    mapping_status varchar(40),
                    tour_id uuid REFERENCES tours(id),
                    needs_manual_review boolean
                );
                CREATE TABLE audit_log (
                    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
                    user_id uuid REFERENCES users(id),
                    entity_type varchar(50) NOT NULL,
                    entity_id uuid NOT NULL,
                    action varchar(50) NOT NULL,
                    old_value jsonb,
                    new_value jsonb,
                    created_at timestamptz DEFAULT now()
                );
                """
            )
            migration = (
                Path(__file__).resolve().parents[2]
                / "database/migrations/20261015_add_audit_log_idempotency_fields.sql"
            ).read_text(encoding="utf-8")
            migration = "\n".join(
                line for line in migration.splitlines()
                if not line.lstrip().startswith("--")
                and line.strip().upper() not in {"BEGIN;", "COMMIT;"}
            )
            for statement in migration.split(";"):
                if statement.strip():
                    conn.execute(statement)

    @classmethod
    def connect_admin(cls):
        return cls.psycopg.connect(
            TEST_DATABASE_URL,
            options=cls.schema_options,
            autocommit=True,
        )

    @classmethod
    def tearDownClass(cls):
        with cls.psycopg.connect(TEST_DATABASE_URL, autocommit=True) as admin:
            admin.execute(f'DROP SCHEMA IF EXISTS "{cls.schema}" CASCADE')

    def setUp(self):
        self.actor_id = uuid4()
        self.role_id = uuid4()
        self.booking_id = uuid4()
        self.tour_id = uuid4()
        self.request_id = uuid4()
        self.booking_code = f"TST-REVIEW-{uuid4().hex[:10]}"
        self.secret = os.urandom(48).hex()
        self.app = FastAPI()
        self.app.include_router(bookings.router)
        self._auth_settings = patch.multiple(
            auth.settings,
            auth_jwt_secret=SecretStr(self.secret),
            auth_jwt_issuer="approval-test-issuer",
            auth_jwt_audience="approval-test-api",
        )
        self._auth_settings.start()
        self.addCleanup(self._auth_settings.stop)
        self.actor = auth.CurrentUser(
            id=self.actor_id,
            email="reviewer@example.invalid",
            full_name="Isolated Reviewer",
            role_id=self.role_id,
            role_name="test-reviewer",
            permissions={"bookings.import_review.approve": True},
        )
        self._booking_connection_patch = patch.object(
            bookings, "get_connection", side_effect=self.connect
        )
        self._auth_connection_patch = patch.object(
            auth, "get_connection", side_effect=self.connect
        )
        self._booking_connection_patch.start()
        self._auth_connection_patch.start()
        self.addCleanup(self._booking_connection_patch.stop)
        self.addCleanup(self._auth_connection_patch.stop)

        with self.connect() as conn:
            conn.execute(
                "INSERT INTO roles (id, name, permissions) VALUES (%s, %s, %s)",
                (self.role_id, "test-reviewer", Jsonb({"bookings.import_review.approve": True})),
            )
            conn.execute(
                "INSERT INTO users (id, email, full_name, role_id) VALUES (%s, %s, %s, %s)",
                (self.actor_id, "reviewer@example.invalid", "Isolated Reviewer", self.role_id),
            )
            conn.execute(
                "INSERT INTO tours (id, name, is_active) VALUES (%s, %s, true)",
                (self.tour_id, "Canonical Isolated Tour"),
            )
            conn.execute(
                """INSERT INTO bookings (
                       id, booking_code, status, imported_raw_tour_name,
                       mapping_status, tour_id, needs_manual_review
                   ) VALUES (%s, %s, 'Inquiry', %s, 'probable_manual_review', NULL, true)""",
                (self.booking_id, self.booking_code, "Imported raw label"),
            )

    def connect(self):
        return self.psycopg.connect(TEST_DATABASE_URL, options=self.schema_options)

    def request_payload(self, **changes):
        payload = {
            "expected_mapping_status": "probable_manual_review",
            "expected_tour_id": None,
            "expected_needs_manual_review": True,
            "mapping_status": "confirmed",
            "tour_id": str(self.tour_id),
            "reason": "Owner confirmed source mapping",
            "confirm": True,
            "request_id": str(self.request_id),
        }
        payload.update(changes)
        return payload

    def post(self, payload=None, *, token="auto", booking_code=None):
        if token == "auto":
            token = _make_token(self.actor_id, self.secret)
        return _asgi_request(
            self.app,
            "POST",
            f"/bookings/{booking_code or self.booking_code}/import-review/decision",
            body=payload or self.request_payload(),
            token=token,
        )

    def assert_http_error(self, status_code, payload=None):
        actual, body = self.post(payload)
        self.assertEqual(actual, status_code, body)
        return body

    def auth_token(self, *, issuer="approval-test-issuer", audience="approval-test-api"):
        return _make_token(self.actor_id, self.secret, issuer=issuer, audience=audience)

    def event_count(self):
        with self.connect() as conn:
            return conn.execute(
                "SELECT count(*) FROM audit_log WHERE user_id = %s AND request_id = %s",
                (self.actor_id, self.request_id),
            ).fetchone()[0]

    def test_endpoint_is_bound_to_required_permission_dependency(self):
        dependency = inspect.signature(bookings.decide_import_review).parameters[
            "current_user"
        ].default.dependency
        permission = inspect.getclosurevars(dependency).nonlocals["permission_key"]
        self.assertEqual(permission, "bookings.import_review.approve")

    def test_missing_and_invalid_tokens_are_rejected(self):
        self.assertEqual(self.post(token=None)[0], 401)
        self.assertEqual(self.post(token="not-a-jwt")[0], 401)

    def test_wrong_issuer_and_audience_are_rejected(self):
        self.assertEqual(self.post(token=self.auth_token(issuer="untrusted"))[0], 401)
        self.assertEqual(self.post(token=self.auth_token(audience="another-api"))[0], 401)

    def test_request_id_is_required_and_confirmation_must_be_explicit(self):
        missing_request_id = self.request_payload()
        missing_request_id.pop("request_id")
        response, _ = self.post(missing_request_id)
        self.assertEqual(response, 422)
        self.assert_http_error(400, self.request_payload(confirm=False))

    def test_insufficient_permission_is_rejected_by_endpoint(self):
        with self.connect() as conn:
            conn.execute(
                "UPDATE roles SET permissions = %s WHERE id = %s",
                (Jsonb({}), self.role_id),
            )
        response, _ = self.post()
        self.assertEqual(response, 403)
        self.assertEqual(self.event_count(), 0)

    def test_missing_booking_returns_404(self):
        response, body = self.post(booking_code="UNKNOWN-BOOKING")
        self.assertEqual(response, 404, body)

    def test_missing_or_inactive_tour_returns_422(self):
        self.assert_http_error(422, self.request_payload(tour_id=str(uuid4())))
        with self.connect() as conn:
            conn.execute("UPDATE tours SET is_active = false WHERE id = %s", (self.tour_id,))
        self.assert_http_error(422)
        self.assertEqual(self.event_count(), 0)

    def test_stale_mapping_returns_409_without_audit(self):
        with self.connect() as conn:
            conn.execute(
                "UPDATE bookings SET mapping_status = 'unmapped' WHERE id = %s",
                (self.booking_id,),
            )
        self.assert_http_error(409)
        self.assertEqual(self.event_count(), 0)

    def test_approval_updates_mapping_and_audit_atomically(self):
        response_status, body = self.post()
        self.assertEqual(response_status, 200, body)
        self.assertEqual(body["mapping_status"], "confirmed")
        self.assertFalse(body["needs_manual_review"])
        self.assertEqual(body["tour_id"], str(self.tour_id))
        self.assertEqual(body["tour_name"], "Canonical Isolated Tour")
        self.assertFalse(body["replayed"])
        with self.connect() as conn:
            booking = conn.execute(
                """SELECT status, imported_raw_tour_name, mapping_status,
                          tour_id, needs_manual_review
                   FROM bookings WHERE id = %s""",
                (self.booking_id,),
            ).fetchone()
            event = conn.execute(
                """SELECT action, old_value, new_value, actor_email_snapshot, reason
                   FROM audit_log WHERE user_id = %s AND request_id = %s""",
                (self.actor_id, self.request_id),
            ).fetchone()
        self.assertEqual(booking, (
            "Inquiry", "Imported raw label", "confirmed", self.tour_id, False
        ))
        self.assertEqual(event[0], "import_review.approved")
        self.assertEqual(event[1]["mapping_status"], "probable_manual_review")
        self.assertEqual(event[2]["mapping_status"], "confirmed")
        self.assertEqual(event[2]["imported_raw_tour_name"], "Imported raw label")
        self.assertEqual(event[3], "reviewer@example.invalid")
        self.assertEqual(event[4], "Owner confirmed source mapping")
        self.assertEqual(self.event_count(), 1)

    def test_identical_retry_returns_existing_event_without_duplicate(self):
        first = self.post()
        retry = self.post()
        self.assertEqual(first[0], 200, first[1])
        self.assertEqual(retry[0], 200, retry[1])
        self.assertEqual(first[1]["review_event_id"], retry[1]["review_event_id"])
        self.assertTrue(retry[1]["replayed"])
        self.assertEqual(self.event_count(), 1)

    def test_concurrent_identical_requests_create_one_event(self):
        barrier = Barrier(2)

        def submit():
            barrier.wait(timeout=10)
            return self.post()

        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(lambda _index: submit(), range(2)))
        self.assertEqual([status for status, _body in results], [200, 200])
        self.assertEqual(
            len({body["review_event_id"] for _status, body in results}), 1
        )
        self.assertEqual(
            sorted(body["replayed"] for _status, body in results), [False, True]
        )
        self.assertEqual(self.event_count(), 1)

    def test_same_request_id_with_different_payload_returns_409(self):
        self.post()
        self.assert_http_error(
            409, self.request_payload(reason="Different semantic request")
        )
        self.assertEqual(self.event_count(), 1)

    def test_audit_insert_failure_rolls_back_booking_update(self):
        with self.connect() as conn:
            conn.execute(
                """
                CREATE FUNCTION reject_review_audit() RETURNS trigger AS $$
                BEGIN
                    IF NEW.entity_type = 'booking_import_review' THEN
                        RAISE EXCEPTION 'isolated audit failure';
                    END IF;
                    RETURN NEW;
                END;
                $$ LANGUAGE plpgsql;
                CREATE TRIGGER reject_review_audit_trigger
                BEFORE INSERT ON audit_log
                FOR EACH ROW EXECUTE FUNCTION reject_review_audit();
                """
            )
        response, _ = self.post()
        self.assertEqual(response, 500)
        with self.connect() as conn:
            booking_state = conn.execute(
                "SELECT mapping_status, tour_id, needs_manual_review FROM bookings WHERE id = %s",
                (self.booking_id,),
            ).fetchone()
            conn.execute("DROP TRIGGER reject_review_audit_trigger ON audit_log")
            conn.execute("DROP FUNCTION reject_review_audit()")
        self.assertEqual(booking_state, ("probable_manual_review", None, True))
        self.assertEqual(self.event_count(), 0)

    def test_probable_review_can_be_marked_unmapped(self):
        payload = self.request_payload(
            mapping_status="unmapped",
            tour_id=None,
            reason="No canonical match exists",
        )
        response_status, response = self.post(payload)
        self.assertEqual(response_status, 200, response)
        self.assertEqual(response["mapping_status"], "unmapped")
        self.assertIsNone(response["tour_id"])
        with self.connect() as conn:
            action = conn.execute(
                "SELECT action FROM audit_log WHERE request_id = %s", (self.request_id,)
            ).fetchone()[0]
            self.assertEqual(action, "import_review.rejected")


if __name__ == "__main__":
    unittest.main()
