"""Transactional audit-log writes with actor-scoped request idempotency."""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Callable, TypeVar
from uuid import UUID

from psycopg.types.json import Jsonb


OperationResult = TypeVar("OperationResult")


class AuditIdempotencyConflict(Exception):
    """Raised when an actor reuses a request ID for a different payload."""


@dataclass(frozen=True)
class AuditEventResult:
    event: dict[str, Any]
    replayed: bool
    operation_result: Any = None


def _normalize_payload_value(value: Any, key: str | None = None) -> Any:
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, dict):
        if any(not isinstance(item_key, str) for item_key in value):
            raise TypeError("Canonical audit payload object keys must be strings")
        return {
            item_key: _normalize_payload_value(item, item_key)
            for item_key, item in value.items()
            if not (key is None and item_key == "request_id")
        }
    if isinstance(value, (list, tuple)):
        return [_normalize_payload_value(item) for item in value]
    if isinstance(value, str):
        if key == "reason":
            value = value.strip()
        try:
            return str(UUID(value))
        except ValueError:
            return value
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError("Canonical audit payload cannot contain non-finite numbers")
    if value is None or isinstance(value, (bool, int, float)):
        return value
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    raise TypeError(f"Unsupported canonical audit payload value: {type(value).__name__}")


def canonical_audit_payload(payload: dict[str, Any]) -> bytes:
    """Serialize semantic request data deterministically, excluding request_id."""
    if not isinstance(payload, dict):
        raise TypeError("Canonical audit payload must be an object")
    normalized = _normalize_payload_value(payload)
    return json.dumps(
        normalized,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def hash_audit_payload(payload: dict[str, Any]) -> str:
    """Return the lowercase SHA-256 digest of a canonical audit payload."""
    return hashlib.sha256(canonical_audit_payload(payload)).hexdigest()


_EVENT_COLUMNS = (
    "id",
    "user_id",
    "entity_type",
    "entity_id",
    "action",
    "old_value",
    "new_value",
    "created_at",
    "request_id",
    "request_payload_hash",
    "actor_email_snapshot",
    "actor_name_snapshot",
    "reason",
)


def _event_dict(row: tuple[Any, ...]) -> dict[str, Any]:
    return dict(zip(_EVENT_COLUMNS, row))


def run_idempotent_audit_event(
    conn: Any,
    *,
    user_id: UUID,
    request_id: UUID,
    request_payload: dict[str, Any],
    entity_type: str,
    entity_id: UUID,
    action: str,
    old_value: Any,
    new_value: Any,
    actor_email_snapshot: str | None,
    actor_name_snapshot: str | None,
    reason: str | None,
    operation: Callable[[Any], OperationResult],
) -> AuditEventResult:
    """Run a business operation and append its audit event in caller's transaction.

    The caller owns transaction scope and must commit or roll back. This function
    deliberately does neither. A retry with the same actor, request ID, and
    canonical payload returns the original event without calling ``operation``.
    """
    if getattr(conn, "autocommit", False):
        raise ValueError("Audit writes require a caller-managed transaction")
    if not callable(operation):
        raise TypeError("operation must be callable")

    payload_hash = hash_audit_payload(request_payload)
    actor_key = str(UUID(str(user_id)))
    request_key = str(UUID(str(request_id)))

    with conn.cursor() as cur:
        # Transaction-scoped advisory lock serializes concurrent requests with
        # this actor/request pair, including the initial insert when no row exists.
        cur.execute(
            "SELECT pg_advisory_xact_lock(hashtextextended(%s, 731294))",
            (f"audit_log:{actor_key}:{request_key}",),
        )
        cur.execute(
            """
            SELECT id, user_id, entity_type, entity_id, action, old_value,
                   new_value, created_at, request_id, request_payload_hash,
                   actor_email_snapshot, actor_name_snapshot, reason
            FROM audit_log
            WHERE user_id = %s AND request_id = %s
            """,
            (user_id, request_id),
        )
        existing = cur.fetchone()
        if existing is not None:
            event = _event_dict(existing)
            if event["request_payload_hash"] != payload_hash:
                raise AuditIdempotencyConflict(
                    "This actor/request_id pair was already used with a different payload"
                )
            return AuditEventResult(event=event, replayed=True)

        operation_result = operation(conn)
        cur.execute(
            """
            INSERT INTO audit_log (
                user_id, entity_type, entity_id, action, old_value, new_value,
                request_id, request_payload_hash, actor_email_snapshot,
                actor_name_snapshot, reason
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id, user_id, entity_type, entity_id, action, old_value,
                      new_value, created_at, request_id, request_payload_hash,
                      actor_email_snapshot, actor_name_snapshot, reason
            """,
            (
                user_id,
                entity_type,
                entity_id,
                action,
                Jsonb(old_value),
                Jsonb(new_value),
                request_id,
                payload_hash,
                actor_email_snapshot,
                actor_name_snapshot,
                reason,
            ),
        )
        event = _event_dict(cur.fetchone())

    return AuditEventResult(
        event=event,
        replayed=False,
        operation_result=operation_result,
    )
