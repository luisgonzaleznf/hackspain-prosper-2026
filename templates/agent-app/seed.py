"""Deterministic seed data for the demo.

Keep this small and self-contained so the golden demo path is reproducible on
a clean checkout with no external services.
"""

from __future__ import annotations

SEED_DOCS: list[dict[str, str]] = [
    {
        "title": "Refund policy",
        "body": "Refunds are issued within 14 days of purchase, no questions asked.",
    },
    {
        "title": "Support hours",
        "body": "Support is available Monday to Friday, 9am-6pm Pacific.",
    },
    {
        "title": "Shipping",
        "body": "Standard shipping takes 3-5 business days; express takes 1-2.",
    },
    {
        "title": "Account security",
        "body": "Enable two-factor authentication from Settings > Security.",
    },
]

# A canned conversation starter used by the UI and the golden demo path.
DEMO_PROMPT = "What's your refund policy, and what time is it right now?"
