"""The clinic catalogue and the text the model reads.

The static part (sites, doctors, specialties, types, plans, rules) lives in the clinic database
(`meta.catalogue`, written by `make seed`). The live part is computed for today in Madrid: the
bookable calendar, closures, each doctor's absences, and counts. It is cached and recomputed
when the Madrid date or the database file changes.

Also the pure helpers the checks rely on: the DNI/NIE check letter and the dated calendar.
"""

import json
import re
from datetime import date, datetime, timedelta
from typing import Any

from integrations.local_store import LocalStore

from app import config

MAX_SPAN_DAYS = 14
SLOT_MINUTES = 15


class ClinicError(Exception):
    """A clinic read the model has to hear about, carrying a status and a detail for it."""

    def __init__(self, status: int, detail: Any):
        super().__init__(f"{status}: {detail}")
        self.status = status
        self.detail = detail


# Tests set `_catalogue` to a fixed dict; any dict this module did not build is used as-is.
_catalogue: dict | None = None
_built: dict | None = None
_built_key: tuple | None = None


def _key(store: LocalStore) -> tuple:
    try:
        stamp = store.path.stat().st_mtime_ns
    except OSError:
        stamp = None
    return datetime.now(config.TZ).date(), str(store.path), stamp


def load() -> dict:
    """The catalogue for today: a test's fixed dict, the cached one, or a fresh build."""
    global _catalogue, _built, _built_key
    if _catalogue is not None and _catalogue is not _built:
        return _catalogue
    store = LocalStore()
    key = _key(store)
    if _catalogue is None or key != _built_key:
        _catalogue = _built = build(store, key[0])
        _built_key = key
    return _catalogue


async def catalogue() -> dict:
    return load()


def cached() -> dict | None:
    """The catalogue if it has been loaded, for code that must not touch the database."""
    return _catalogue


def build(store: LocalStore, today: date) -> dict:
    """meta.catalogue plus calendar, closures, absences and counts as of `today`."""
    with store.connect() as db:
        meta = {row["key"]: row["value"] for row in db.execute("SELECT key, value FROM meta")}
        if "catalogue" not in meta:
            raise ClinicError(503, "The clinic database is not seeded. Run `make seed`.")
        cat = json.loads(meta["catalogue"])
        ends = meta.get("horizon_end") or (today + timedelta(days=27)).isoformat()
        closures = [
            {"date": row["date"], "location_id": row["location_id"], "name": row["name"]}
            for row in db.execute(
                "SELECT date, location_id, name FROM closures WHERE date BETWEEN ? AND ? "
                "ORDER BY date, location_id",
                (today.isoformat(), ends),
            )
        ]
        absences = db.execute(
            "SELECT provider_id, start_date, end_date, start_time, end_time, reason "
            "FROM absences WHERE end_date >= ? ORDER BY start_date, start_time",
            (today.isoformat(),),
        ).fetchall()
        booked = db.execute(
            "SELECT COUNT(*) FROM appointments WHERE status='booked' AND start_date >= ?",
            (today.isoformat(),),
        ).fetchone()[0]
        patients = db.execute("SELECT COUNT(*) FROM patients").fetchone()[0]
    sites = {loc["id"] for loc in cat["locations"]}
    closed: dict[str, set] = {}
    for c in closures:
        closed.setdefault(c["date"], set()).update(
            sites if c["location_id"] is None else {c["location_id"]}
        )
    cat["calendar"] = {
        "starts": today.isoformat(),
        "ends": ends,
        "max_span_days": MAX_SPAN_DAYS,
        "slot_minutes": SLOT_MINUTES,
        "closure_days": sorted(day for day, where in closed.items() if where >= sites),
        "closures": closures,
        "appointment_count": booked,
    }
    cat["patient_count"] = patients
    for p in cat["providers"]:
        mine = [
            {
                "start": a["start_date"],
                "end": a["end_date"],
                "start_time": a["start_time"],
                "end_time": a["end_time"],
                "reason": a["reason"],
            }
            for a in absences
            if a["provider_id"] == p["id"]
        ]
        p["absences"] = mine
        whole = [a for a in mine if a["start_time"] is None]
        p["leave"] = {k: whole[0][k] for k in ("start", "end", "reason")} if whole else None
    return cat


# ── National id ─────────────────────────────────────────────────────

_ID_LETTERS = "TRWAGMYFPDXBNJZSQVHLCKE"


def normalize_national_id(raw: str) -> str:
    """'x-1234567-l' -> 'X1234567L': separators and case never tell two people apart."""
    return re.sub(r"[^0-9A-Za-z]", "", raw).upper()


def national_id_valid(raw: str) -> bool:
    """DNI (8 digits + letter) or NIE (X/Y/Z + 7 digits + letter) with a matching check letter.

    The check letter is what separates a misheard digit from the real number.
    """
    m = re.fullmatch(r"([XYZ]?)(\d+)([A-Z])", normalize_national_id(raw))
    if not m:
        return False
    prefix, digits, letter = m.groups()
    if prefix:
        if len(digits) != 7:
            return False
        number = int(str("XYZ".index(prefix)) + digits)
    else:
        if len(digits) != 8:
            return False
        number = int(digits)
    return _ID_LETTERS[number % 23] == letter


# ── Text for the model ──────────────────────────────────────────────

_WEEKDAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]


def _week(days: list[dict]) -> str:
    """[{weekday, intervals}] -> 'Mon/Tue/Wed 09:00-14:00; Sat 09:00-13:00', grouped by identical hours."""
    groups: dict[str, list[str]] = {}
    for d in sorted(days, key=lambda d: _WEEKDAYS.index(d["weekday"])):
        groups.setdefault(", ".join(d["intervals"]), []).append(d["weekday"][:3].title())
    return "; ".join(f"{'/'.join(names)} {hours}" for hours, names in groups.items())


def _short(day: str) -> str:
    d = date.fromisoformat(day)
    return f"{d:%a} {d.day} {d:%b}"


def _away(p: dict, today: date | None) -> list[str]:
    """Current and future absences: 'AWAY 2026-09-30 to 2026-10-02 (congress)' or, for part of
    a day, 'AWAY Fri 2 Oct 12:00-14:00 (personal)'."""
    absences = p.get("absences")
    if absences is None:  # a catalogue with only the single `leave` window
        absences = [p["leave"]] if p.get("leave") else []
    lines = []
    for a in absences:
        if today and date.fromisoformat(a["end"]) < today:
            continue
        if a.get("start_time"):
            days = _short(a["start"]) + (
                "" if a["end"] == a["start"] else f" to {_short(a['end'])}"
            )
            lines.append(f"AWAY {days} {a['start_time']}-{a['end_time']} ({a['reason']})")
        else:
            days = a["start"] + ("" if a["end"] == a["start"] else f" to {a['end']}")
            lines.append(f"AWAY {days} ({a['reason']})")
    return lines


def render_catalogue(cat: dict, today: date | None = None) -> str:
    """Compact reference the model keeps in its prompt: ids are what the record_* tools take."""
    lines = ["SITES (location_id):"]
    for loc in cat["locations"]:
        uncovered = ", ".join(p["id"] for p in loc["not_covered_by"]) or "none"
        lines.append(
            f"- {loc['id']}: {loc['name']}, {loc['address']}. Open {_week(loc['hours'])}. "
            f"Plans NOT accepted at this site: {uncovered}."
        )
        if "latitude" in loc and "longitude" in loc:
            lines.append(
                f"  Coordinates: {loc['latitude']}, {loc['longitude']} (latitude, longitude)."
            )
    lines.append("\nPROVIDERS (provider_id; say the name exactly as written):")
    for p in cat["providers"]:
        where = " | ".join(f"{s['location_id']} {_week(s['days'])}" for s in p["schedules"])
        extra = []
        if p["refused_insurers"]:
            extra.append("does NOT take " + ", ".join(i["id"] for i in p["refused_insurers"]))
        extra += _away(p, today)
        lines.append(
            f"- {p['id']}: {p['name']} — {p['specialty_id']} — speaks {', '.join(p['languages'])} "
            f"— {where}" + (f" — {'; '.join(extra)}" if extra else "")
        )
    lines.append("\nSPECIALTIES (specialty_id):")
    for s in cat["specialties"]:
        lo, hi = s["min_age_months"], s["max_age_months"]
        if hi is not None:
            age = "under 14 only"
        elif lo:
            age = "from the 14th birthday"
        else:
            age = "any age"
        uncovered = ", ".join(p["id"] for p in s["not_covered_by"]) or "none"
        referral = "needs a GP referral on file" if s["referral_required"] else "no referral needed"
        lines.append(f"- {s['id']}: {age}; {referral}; plans that do NOT cover it: {uncovered}.")
    lines.append("\nINSURANCE PLANS (policy_id):")
    for plan in cat["plans"]:
        gaps = []
        if plan["uncovered_specialty_names"]:
            gaps.append("no " + ", ".join(plan["uncovered_specialty_names"]))
        if plan["uncovered_location_names"]:
            gaps.append("not valid at " + ", ".join(plan["uncovered_location_names"]))
        if plan["refused_by"]:
            gaps.append("refused by " + ", ".join(plan["refused_by"]))
        lines.append(f"- {plan['id']}: {plan['name']}" + (f" — {'; '.join(gaps)}" if gaps else ""))
    lines.append(
        "\nAPPOINTMENT TYPES (search_availability names the right one; never pick by hand):"
    )
    for t in cat["appointment_types"]:
        who = "new patients" if t["new_patient_requirement"] == "new_only" else "returning patients"
        lines.append(
            f"- {t['id']}: {t['duration_minutes']} min, {who}, "
            f"{t['specialty_id'] or 'general practice/gynaecology'}"
        )
    lines.append(
        "\nRESTRICTIONS (the reason ids for record_no_action when a rule blocks a booking):"
    )
    for r in cat["restrictions"]:
        lines.append(f"- {r['id']}: {r['explanation']}")
    return "\n".join(lines)


def _and(names: list[str]) -> str:
    return names[0] if len(names) == 1 else ", ".join(names[:-1]) + " and " + names[-1]


def calendar_text(now: datetime, cat: dict, days: int = 28) -> str:
    """Dated day list from today, so the model never does weekday arithmetic itself."""
    closures = set(cat["calendar"]["closure_days"])
    site_names = {loc["id"]: loc.get("name", loc["id"]) for loc in cat["locations"]}
    holiday_names: dict[str, str] = {}
    partial: dict[str, list[dict]] = {}
    for c in cat["calendar"].get("closures", []):
        holiday_names.setdefault(c["date"], c["name"])
        if c["location_id"] is not None:
            partial.setdefault(c["date"], []).append(c)
    last = date.fromisoformat(cat["calendar"]["ends"])
    saturday_sites = [
        loc["id"]
        for loc in cat["locations"]
        if any(h["weekday"] == "saturday" for h in loc["hours"])
    ]
    today = now.date()
    lines = [
        f"Right now it is {now:%A %d %B %Y, %H:%M} in Madrid.",
        "Nothing is ever booked for today: the earliest bookable day is tomorrow.",
        f"The bookable calendar ends {last:%A %d %B %Y} ({last.isoformat()}): nothing after it "
        "can be booked, and searches stop there.",
        "",
        "Upcoming days:",
    ]
    for i in range(1, days + 1):
        d = today + timedelta(days=i)
        if d > last:
            lines.append(f"- After {last:%a %d %b %Y}: the calendar ends; nothing is bookable.")
            break
        label = f"- {d:%a %d %b %Y} ({d.isoformat()})"
        if i == 1:
            label += " = tomorrow"
        elif i == 2:
            label += " = the day after tomorrow"
        elif i == 7:
            label += " = a week from today"
        elif i == 14:
            label += " = in a fortnight"
        day = d.isoformat()
        if day in closures:
            name = holiday_names.get(day)
            label += f" — CLOSED everywhere (public holiday{': ' + name if name else ''})"
        elif d.weekday() == 6:
            label += " — closed (Sunday)"
        else:
            if d.weekday() == 5:
                label += f" — Saturday: only {', '.join(saturday_sites)} is open"
            if day in partial:
                where = _and(
                    [site_names.get(c["location_id"], c["location_id"]) for c in partial[day]]
                )
                label += f" — closed at {where} ({partial[day][0]['name']})"
        lines.append(label)
    return "\n".join(lines)
