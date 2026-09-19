"""Read-only HTTP view of the per-call JSONL, for the ROSARIO console.

The console was built against this log format: `frontend/src/lib/types.ts` says the
field names are the backend's, verbatim, and every event kind it projects
(`transcript`, `tool`, `submit`, `action_staged`) is one `app/session.py` writes. So this
is an adapter over files we already own, not an integration.

    GET /api/calls            -> {calls_dir, calls: [CallSummary]}
    GET /api/calls/{id}       -> CallDetail
    GET /api/calls/{id}/audio -> the call's WAV, when one was recorded

Never mount this on the Prosper call server: that app goes under a public tunnel during a
run, and this exposes every transcript. `app/dashboard.py` serves it on its own port.
"""

import json
import wave
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app import config

# Chatter from the voice layer: kept in `events` for the timeline, never counted as a turn.
NOISE_KINDS = {"codex", "usage"}
# What the console renders as a warning badge on a call.
WARNING_KINDS = {"fallback", "error", "socket_closed", "stop_received"}


def _calls_dir() -> Path:
    return Path(config.CALLS_DIR)


def _audio_path(call_id: str) -> Path:
    return Path(config.AUDIO_DIR) / f"{call_id}.wav"


def _read(path: Path) -> list[dict[str, Any]]:
    """Parse one call's JSONL. A half-written last line of a live call is skipped."""
    events = []
    for number, line in enumerate(path.read_text(errors="replace").splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if isinstance(event, dict):
            event["_line"] = number
            events.append(event)
    return events


def _of_kind(events: list[dict[str, Any]], kind: str) -> list[dict[str, Any]]:
    return [e for e in events if e.get("kind") == kind]


def _warnings(events: list[dict[str, Any]]) -> list[str]:
    out = []
    for event in events:
        kind = event.get("kind")
        if kind in WARNING_KINDS:
            detail = event.get("reason") or event.get("error") or event.get("detail") or ""
            out.append(f"{kind}: {detail}".strip().rstrip(":"))
        elif kind == "submit" and int(event.get("status") or 0) >= 400:
            out.append(f"submit rejected: HTTP {event.get('status')}")
    return out


def _status(events: list[dict[str, Any]]) -> str:
    submits = _of_kind(events, "submit")
    if submits:
        codes = [int(s.get("status") or 0) for s in submits]
        return "submitted" if all(200 <= c < 300 for c in codes) else "rejected"
    if _of_kind(events, "call_ended"):
        return "ended"
    # The console's Live screen keys off this exact string (`isActive` in
    # frontend/src/lib/store.ts); do not reword it.
    return "in progress"


def _action(events: list[dict[str, Any]]) -> str:
    """What the call did, as the console's one-word column."""
    verbs = [str((s.get("action") or {}).get("action", "")) for s in _of_kind(events, "submit")]
    if not verbs:
        staged = _of_kind(events, "action_staged")
        verbs = [str((s.get("action") or {}).get("action", "")) for s in staged[-1:]]
    verbs = [v for v in verbs if v]
    return "+".join(dict.fromkeys(verbs)) if verbs else "—"


def _audio_info(call_id: str) -> dict[str, Any] | None:
    path = _audio_path(call_id)
    if not path.exists():
        return None
    try:
        with wave.open(str(path), "rb") as handle:
            frames, rate = handle.getnframes(), handle.getframerate()
            info = {
                "channels": handle.getnchannels(),
                "sample_rate": rate,
                "sample_width": handle.getsampwidth(),
                "frames": frames,
                "duration_seconds": round(frames / rate, 3) if rate else 0.0,
            }
    except (wave.Error, OSError):
        return None
    return {
        "url": f"/api/calls/{call_id}/audio",
        **info,
        "timeline_clock": None,
        "caller_carrier_drift_seconds": None,
    }


def _summary(path: Path, events: list[dict[str, Any]]) -> dict[str, Any]:
    call_id = path.stem
    stamps = [float(e["t"]) for e in events if isinstance(e.get("t"), int | float)]
    started = min(stamps) if stamps else path.stat().st_mtime
    modified = path.stat().st_mtime
    return {
        "call_id": call_id,
        "started_at": started,
        "modified_at": modified,
        "modified_iso": datetime.fromtimestamp(modified, UTC).isoformat(),
        "status": _status(events),
        "action": _action(events),
        "duration_seconds": round(max(stamps) - started, 3) if stamps else None,
        "warnings": len(_warnings(events)),
        "has_audio": _audio_path(call_id).exists(),
        "run": None,  # Prosper does not tell us its run id on the call.
    }


def _provenance(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Tie each submitted action back to the staging event and the lookup behind it."""
    staged = _of_kind(events, "action_staged")
    tools = _of_kind(events, "tool")
    chains = []
    for submit in _of_kind(events, "submit"):
        action = submit.get("action") or {}
        recorded = next((s for s in staged if (s.get("action") or {}) == action), None)
        before = recorded.get("_line") if recorded else submit.get("_line")
        lookup = next((t for t in reversed(tools) if t.get("_line", 0) < (before or 0)), None)
        chains.append({"lookup": lookup, "recorded": recorded, "submit": submit, "action": action})
    return chains


def _detail(path: Path) -> dict[str, Any]:
    events = _read(path)
    call_id = path.stem
    return {
        "call_id": call_id,
        "summary": _summary(path, events),
        "run": None,
        "warnings": _warnings(events),
        "audio": _audio_info(call_id),
        "transcript": _of_kind(events, "transcript"),
        "tools": _of_kind(events, "tool"),
        "staged_actions": _of_kind(events, "action_staged"),
        "submissions": _of_kind(events, "submit"),
        "errors": [e for e in events if e.get("kind") in WARNING_KINDS],
        "provenance": _provenance(events),
        "events": [e for e in events if e.get("kind") not in NOISE_KINDS],
    }


router = APIRouter(prefix="/api/calls", tags=["calls"])


@router.get("")
def list_calls() -> dict[str, Any]:
    directory = _calls_dir()
    calls = []
    for path in directory.glob("*.jsonl"):
        try:
            calls.append(_summary(path, _read(path)))
        except OSError:
            continue  # a file being written right now; it shows up on the next poll
    calls.sort(key=lambda c: c["started_at"], reverse=True)
    return {"calls_dir": str(directory.resolve()), "calls": calls}


@router.get("/{call_id}")
def get_call(call_id: str) -> dict[str, Any]:
    path = _calls_dir() / f"{call_id}.jsonl"
    if not path.is_file() or path.parent.resolve() != _calls_dir().resolve():
        raise HTTPException(404, f"No log for call {call_id}.")
    return _detail(path)


@router.get("/{call_id}/audio")
def get_audio(call_id: str) -> FileResponse:
    path = _audio_path(call_id)
    if not path.is_file() or path.parent.resolve() != Path(config.AUDIO_DIR).resolve():
        raise HTTPException(404, f"No recording for call {call_id}.")
    return FileResponse(path, media_type="audio/wav")
