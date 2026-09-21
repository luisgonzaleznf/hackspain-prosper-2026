"""Credit-exhaustion detection: classify voice-layer failures the console can surface.

When the OpenAI key is out of credits (401/429 quota errors) or the Codex
subscription hits its usage cap, calls die at session start. The voice layers
log a `voice.credits` event for those; `calls_api` lifts it into the call
summary and the console shows the "demo finished" popup. Twilio exhaustion is
not detectable here: inbound calls then never reach the app at all, and the
demo deliberately holds no Twilio API credentials.
"""

from __future__ import annotations

import re

# Error text that means the model provider refused for lack of payment/quota.
# Deliberately narrow: bare status codes ("401", "429") and plain throttling
# phrases ("rate limit exceeded") also fire for a revoked key or a temporary
# throttle on a healthy account, which the console would misreport as
# exhaustion. Only explicit quota/billing language counts.
_CREDIT = re.compile(
    r"insufficient_quota|quota exceeded|exceeded your current quota|"
    r"billing|usage limit|usage_cap",
    re.IGNORECASE,
)

# Transient/noise strings that must not read as exhaustion even though they
# mention a matched word (e.g. "billing" inside a transient-error body).
_TRANSIENT = re.compile(r"temporary|retry|backoff", re.IGNORECASE)


def classify_error(text: str) -> dict | None:
    """`{"provider": ..., "detail": ...}` when the error reads as exhausted credits."""
    if not text or _TRANSIENT.search(text):
        return None
    if not _CREDIT.search(text):
        return None
    provider = "codex" if "codex" in text.lower() or "thread" in text.lower() else "openai"
    return {"provider": provider, "detail": text[:300]}
