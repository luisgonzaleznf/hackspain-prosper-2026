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

# Error text that means the model provider refused for lack of payment/quota,
# not a transient outage: auth failures on a key that worked before, quota and
# billing language, and OpenAI's insufficient_quota code.
_CREDIT = re.compile(
    r"insufficient_quota|quota exceeded|billing|exceeded your current quota|"
    r"usage limit|usage_cap|rate limit exceeded|401|429",
    re.IGNORECASE,
)

# Transient/noise strings that must not read as exhaustion even though they
# mention a matched word (e.g. a 429 that is plain per-minute throttling on a
# healthy account is still "the demo cannot run right now" for the console).
_TRANSIENT = re.compile(r"temporary|retry|backoff", re.IGNORECASE)


def classify_error(text: str) -> dict | None:
    """`{"provider": ..., "detail": ...}` when the error reads as exhausted credits."""
    if not text or _TRANSIENT.search(text):
        return None
    if not _CREDIT.search(text):
        return None
    provider = "codex" if "codex" in text.lower() or "thread" in text.lower() else "openai"
    return {"provider": provider, "detail": text[:300]}
