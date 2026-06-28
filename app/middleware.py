from __future__ import annotations

import json
import logging
import secrets
import time
import uuid
from collections import defaultdict, deque
from collections.abc import Awaitable, Callable

from fastapi import Request, Response
from starlette.responses import JSONResponse

from app.config import Settings

PUBLIC_PATHS = {
    "/",
    "/health",
    "/ready",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/query",
    "/upload",
}


class InMemoryRateLimiter:
    def __init__(self, limit_per_minute: int) -> None:
        self.limit_per_minute = max(1, limit_per_minute)
        self.window_seconds = 60
        self.requests: defaultdict[str, deque[float]] = defaultdict(deque)

    def allow(self, key: str, now: float | None = None) -> bool:
        current = now or time.monotonic()
        bucket = self.requests[key]
        cutoff = current - self.window_seconds
        while bucket and bucket[0] < cutoff:
            bucket.popleft()
        if len(bucket) >= self.limit_per_minute:
            return False
        bucket.append(current)
        return True


def configure_logging(level: str) -> None:
    logging.basicConfig(level=getattr(logging, level.upper(), logging.INFO))


def make_security_middleware(
    settings: Settings,
) -> Callable[[Request, Callable[[Request], Awaitable[Response]]], Awaitable[Response]]:
    limiter = InMemoryRateLimiter(settings.rate_limit_per_minute)
    logger = logging.getLogger("telcoassist.requests")

    async def middleware(
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        request_id = request.headers.get("x-request-id", str(uuid.uuid4()))
        started = time.perf_counter()
        path = request.url.path
        client_host = request.client.host if request.client else "unknown"

        auth_response = _authorize(request, settings, path)
        if auth_response is not None:
            response = auth_response
        elif path not in PUBLIC_PATHS and not limiter.allow(f"{client_host}:{path}"):
            response = JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded"},
                headers={"Retry-After": "60"},
            )
        else:
            response = await call_next(request)

        response.headers["X-Request-ID"] = request_id
        response.headers["X-RateLimit-Limit"] = str(limiter.limit_per_minute)

        latency_ms = int((time.perf_counter() - started) * 1000)
        logger.info(
            json.dumps(
                {
                    "request_id": request_id,
                    "method": request.method,
                    "path": path,
                    "status_code": response.status_code,
                    "latency_ms": latency_ms,
                    "client": client_host,
                }
            )
        )
        return response

    return middleware


def _authorize(request: Request, settings: Settings, path: str) -> JSONResponse | None:
    if path in PUBLIC_PATHS or not settings.api_key_required:
        return None
    if path == "/ask" and request.method == "POST" and settings.public_ask_enabled:
        return None
    if not settings.app_api_key:
        return JSONResponse(
            status_code=503,
            content={"detail": "API key auth enabled but APP_API_KEY is not configured"},
        )

    supplied = request.headers.get("x-api-key")
    authorization = request.headers.get("authorization", "")
    if authorization.lower().startswith("bearer "):
        supplied = authorization.split(" ", 1)[1]

    if supplied and secrets.compare_digest(supplied, settings.app_api_key):
        return None
    return JSONResponse(status_code=401, content={"detail": "Invalid or missing API key"})
