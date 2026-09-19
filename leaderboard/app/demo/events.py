"""Safe, replayable engineering events projected from the durable call JSONL."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app import config

_TOOL_LABELS = {
    "resolve_names": "Resolve clinic names",
    "find_patient": "Identify patient",
    "list_appointments": "Read appointment diary",
    "search_availability": "Search live availability",
    "record_booking": "Validate booking",
    "record_reschedule": "Validate appointment change",
    "record_cancellation": "Validate cancellation",
    "record_registration": "Validate registration",
    "record_no_action": "Validate refusal",
    "record_escalation": "Validate safety escalation",
    "clear_recorded_actions": "Clear prepared outcome",
}


def call_log_path(session_id: str) -> Path:
    if not session_id or any(char not in "0123456789abcdef-" for char in session_id.lower()):
        raise ValueError("invalid session id")
    return config.CALLS_DIR / f"{session_id}.jsonl"


def _detail(raw: Any) -> dict:
    if isinstance(raw, dict):
        return raw
    if not isinstance(raw, str):
        return {}
    try:
        value = json.loads(raw)
    except (TypeError, ValueError):
        return {}
    return value if isinstance(value, dict) else {}


def _tool_summary(name: str, result: Any) -> tuple[str, str]:
    if isinstance(result, dict) and result.get("error"):
        return "rejected", "Deterministic validation rejected the request"
    if name == "find_patient" and isinstance(result, dict):
        count = result.get("count")
        if isinstance(count, int):
            return "succeeded", f"Found {count} matching patient record{'s' if count != 1 else ''}"
    if name == "search_availability" and isinstance(result, dict):
        count = result.get("slots_found")
        if isinstance(count, int):
            return "succeeded", f"Found {count} eligible appointment time{'s' if count != 1 else ''}"
    if name == "list_appointments" and isinstance(result, dict):
        appointments = result.get("appointments")
        if isinstance(appointments, list):
            return "succeeded", f"Found {len(appointments)} upcoming appointment{'s' if len(appointments) != 1 else ''}"
    return "succeeded", _TOOL_LABELS.get(name, "Completed clinic operation")

def _participant(event_type: str) -> str:
    if event_type == "conversation.user":
        return "caller"
    if event_type == "conversation.agent":
        return "ai"
    if event_type.startswith("tool."):
        return "tools"
    if event_type.startswith("action."):
        return "state"
    if event_type.startswith("voice."):
        return "voice"
    return "brain"


def _event(base: dict, event_type: str, label: str, summary: str, status: str, **extra: Any) -> dict:
    return {
        **base,
        "type": event_type,
        "participant": _participant(event_type),
        "label": label,
        "summary": summary,
        "status": status,
        "details": {
            "event": event_type,
            "source": _participant(event_type),
            "recorded_at": base.get("at"),
            **({"operation": extra["tool"]} if extra.get("tool") else {}),
        },
        **extra,
    }


def project_event(row: dict, event_id: int) -> dict | None:
    kind = row.get("kind")
    base = {"id": event_id, "at": row.get("t")}
    if kind == "transcript":
        role = "agent" if row.get("role") in {"agent", "assistant"} else "user"
        text = str(row.get("text") or "").strip()
        return _event(base, f"conversation.{role}", "AI receptionist" if role == "agent" else "Caller", text, "complete") if text else None
    if kind == "tool":
        name = str(row.get("name") or "")
        status, summary = _tool_summary(name, row.get("result"))
        return _event(base, "tool.completed" if status == "succeeded" else "tool.rejected", _TOOL_LABELS.get(name, name), summary, status, tool=name)
    if kind == "action_staged":
        action = row.get("action") if isinstance(row.get("action"), dict) else {}
        verb = str(action.get("action") or "ACTION")
        return _event(base, "action.staged", f"{verb.replace('_', ' ').title()} prepared", "Passed deterministic checks and entered staged call state", "succeeded")
    if kind != "codex":
        return None
    event = str(row.get("event") or "")
    detail = _detail(row.get("detail"))
    if event == "delegation.created":
        return _event(base, "delegation.started", "Back office engaged", "Voice delegated the request for clinic reasoning", "running")
    if event == "item/started" and (detail.get("item") or {}).get("type") == "dynamicToolCall":
        name = str((detail.get("item") or {}).get("tool") or "")
        return _event(base, "tool.started", _TOOL_LABELS.get(name, name), "Calling checked clinic operation", "running", tool=name)
    if event == "voice.recovering":
        return _event(base, "voice.recovering", "Voice lane recovering", "Browser call and clinic state remain active", "running")
    if event == "voice.recovered":
        return _event(base, "voice.recovered", "Voice lane recovered", "Listening resumed on a fresh realtime connection", "succeeded")
    return None


def read_projected(session_id: str, after: int = 0) -> tuple[list[dict], int]:
    path = call_log_path(session_id)
    if not path.is_file():
        return [], after
    events: list[dict] = []
    last = after
    with path.open(encoding="utf-8") as log:
        for event_id, line in enumerate(log, start=1):
            if event_id <= after:
                continue
            last = event_id
            try:
                row = json.loads(line)
            except (TypeError, ValueError):
                continue
            if projected := project_event(row, event_id):
                events.append(projected)
    return events, last
