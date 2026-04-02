"""Simple in-memory rate-limiting middleware for FastAPI.

Uses a sliding-window counter per client IP. Configure via environment
variables:

  RATE_LIMIT_RPM   – max requests per minute per IP (default: 120)
  RATE_LIMIT_BURST – max burst size above steady rate (default: 20)
"""

from __future__ import annotations

import os
import time
from collections import defaultdict

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

_RPM = int(os.environ.get("RATE_LIMIT_RPM", "120"))
_BURST = int(os.environ.get("RATE_LIMIT_BURST", "20"))
_WINDOW = 60.0  # seconds


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Per-IP sliding-window rate limiter."""

    def __init__(self, app, rpm: int = _RPM, burst: int = _BURST):
        super().__init__(app)
        self.rpm = rpm
        self.burst = burst
        self._hits: dict[str, list[float]] = defaultdict(list)

    def _client_ip(self, request: Request) -> str:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    def _prune(self, key: str, now: float) -> int:
        entries = self._hits[key]
        cutoff = now - _WINDOW
        # Remove expired entries
        while entries and entries[0] < cutoff:
            entries.pop(0)
        return len(entries)

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # Skip rate limiting for health checks and metrics
        if request.url.path in ("/api/health", "/metrics"):
            return await call_next(request)

        ip = self._client_ip(request)
        now = time.monotonic()
        count = self._prune(ip, now)

        limit = self.rpm + self.burst
        if count >= limit:
            return Response(
                content='{"detail":"rate limit exceeded"}',
                status_code=429,
                media_type="application/json",
                headers={
                    "Retry-After": str(int(_WINDOW)),
                    "X-RateLimit-Limit": str(limit),
                    "X-RateLimit-Remaining": "0",
                },
            )

        self._hits[ip].append(now)
        response = await call_next(request)
        remaining = max(0, limit - count - 1)
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        return response
