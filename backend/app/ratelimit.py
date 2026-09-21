"""In-memory rate limiting for the public surfaces.

One sliding window per client IP for HTTP (both FastAPI apps), plus concurrent
and burst caps on /ws: every accepted call socket burns voice credits, so a
looping client must be shut out before the pipeline starts. Per-IP state lives
in the process; the demo is one host by design (see README "Scaling up").
"""

from __future__ import annotations

import os
import time
from collections import defaultdict, deque

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

HTTP_LIMIT = int(os.getenv("RATE_LIMIT_HTTP", "300"))  # requests ...
HTTP_WINDOW = float(os.getenv("RATE_LIMIT_HTTP_WINDOW", "10"))  # ... per this many seconds
WS_BURST = int(os.getenv("RATE_LIMIT_WS", "6"))  # call sockets ...
WS_BURST_WINDOW = 60.0  # ... per minute
MAX_CONCURRENT_CALLS = int(os.getenv("MAX_CONCURRENT_CALLS", "10"))  # process-wide
MAX_CALLS_PER_IP = int(os.getenv("MAX_CALLS_PER_IP", "3"))  # per client IP


def client_ip(request: Request) -> str:
    """The tunnel (ngrok) forwards the real caller in X-Forwarded-For."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


class SlidingWindow:
    """Per-key sliding window: True when the hit is allowed."""

    def __init__(self, limit: int, window: float):
        self.limit, self.window = limit, window
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def check(self, key: str) -> bool:
        now = time.monotonic()
        hits = self._hits[key]
        while hits and now - hits[0] > self.window:
            hits.popleft()
        if len(hits) >= self.limit:
            return False
        hits.append(now)
        return True


http_window = SlidingWindow(HTTP_LIMIT, HTTP_WINDOW)
ws_burst_window = SlidingWindow(WS_BURST, WS_BURST_WINDOW)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Per-IP sliding window on every HTTP request; 429 with Retry-After on excess."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if not http_window.check(client_ip(request)):
            return JSONResponse(
                {"detail": "Too many requests"}, status_code=429, headers={"Retry-After": str(int(HTTP_WINDOW))}
            )
        return await call_next(request)


class CallLimitExceeded(Exception):
    """The call socket was refused before any pipeline started."""


def check_call_admission(ip: str, active: set[str]) -> None:
    """Raise CallLimitExceeded when this client or the host is over its call budget."""
    if len(active) >= MAX_CONCURRENT_CALLS:
        raise CallLimitExceeded("host is at its concurrent-call limit")
    if not ws_burst_window.check(ip):
        raise CallLimitExceeded("too many call attempts from this address")
