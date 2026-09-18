"""Example tools for the agent loop.

Each tool is a plain Python function plus a JSON-schema definition the model
sees. Keep tools small and deterministic so the demo is reproducible.
"""

from __future__ import annotations

import datetime as _dt
import json
from typing import Any, Callable

from seed import SEED_DOCS

# ---------------------------------------------------------------------------
# Tool implementations
# ---------------------------------------------------------------------------


def get_time(timezone: str = "UTC") -> str:
    """Return a deterministic-ish current time string.

    For the demo we don't actually resolve timezones — we just echo the label
    back with a fixed clock so the golden path is reproducible. Swap in
    `zoneinfo` here if you need real timezone math.
    """
    now = _dt.datetime(2026, 6, 21, 14, 30, 0)
    return f"The current time in {timezone} is {now.strftime('%Y-%m-%d %H:%M:%S')}."


def search(query: str) -> str:
    """Fake search over a tiny seeded corpus.

    Returns the best-matching seed doc(s) by naive substring/keyword overlap.
    Replace this with a real retriever (see recipes/rag.md) for production.
    """
    q = query.lower()
    scored: list[tuple[int, dict[str, str]]] = []
    for doc in SEED_DOCS:
        haystack = f"{doc['title']} {doc['body']}".lower()
        score = sum(1 for term in q.split() if term in haystack)
        if score:
            scored.append((score, doc))

    if not scored:
        return f"No results found for {query!r}."

    scored.sort(key=lambda pair: pair[0], reverse=True)
    top = [doc for _, doc in scored[:2]]
    return "\n".join(f"- {doc['title']}: {doc['body']}" for doc in top)


# ---------------------------------------------------------------------------
# Tool registry: name -> (callable, JSON schema for the Anthropic API)
# ---------------------------------------------------------------------------

TOOL_FUNCTIONS: dict[str, Callable[..., str]] = {
    "get_time": get_time,
    "search": search,
}

TOOL_SCHEMAS: list[dict[str, Any]] = [
    {
        "name": "get_time",
        "description": (
            "Get the current date and time. Call this when the user asks what "
            "time or day it is, or needs the current timestamp."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "timezone": {
                    "type": "string",
                    "description": "IANA timezone label, e.g. 'UTC' or 'America/New_York'.",
                }
            },
            "required": [],
        },
    },
    {
        "name": "search",
        "description": (
            "Search the internal knowledge base for facts. Call this when the "
            "user asks about something that may be in the docs rather than "
            "general knowledge."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "What to look up.",
                }
            },
            "required": ["query"],
        },
    },
]


def run_tool(name: str, tool_input: dict[str, Any]) -> str:
    """Dispatch a tool call by name, returning a string result.

    Errors are returned as strings (not raised) so the loop can hand them back
    to the model as a tool_result with is_error=True.
    """
    fn = TOOL_FUNCTIONS.get(name)
    if fn is None:
        return f"Error: unknown tool {name!r}."
    try:
        return fn(**tool_input)
    except TypeError as exc:
        return f"Error: bad arguments for {name!r}: {exc}. Got {json.dumps(tool_input)}."
    except Exception as exc:  # noqa: BLE001 - surface any tool failure to the model
        return f"Error running {name!r}: {exc}"
