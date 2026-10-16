"""Defence-in-depth controls for the public website API routes."""

import logging
import threading
import time
from collections import deque
from typing import Callable

from starlette.responses import JSONResponse


logger = logging.getLogger("app.website.security")

PUBLIC_WEBSITE_ROUTES = {
    ("GET", "/api/website/catalog"): "catalog",
    ("POST", "/api/website/pricing"): "pricing",
    ("POST", "/api/website/bookings"): "bookings",
}


class WebsiteProtectionMiddleware:
    """Apply bounded request bodies and process-local fixed-window limits.

    The ingress proxy must also enforce distributed/client-aware rate limits.
    """

    def __init__(
        self,
        app,
        *,
        enabled: bool = True,
        body_limit_bytes: int,
        requests_per_minute: dict[str, int],
        clock: Callable[[], float] = time.monotonic,
    ):
        self.app = app
        self.enabled = enabled
        self.body_limit_bytes = body_limit_bytes
        self.requests_per_minute = dict(requests_per_minute)
        self.clock = clock
        self._windows: dict[tuple[str, str], deque[float]] = {}
        self._lock = threading.Lock()

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        if not self.enabled:
            await self.app(scope, receive, send)
            return

        method = scope.get("method", "").upper()
        path = scope.get("path", "")
        route_kind = PUBLIC_WEBSITE_ROUTES.get((method, path))
        if route_kind is None:
            await self.app(scope, receive, send)
            return

        client = scope.get("client") or ("unknown", 0)
        client_key = str(client[0])
        limit = self.requests_per_minute[route_kind]
        retry_after = self._consume(route_kind, client_key, limit)
        if retry_after is not None:
            logger.warning(
                "website_public_event event=rate_limit_exceeded route=%s",
                route_kind,
            )
            await JSONResponse(
                status_code=429,
                content={"detail": "Too many requests. Please retry later."},
                headers={"Retry-After": str(retry_after)},
            )(scope, receive, send)
            return

        content_length = self._content_length(scope)
        if content_length is not None and content_length < 0:
            await JSONResponse(
                status_code=400,
                content={"detail": "Invalid request body length."},
            )(scope, receive, send)
            logger.warning(
                "website_public_event event=request_rejected route=%s status=400",
                route_kind,
            )
            return
        if content_length is not None and content_length > self.body_limit_bytes:
            await self._body_too_large(scope, receive, send, route_kind)
            return
        buffered = await self._read_bounded_body(scope, receive, send, route_kind)
        if buffered is None:
            return
        messages = deque(buffered)

        async def replay_receive():
            if messages:
                return messages.popleft()
            return await receive()

        receive = replay_receive

        async def observe_response(message):
            if message["type"] == "http.response.start":
                status_code = message["status"]
                if status_code in {400, 409, 422}:
                    event = f"{route_kind}_rejected"
                elif status_code >= 500:
                    event = "backend_error"
                else:
                    event = None
                if event:
                    logger.warning(
                        "website_public_event event=%s route=%s status=%s",
                        event,
                        route_kind,
                        status_code,
                    )
            await send(message)

        try:
            await self.app(scope, receive, observe_response)
        except Exception:
            logger.error(
                "website_public_event event=backend_error route=%s",
                route_kind,
            )
            raise

    def _consume(self, route_kind: str, client_key: str, limit: int) -> int | None:
        now = self.clock()
        window_start = now - 60
        key = (route_kind, client_key)
        with self._lock:
            if key not in self._windows and len(self._windows) >= 4096:
                key = (route_kind, "__overflow__")
            bucket = self._windows.setdefault(key, deque())
            while bucket and bucket[0] <= window_start:
                bucket.popleft()
            if len(bucket) >= limit:
                return max(1, int(bucket[0] + 60 - now + 0.999))
            bucket.append(now)
            if len(self._windows) > 4096:
                for old_key in list(self._windows):
                    old_bucket = self._windows[old_key]
                    while old_bucket and old_bucket[0] <= window_start:
                        old_bucket.popleft()
                    if not old_bucket:
                        self._windows.pop(old_key, None)
        return None

    @staticmethod
    def _content_length(scope) -> int | None:
        for name, value in scope.get("headers", []):
            if name.lower() == b"content-length":
                try:
                    return int(value)
                except ValueError:
                    return -1
        return None

    async def _read_bounded_body(self, scope, receive, send, route_kind):
        messages = []
        total = 0
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return None
            if message["type"] != "http.request":
                continue
            total += len(message.get("body", b""))
            if total > self.body_limit_bytes:
                await self._body_too_large(scope, receive, send, route_kind)
                return None
            messages.append(message)
            if not message.get("more_body", False):
                return messages

    async def _body_too_large(self, scope, receive, send, route_kind):
        logger.warning(
            "website_public_event event=request_body_too_large route=%s",
            route_kind,
        )
        await JSONResponse(
            status_code=413,
            content={"detail": "Request body exceeds the allowed size."},
        )(scope, receive, send)


def website_rate_limits(settings) -> dict[str, int]:
    return {
        "catalog": settings.website_catalog_requests_per_minute,
        "pricing": settings.website_pricing_requests_per_minute,
        "bookings": settings.website_bookings_requests_per_minute,
    }
