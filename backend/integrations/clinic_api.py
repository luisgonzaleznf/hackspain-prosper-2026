"""Local-only console view of the clinic diary; no public voice-server route.

    GET /api/clinic/calendar?from=YYYY-MM-DD&to=YYYY-MM-DD   (default today-7 .. today+35)

One window of the diary from the clinic database: every appointment in it (booked and
cancelled), the doctors and sites to filter by, and the absences and closures to paint.
A record with a `callId` was booked, moved or cancelled by a call; the rest is the diary.
"""

import json
from datetime import date, datetime, timedelta

from app import clinic, config
from fastapi import APIRouter, HTTPException, Query
from loguru import logger

from integrations.local_store import LocalStore

router = APIRouter(prefix="/api/clinic")

DAYS_BEFORE, DAYS_AFTER = 7, 35  # the default window around today
MAX_DAYS = 62


def _day(slot: str | None) -> str | None:
    return datetime.fromisoformat(slot).astimezone(config.TZ).date().isoformat() if slot else None


def _logged(call_id: str | None) -> bool:
    return bool(call_id) and (config.CALLS_DIR / f"{call_id}.jsonl").is_file()


def _end(a: dict) -> str | None:
    if not a.get("start_time") or not a.get("duration_minutes"):
        return None
    start = datetime.fromisoformat(a["start_time"])
    return (start + timedelta(minutes=int(a["duration_minutes"]))).isoformat(timespec="seconds")


def _record(a: dict, names: dict[str, str]) -> dict:
    call_id = a.get("call_id")
    provider_id = a.get("provider_id")
    location_id = a.get("location_id")
    return {
        "id": a["appointment_id"],
        "appointmentId": a["appointment_id"],
        "callId": call_id,
        "kind": "CANCEL" if a.get("status") == "cancelled" else "BOOK",
        "recordedAt": a.get("updated_at"),
        "slot": a.get("start_time"),
        "previousSlot": None,
        "day": _day(a.get("start_time")),
        "patient": a.get("patient_name") or a.get("patient_id"),
        "patientId": a.get("patient_id"),
        "caller": None,
        "provider": a.get("provider_name") or names.get(provider_id or "", provider_id),
        "site": names.get(location_id or "", location_id),
        "supersededBy": None,
        "practice": False,
        "persisted": True,
        "providerId": provider_id,
        "specialtyId": a.get("specialty_id"),
        "durationMinutes": a.get("duration_minutes"),
        "end": _end(a),
        "appointmentType": a.get("appointment_type_id"),
        "status": a.get("status"),
        "source": "call" if call_id else "diary",
        "callLogged": _logged(call_id),
    }


def _order(record: dict) -> tuple[float, float]:
    slot = record.get("slot")
    return (
        datetime.fromisoformat(slot).timestamp() if slot else float("inf"),
        record.get("recordedAt") or 0.0,
    )


def _window(start: str | None, end: str | None) -> tuple[date, date]:
    today = datetime.now(config.TZ).date()
    try:
        first = date.fromisoformat(start) if start else today - timedelta(days=DAYS_BEFORE)
        last = date.fromisoformat(end) if end else today + timedelta(days=DAYS_AFTER)
    except ValueError:
        raise HTTPException(422, "from and to must be YYYY-MM-DD") from None
    if last < first:
        raise HTTPException(422, "to is before from")
    if (last - first).days + 1 > MAX_DAYS:
        raise HTTPException(422, f"at most {MAX_DAYS} days at a time")
    return first, last


@router.get("/calendar")
async def calendar(
    start: str | None = Query(None, alias="from"), end: str | None = Query(None, alias="to")
) -> dict:
    first, last = _window(start, end)
    span = (first.isoformat(), last.isoformat())
    catalogue: dict = {}
    try:
        catalogue = await clinic.catalogue()
    except Exception as e:  # ids still make a usable calendar
        logger.warning(f"calendar: clinic catalogue unavailable: {e!r}")
    providers = [
        {
            "id": p["id"],
            "name": p["name"],
            "specialtyId": p.get("specialty_id"),
            "specialtyName": p.get("specialty_name"),
        }
        for p in catalogue.get("providers", [])
    ]
    locations = [{"id": loc["id"], "name": loc["name"]} for loc in catalogue.get("locations", [])]
    names = {p["id"]: p["name"] for p in providers} | {loc["id"]: loc["name"] for loc in locations}
    store = LocalStore()
    with store.connect() as db:
        absences = [
            {
                "providerId": row["provider_id"],
                "start": row["start_date"],
                "end": row["end_date"],
                "startTime": row["start_time"],
                "endTime": row["end_time"],
                "reason": row["reason"],
            }
            for row in db.execute(
                "SELECT provider_id, start_date, end_date, start_time, end_time, reason "
                "FROM absences WHERE start_date <= ? AND end_date >= ? "
                "ORDER BY start_date, provider_id",
                (span[1], span[0]),
            )
        ]
        closures = [
            {"date": row["date"], "locationId": row["location_id"], "name": row["name"]}
            for row in db.execute(
                "SELECT date, location_id, name FROM closures WHERE date BETWEEN ? AND ? "
                "ORDER BY date, location_id",
                span,
            )
        ]
        rows = db.execute(
            "SELECT data, status FROM appointments WHERE start_date BETWEEN ? AND ?", span
        ).fetchall()
    records = [_record({**json.loads(row["data"]), "status": row["status"]}, names) for row in rows]
    return {
        "from": span[0],
        "to": span[1],
        "providers": providers,
        "locations": locations,
        "absences": absences,
        "closures": closures,
        "records": sorted(records, key=_order),
    }
