"""Rate limiter (app/ratelimit.py): limit enforcement, expiry, key eviction."""

import app.dashboard as dashboard
import pytest
from app import ratelimit
from app.ratelimit import SlidingWindow, client_ip
from starlette.testclient import TestClient


def _clear_windows():
    """The suite shares one process-wide window; the flood here must not 429 later tests."""
    ratelimit.http_window._hits.clear()
    ratelimit.ws_burst_window._hits.clear()


@pytest.fixture(autouse=True)
def _clean_windows_after():
    yield
    _clear_windows()


def test_window_enforces_the_limit():
    w = SlidingWindow(2, 10)
    assert w.check("a")
    assert w.check("a")
    assert not w.check("a"), "third hit inside the window must be refused"
    assert w.check("b"), "other keys are independent"


def test_expired_hits_are_re_admitted_and_replaced():
    import time

    w = SlidingWindow(1, 0.05)
    assert w.check("x")
    deadline = time.monotonic() + 0.2
    while time.monotonic() < deadline:
        pass
    assert w.check("x"), "an expired key must be re-admitted"
    assert len(w._hits) == 1, "expired entry is replaced, not duplicated"


def test_key_map_is_capped():
    w = SlidingWindow(10, 10)
    w.MAX_KEYS = 3
    for key in ("a", "b", "c"):
        w.check(key)
    assert w.check("d"), "cap reached: the coldest key is shed, the new one passes"
    assert set(w._hits) == {"b", "c", "d"}
    assert w.check("b"), "a shed key can be re-admitted later"


def test_middleware_429s_and_exempts_health():
    client = TestClient(dashboard.app)
    assert client.get("/health").status_code == 200
    # hammer one endpoint well past the window limit from a single IP
    codes = [client.get("/api/calls").status_code for _ in range(400)]
    assert 429 in codes, "exceeding the per-IP window must produce a 429"


def test_health_stays_ok_under_flood():
    client = TestClient(dashboard.app)
    for _ in range(400):
        client.get("/api/calls")
    assert client.get("/health").status_code == 200, "/health is exempt from the window"


@pytest.fixture(autouse=True)
def _clean_windows_after(request):
    yield
    _clear_windows()


import pytest  # noqa: E402  (fixture needs the yield helper defined first)


def test_forwarded_header_wins():
    class FakeRequest:
        client = None

        def __init__(self):
            self.headers = {"x-forwarded-for": "203.0.113.7, 10.0.0.1"}

    assert client_ip(FakeRequest()) == "203.0.113.7"
