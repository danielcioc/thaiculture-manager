"""Reusable server-side authentication and permission dependencies.

This module validates externally issued HS256 JWTs. It intentionally does not
issue tokens or provide a development identity fallback.
"""

import base64
import hashlib
import hmac
import json
import math
import time
from dataclasses import dataclass
from typing import Any, Callable, Optional
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import settings
from app.database import get_connection


_bearer_scheme = HTTPBearer(auto_error=False)
_MAX_TOKEN_LENGTH = 8192


@dataclass(frozen=True)
class CurrentUser:
    id: UUID
    email: str
    full_name: str
    role_id: Optional[UUID]
    role_name: Optional[str]
    permissions: dict[str, Any]


def _unauthorized() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Missing or invalid bearer identity",
        headers={"WWW-Authenticate": "Bearer"},
    )


def _decode_segment(segment: str) -> bytes:
    padding = "=" * (-len(segment) % 4)
    return base64.b64decode(
        segment + padding,
        altchars=b"-_",
        validate=True,
    )


def _decode_identity_token(token: str) -> UUID:
    secret = settings.auth_jwt_secret
    issuer = settings.auth_jwt_issuer
    audience = settings.auth_jwt_audience
    if secret is None or issuer is None or audience is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication is not configured",
        )
    secret_value = secret.get_secret_value()
    if len(secret_value.encode("utf-8")) < 32:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication is not configured",
        )
    if not token or len(token) > _MAX_TOKEN_LENGTH:
        raise _unauthorized()

    try:
        header_segment, payload_segment, signature_segment = token.split(".")
        header = json.loads(_decode_segment(header_segment))
        claims = json.loads(_decode_segment(payload_segment))
        if not isinstance(header, dict) or header.get("alg") != "HS256":
            raise ValueError("Unsupported JWT algorithm")
        if set(header) - {"alg", "typ"}:
            raise ValueError("Unsupported JWT header parameter")
        if header.get("typ", "JWT") != "JWT":
            raise ValueError("Unsupported JWT type")

        signing_input = f"{header_segment}.{payload_segment}".encode("ascii")
        expected_signature = hmac.new(
            secret_value.encode("utf-8"),
            signing_input,
            hashlib.sha256,
        ).digest()
        supplied_signature = _decode_segment(signature_segment)
        if not hmac.compare_digest(expected_signature, supplied_signature):
            raise ValueError("Invalid signature")

        if not isinstance(claims, dict):
            raise ValueError("Invalid claims")
        subject = claims.get("sub")
        expiration = claims.get("exp")
        not_before = claims.get("nbf")
        if not isinstance(subject, str):
            raise ValueError("Missing subject")
        if isinstance(expiration, bool) or not isinstance(expiration, (int, float)):
            raise ValueError("Missing expiration")
        if not math.isfinite(expiration) or expiration <= time.time():
            raise ValueError("Expired token")
        if not_before is not None:
            if isinstance(not_before, bool) or not isinstance(not_before, (int, float)):
                raise ValueError("Invalid not-before claim")
            if not math.isfinite(not_before) or not_before > time.time():
                raise ValueError("Token is not active")
        if claims.get("iss") != issuer:
            raise ValueError("Invalid issuer")
        token_audience = claims.get("aud")
        if token_audience != audience and not (
            isinstance(token_audience, list) and audience in token_audience
        ):
            raise ValueError("Invalid audience")
        return UUID(subject)
    except (
        ValueError,
        TypeError,
        UnicodeError,
        OverflowError,
        json.JSONDecodeError,
        base64.binascii.Error,
    ):
        raise _unauthorized() from None


def _load_user(user_id: UUID) -> CurrentUser:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT u.id, u.email, u.full_name, u.is_active,
                       r.id AS role_id, r.name AS role_name, r.permissions
                FROM users u
                LEFT JOIN roles r ON r.id = u.role_id
                WHERE u.id = %s;
                """,
                (user_id,),
            )
            row = cur.fetchone()

    if row is None:
        raise _unauthorized()
    user_db_id, email, full_name, is_active, role_id, role_name, permissions = row
    if not is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive",
        )
    if not isinstance(permissions, dict):
        permissions = {}
    return CurrentUser(
        id=user_db_id,
        email=email,
        full_name=full_name,
        role_id=role_id,
        role_name=role_name,
        permissions=permissions,
    )


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer_scheme),
) -> CurrentUser:
    """Validate bearer identity and reload the active user from the database."""
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise _unauthorized()
    user_id = _decode_identity_token(credentials.credentials)
    return _load_user(user_id)


def require_permission(permission_key: str) -> Callable[..., CurrentUser]:
    """Create a FastAPI dependency that requires one role permission key."""
    if not permission_key or not isinstance(permission_key, str):
        raise ValueError("permission_key must be a non-empty string")

    def dependency(current_user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if current_user.permissions.get(permission_key) is not True:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User lacks the required permission",
            )
        return current_user

    return dependency
