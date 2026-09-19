"""The clinic catalogue (fetched once, identical for every call) and the text the model reads.

Also the pure helpers the checks rely on: the DNI/NIE check letter and the dated calendar.
"""

import re
from datetime import date, datetime, timedelta

from app import prosper

_catalogue: dict | None = None


async def catalogue() -> dict:
    """GET /api/v1/clinic once per process; it never changes during the event."""
    global _catalogue
    if _catalogue is None:
        _catalogue = await prosper.client().clinic()
    return _catalogue


def cached() -> dict | None:
    """The catalogue if it has been fetched, for code that must not wait on the network."""
    return _catalogue


# ── National id ─────────────────────────────────────────────────────

_ID_LETTERS = "TRWAGMYFPDXBNJZSQVHLCKE"


def normalize_national_id(raw: str) -> str:
    """'x-1234567-l' -> 'X1234567L': the scorer's own normalization."""
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


def render_catalogue(cat: dict) -> str:
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
        if p["leave"]:
            leave = p["leave"]
            extra.append(f"ON LEAVE {leave['start']} to {leave['end']} ({leave['reason']})")
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


def calendar_text(now: datetime, cat: dict, days: int = 28) -> str:
    """Dated day list from today, so the model never does weekday arithmetic itself."""
    closures = set(cat["calendar"]["closure_days"])
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
        "can be booked, and a search past it is refused.",
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
        if d.isoformat() in closures:
            label += " — CLOSED everywhere (public holiday)"
        elif d.weekday() == 6:
            label += " — closed (Sunday)"
        elif d.weekday() == 5:
            label += f" — Saturday: only {', '.join(saturday_sites)} is open"
        lines.append(label)
    return "\n".join(lines)
