"""Local-only console view of the agent's appointments; no public voice-server route.

Two feeds, merged into one calendar:

- the SQLite overlay: bookings the Twilio receptionist wrote for real (`source: "local"`);
- Prosper's `/api/v1/submissions`: every BOOK, RESCHEDULE and CANCEL this API key reported
  and the scorer accepted (`source: "prosper"`). Prosper's EHR is read-only, so its
  per-patient diary never shows these; the submissions list is the only Prosper-side record.

Prosper names patients and appointments by id only. A name comes from the call's own log when
it lives on this host (find_patient / list_appointments results), else from an exact directory
lookup seeded with the published practice personas — a demo shortcut, never the record itself.
"""

import asyncio
import json
import time
from datetime import datetime
from pathlib import Path

from app import clinic, config, prosper
from fastapi import APIRouter
from loguru import logger

from integrations.local_store import LocalStore

router = APIRouter(prefix="/api/clinic")

PUBLIC_CASES = Path(__file__).resolve().parents[1] / "docs/prosper/data/public-cases.json"
SUBMISSIONS_LIMIT = 200  # Prosper's cap
SUBMISSIONS_TTL = 10.0  # seconds; the console polls every 5 s and Prosper is not ours to hammer
CALENDAR_KINDS = {"BOOK", "RESCHEDULE", "CANCEL"}

_names: dict[str, str] | None = None  # patient_id -> full name, built once per process
_names_lock = asyncio.Lock()
_submissions: tuple[float, list[dict]] | None = None


def _day(slot: str | None) -> str | None:
    return datetime.fromisoformat(slot).astimezone(config.TZ).date().isoformat() if slot else None


def _catalogue_names(catalogue: dict | None) -> dict[str, str]:
    if not catalogue:
        return {}
    return {p["id"]: p["name"] for p in catalogue["providers"]} | {
        loc["id"]: loc["name"] for loc in catalogue["locations"]
    }


def _logged(call_id: str) -> bool:
    return bool(call_id) and (config.CALLS_DIR / f"{call_id}.jsonl").is_file()


def _local_records(names: dict[str, str]) -> list[dict]:
    records = []
    for a in LocalStore().appointments(include_cancelled=True):
        records.append(
            {
                "id": a["appointment_id"],
                "appointmentId": a["appointment_id"],
                "callId": a["call_id"],
                "kind": "CANCEL" if a["status"] == "cancelled" else "BOOK",
                "recordedAt": a["updated_at"],
                "slot": a["start_time"],
                "previousSlot": None,
                "day": _day(a["start_time"]),
                "patient": a["patient_name"],
                "patientId": a["patient_id"],
                "caller": None,
                "provider": a.get("provider_name", a["provider_id"]),
                "site": names.get(a["location_id"], a["location_id"]),
                "supersededBy": None,
                "practice": False,
                "persisted": True,
                "source": "local",
                "callLogged": _logged(a["call_id"]),
            }
        )
    return records


def _call_log(call_id: str) -> dict:
    """What the call itself looked up, when its log is on this host: patient names by id and
    the appointments it listed (a RESCHEDULE/CANCEL names only an appointment_id)."""
    facts: dict = {"logged": _logged(call_id), "patients": {}, "appointments": {}}
    if not facts["logged"]:
        return facts
    for line in (config.CALLS_DIR / f"{call_id}.jsonl").read_text(errors="replace").splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if not isinstance(event, dict) or event.get("kind") != "tool":
            continue
        result = event.get("result") if isinstance(event.get("result"), dict) else {}
        if event.get("name") == "find_patient":
            for match in result.get("matches") or []:
                if isinstance(match, dict) and match.get("patient_id") and match.get("name"):
                    facts["patients"][match["patient_id"]] = match["name"]
        elif event.get("name") == "list_appointments":
            for appointment in result.get("appointments") or []:
                if isinstance(appointment, dict) and appointment.get("appointment_id"):
                    facts["appointments"][appointment["appointment_id"]] = appointment
    return facts


def _persona_national_ids() -> list[str]:
    """Every DNI/NIE the published practice cases mention: callers and the patients they call for."""
    try:
        cases = json.loads(PUBLIC_CASES.read_text())["cases"]
    except (OSError, ValueError, KeyError, TypeError):
        return []
    ids: list[str] = []
    for case in cases:
        data = ((case or {}).get("persona") or {}).get("data") or {}
        for key, value in data.items():
            if key.endswith("national_id") and isinstance(value, str) and value not in ids:
                ids.append(value)
    return ids


async def _patient_names() -> dict[str, str]:
    """patient_id -> full name for the practice personas: one exact directory lookup each, once.

    Cached for the process once any lookup succeeds; a fully failed batch is retried next time.
    """
    global _names
    async with _names_lock:
        if _names is not None:
            return _names
        names: dict[str, str] = {}
        failures = 0
        client = prosper.client()
        limiter = asyncio.Semaphore(8)

        async def lookup(national_id: str) -> None:
            nonlocal failures
            async with limiter:
                try:
                    matches = await client.directory(national_id=national_id)
                except Exception as e:  # a missing name never hides an appointment
                    failures += 1
                    logger.warning(f"calendar: directory lookup failed: {e!r}")
                    return
            for m in matches:
                full = f"{m.get('given_name', '')} {m.get('first_surname', '')} {m.get('second_surname', '')}"
                if m.get("patient_id") and full.strip():
                    names[m["patient_id"]] = " ".join(full.split())

        await asyncio.gather(*(lookup(nid) for nid in _persona_national_ids()))
        if names or not failures:
            _names = names
        return names


async def _submissions_feed() -> list[dict]:
    global _submissions
    now = time.monotonic()
    if _submissions and now - _submissions[0] < SUBMISSIONS_TTL:
        return _submissions[1]
    feed = await prosper.client().submissions(SUBMISSIONS_LIMIT)
    _submissions = (now, feed)
    return feed


async def _prosper_records(catalogue: dict[str, str]) -> list[dict]:
    submissions = await _submissions_feed()
    names = await _patient_names()
    records = []
    for submission in submissions:
        call_id = str(submission.get("call_id") or "")
        received = submission.get("received_at")
        recorded_at = datetime.fromisoformat(received).timestamp() if received else 0.0
        actions = ((submission.get("record") or {}).get("actions")) or []
        log = _call_log(call_id)
        for index, action in enumerate(actions):
            kind = action.get("action")
            if kind not in CALENDAR_KINDS:
                continue
            appointment_id = action.get("appointment_id")
            known = log["appointments"].get(appointment_id, {}) if appointment_id else {}
            patient_id = action.get("patient_id") or known.get("patient_id")
            slot = action.get("slot") if kind != "CANCEL" else known.get("start_time")
            provider_id = action.get("provider_id") or known.get("provider_id")
            location_id = action.get("location_id") or known.get("location_id")
            patient = (
                log["patients"].get(patient_id)
                or names.get(patient_id)
                or patient_id
                or (f"Appointment {appointment_id}" if appointment_id else "Patient not identified")
            )
            records.append(
                {
                    "id": f"prosper:{call_id}:{index}",
                    "appointmentId": appointment_id,
                    "callId": call_id,
                    "kind": kind,
                    "recordedAt": recorded_at,
                    "slot": slot,
                    "previousSlot": known.get("start_time") if kind == "RESCHEDULE" else None,
                    "day": _day(slot),
                    "patient": patient,
                    "patientId": patient_id,
                    "caller": None,
                    "provider": catalogue.get(provider_id, provider_id),
                    "site": catalogue.get(location_id, location_id),
                    "supersededBy": None,
                    "practice": False,
                    "persisted": False,
                    "source": "prosper",
                    "callLogged": log["logged"],
                }
            )
    return records


def _order(record: dict) -> tuple[float, float]:
    slot = record.get("slot")
    return (
        datetime.fromisoformat(slot).timestamp() if slot else float("inf"),
        record["recordedAt"],
    )


@router.get("/calendar")
async def calendar() -> dict:
    catalogue: dict[str, str] = {}
    try:
        catalogue = _catalogue_names(await clinic.catalogue())
    except Exception as e:  # ids still make a usable calendar
        logger.warning(f"calendar: clinic catalogue unavailable: {e!r}")
    records = _local_records(catalogue)
    feed: dict = {"ok": True, "count": 0, "detail": None}
    try:
        reported = await _prosper_records(catalogue)
    except Exception as e:  # the saved bookings must show even when Prosper does not answer
        logger.warning(f"calendar: Prosper submissions unavailable: {e!r}")
        feed = {"ok": False, "count": 0, "detail": str(e)}
        reported = []
    saved = {(r["callId"], r["kind"], r["slot"]) for r in records}
    reported = [r for r in reported if (r["callId"], r["kind"], r["slot"]) not in saved]
    feed["count"] = len(reported)
    return {
        "records": sorted(records + reported, key=_order),
        "sources": {"local": len(records), "prosper": feed},
    }
