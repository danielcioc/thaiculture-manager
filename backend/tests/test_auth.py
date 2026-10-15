import base64
import hashlib
import hmac
import json
import unittest
from uuid import UUID
from unittest.mock import patch

from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from pydantic import SecretStr

from app import auth


TEST_USER_ID = UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")
TEST_ROLE_ID = UUID("bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb")
TEST_SECRET = "isolated-unit-test-signing-key-never-used-for-authentication"


def _b64url(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def make_token(*, claims=None, algorithm="HS256", secret=TEST_SECRET):
    token_claims = {
        "sub": str(TEST_USER_ID),
        "iss": "test-issuer",
        "aud": "test-api",
        "exp": 4_102_444_800,
    }
    token_claims.update(claims or {})
    header = _b64url(json.dumps({"alg": algorithm, "typ": "JWT"}).encode())
    payload = _b64url(json.dumps(token_claims).encode())
    signing_input = f"{header}.{payload}".encode("ascii")
    signature = hmac.new(secret.encode(), signing_input, hashlib.sha256).digest()
    return f"{header}.{payload}.{_b64url(signature)}"


class FakeCursor:
    def __init__(self, row):
        self.row = row
        self.query = None
        self.params = None

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def execute(self, query, params=None):
        self.query = query
        self.params = params

    def fetchone(self):
        return self.row


class FakeConnection:
    def __init__(self, row):
        self.fake_cursor = FakeCursor(row)

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def cursor(self):
        return self.fake_cursor


def user_row(*, is_active=True, permissions=None, role_id=TEST_ROLE_ID):
    return (
        TEST_USER_ID,
        "reviewer@example.test",
        "Test Reviewer",
        is_active,
        role_id,
        "reviewer",
        permissions if permissions is not None else {},
    )


class AuthenticationDependencyTests(unittest.TestCase):
    def setUp(self):
        self.config = patch.multiple(
            auth.settings,
            auth_jwt_secret=SecretStr(TEST_SECRET),
            auth_jwt_issuer="test-issuer",
            auth_jwt_audience="test-api",
        )
        self.config.start()
        self.addCleanup(self.config.stop)

    @staticmethod
    def credentials(token):
        return HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

    def test_missing_identity_returns_401_without_database_access(self):
        with patch.object(auth, "get_connection") as get_connection:
            with self.assertRaises(HTTPException) as error:
                auth.get_current_user(None)
        self.assertEqual(error.exception.status_code, 401)
        self.assertEqual(error.exception.headers["WWW-Authenticate"], "Bearer")
        get_connection.assert_not_called()

    def test_invalid_identity_returns_401_without_database_access(self):
        with patch.object(auth, "get_connection") as get_connection:
            with self.assertRaises(HTTPException) as error:
                auth.get_current_user(self.credentials("not-a-jwt"))
        self.assertEqual(error.exception.status_code, 401)
        get_connection.assert_not_called()

    def test_invalid_signature_or_algorithm_returns_401(self):
        for token in (
            make_token(secret="different-signing-key-not-the-configured-key"),
            make_token(algorithm="none"),
        ):
            with self.subTest(token_kind="untrusted"):
                with patch.object(auth, "get_connection") as get_connection:
                    with self.assertRaises(HTTPException) as error:
                        auth.get_current_user(self.credentials(token))
                self.assertEqual(error.exception.status_code, 401)
                get_connection.assert_not_called()

    def test_expired_or_wrong_issuer_token_returns_401(self):
        for claims in (
            {"exp": 1},
            {"iss": "untrusted-issuer"},
            {"aud": "another-api"},
        ):
            with self.subTest(claims=claims):
                with patch.object(auth, "get_connection") as get_connection:
                    with self.assertRaises(HTTPException) as error:
                        auth.get_current_user(self.credentials(make_token(claims=claims)))
                self.assertEqual(error.exception.status_code, 401)
                get_connection.assert_not_called()

    def test_unknown_user_returns_401(self):
        connection = FakeConnection(None)
        with patch.object(auth, "get_connection", return_value=connection):
            with self.assertRaises(HTTPException) as error:
                auth.get_current_user(self.credentials(make_token()))
        self.assertEqual(error.exception.status_code, 401)

    def test_inactive_user_returns_403(self):
        connection = FakeConnection(user_row(is_active=False))
        with patch.object(auth, "get_connection", return_value=connection):
            with self.assertRaises(HTTPException) as error:
                auth.get_current_user(self.credentials(make_token()))
        self.assertEqual(error.exception.status_code, 403)

    def test_active_user_and_permission_are_loaded_from_database_role(self):
        connection = FakeConnection(
            user_row(permissions={"bookings.import_review.approve": True})
        )
        with patch.object(auth, "get_connection", return_value=connection):
            current_user = auth.get_current_user(self.credentials(make_token()))
            permitted = auth.require_permission("bookings.import_review.approve")(current_user)

        self.assertEqual(permitted.id, TEST_USER_ID)
        self.assertEqual(permitted.role_id, TEST_ROLE_ID)
        self.assertIn("LEFT JOIN roles", connection.fake_cursor.query)
        self.assertEqual(connection.fake_cursor.params, (TEST_USER_ID,))

    def test_missing_or_false_permission_returns_403(self):
        for permissions in ({}, {"bookings.import_review.approve": False}):
            with self.subTest(permissions=permissions):
                connection = FakeConnection(user_row(permissions=permissions))
                with patch.object(auth, "get_connection", return_value=connection):
                    current_user = auth.get_current_user(self.credentials(make_token()))
                    with self.assertRaises(HTTPException) as error:
                        auth.require_permission("bookings.import_review.approve")(current_user)
                self.assertEqual(error.exception.status_code, 403)

    def test_unrecognized_permissions_shape_fails_closed(self):
        connection = FakeConnection(
            user_row(permissions=["bookings.import_review.approve"])
        )
        with patch.object(auth, "get_connection", return_value=connection):
            current_user = auth.get_current_user(self.credentials(make_token()))
            with self.assertRaises(HTTPException) as error:
                auth.require_permission("bookings.import_review.approve")(current_user)
        self.assertEqual(error.exception.status_code, 403)

    def test_auth_dependency_fails_closed_when_verifier_config_is_missing(self):
        with patch.object(auth.settings, "auth_jwt_secret", None):
            with patch.object(auth, "get_connection") as get_connection:
                with self.assertRaises(HTTPException) as error:
                    auth.get_current_user(self.credentials(make_token()))
        self.assertEqual(error.exception.status_code, 503)
        get_connection.assert_not_called()


if __name__ == "__main__":
    unittest.main()
