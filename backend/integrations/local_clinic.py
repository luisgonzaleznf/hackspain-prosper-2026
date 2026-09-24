"""The clinic engine: the patient directory, each patient's diary, and free slots under the
clinic's booking rules, all read from the clinic database.

Tool-facing shapes are the ones the prompt and tools were written against:

    directory(name=, national_id=, phone=, date_of_birth=) -> [patient + matched_fields + match_score]
    appointments(patient_id, when="upcoming"|"past"|"all") -> [appointment], earliest first
    availability(date_from, date_to, ...) -> {providers, appointment_type, slots, blocked}

Every "now" is the call's own clock (`now`), never the wall clock.
"""

import json
import math
import re
from datetime import date, datetime, time, timedelta
from difflib import SequenceMatcher

from app import clinic, config
from app.clinic import ClinicError

from integrations.local_store import LocalStore, normalized, phone_digits

FIELDS = ("name", "national_id", "phone", "date_of_birth")  # matched_fields order
NAME_LIMIT = 10  # a name-only search returns at most this many look-alikes
NAME_FLOOR = 0.6  # below this a name is clearly someone else
WEEKDAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]


def client(now: datetime | None = None, store: LocalStore | None = None) -> "LocalClinic":
    """The clinic every call reads through. Tests replace this to inject a fake."""
    return LocalClinic(store or LocalStore(), now or datetime.now(config.TZ))


def _words(text: str) -> list[str]:
    return [w for w in (normalized(part) for part in re.split(r"[\s\-]+", text)) if w]


def _patient_words(patient: dict) -> list[str]:
    return _words(
        " ".join(patient.get(k) or "" for k in ("given_name", "first_surname", "second_surname"))
    )


def _minutes(hhmm: str) -> int:
    hours, minutes = hhmm.strip().split(":")
    return int(hours) * 60 + int(minutes)


def _span(interval: str) -> tuple[int, int]:
    """'09:00\u201314:00' (an en dash, or a hyphen) -> (540, 840)."""
    start, end = re.split(r"\s*[\u2013-]\s*", interval.strip())
    return _minutes(start), _minutes(end)


def _hours(days: list[dict], weekday: str) -> list[tuple[int, int]]:
    return [_span(i) for d in days if d["weekday"] == weekday for i in d["intervals"]]


def _age_months(dob: date, day: date) -> int:
    return (day.year - dob.year) * 12 + day.month - dob.month - (day.day < dob.day)


def _days(first: date, last: date) -> list[date]:
    return [first + timedelta(days=i) for i in range((last - first).days + 1)]


class LocalClinic:
    def __init__(self, store: LocalStore, now: datetime):
        self.store = store
        self.now = now

    # ── directory ───────────────────────────────────────────────────

    async def directory(
        self,
        *,
        name: str | None = None,
        national_id: str | None = None,
        phone: str | None = None,
        date_of_birth: str | None = None,
    ) -> list[dict]:
        """Exact fields (national_id, phone, date_of_birth) filter together. With them, a name
        only narrows to the survivors sharing the most name words (all survivors if none share
        one). A name alone is a fuzzy, accent-blind search: the 10 closest, look-alikes included."""
        query = {
            k: v
            for k, v in zip(FIELDS, (name, national_id, phone, date_of_birth), strict=True)
            if v
        }
        if not query:
            return []
        fields = [k for k in FIELDS if k in query]
        if "national_id" in query:
            nid = clinic.normalize_national_id(query["national_id"])
            with self.store.connect() as db:
                rows = db.execute("SELECT data FROM patients WHERE national_id=?", (nid,))
                patients = [json.loads(row[0]) for row in rows]
        else:
            patients = self.store.patients()
        if any(k in query for k in ("national_id", "phone", "date_of_birth")):
            survivors = [
                p
                for p in patients
                if (
                    "phone" not in query or phone_digits(query["phone"]) == phone_digits(p["phone"])
                )
                and ("date_of_birth" not in query or query["date_of_birth"] == p["date_of_birth"])
            ]
            if name:
                spoken = set(_words(name))
                overlap = {p["patient_id"]: len(spoken & set(_patient_words(p))) for p in survivors}
                best = max(overlap.values(), default=0)
                if best:
                    survivors = [p for p in survivors if overlap[p["patient_id"]] == best]
            return [{**p, "matched_fields": fields, "match_score": 1.0} for p in survivors]
        return self._by_name(query["name"], patients)

    @staticmethod
    def _by_name(name: str, patients: list[dict]) -> list[dict]:
        spoken = _words(name)
        if not spoken:
            return []
        memo: dict[tuple[str, str], float] = {}

        def closeness(heard: str, words: list[str]) -> float:
            if heard in words:
                return 1.0
            best = 0.0
            for word in words:
                if (heard, word) not in memo:
                    memo[heard, word] = SequenceMatcher(None, heard, word, autojunk=False).ratio()
                best = max(best, memo[heard, word])
            return best

        ranked = []
        for p in patients:
            words = _patient_words(p)
            score = sum(closeness(heard, words) for heard in spoken) / len(spoken)
            if score >= NAME_FLOOR:
                ranked.append((-score, words != spoken, p["patient_id"], score, p))
        ranked.sort(key=lambda r: r[:3])
        return [
            {**p, "matched_fields": ["name"], "match_score": round(score, 3)}
            for *_, score, p in ranked[:NAME_LIMIT]
        ]

    # ── a patient's diary ───────────────────────────────────────────

    async def appointments(self, patient_id: str, when: str = "upcoming") -> list[dict]:
        if when not in ("upcoming", "past", "all"):
            raise ClinicError(422, "when must be upcoming, past or all")
        rows = self.store.appointments(patient_id)
        if when == "all":
            return rows
        return [
            a
            for a in rows
            if (datetime.fromisoformat(a["start_time"]) > self.now) == (when == "upcoming")
        ]

    # ── availability ────────────────────────────────────────────────

    async def availability(
        self,
        date_from: str,
        date_to: str,
        *,
        specialty_id: str | None = None,
        provider_id: str | None = None,
        location_id: str | None = None,
        patient_id: str | None = None,
        insurers: list[str] | None = None,
        exclude_appointment_id: str | None = None,
    ) -> dict:
        """Free slots in [date_from, date_to], the one appointment type that fits the patient,
        and in `blocked` the first rule that stops each provider (at most one entry each).

        Slots: a 15-minute grid inside each doctor's hours at a site (within the site's opening
        hours), minus booked appointments, closures, absences, times already past and the
        patient's own appointments. The window is clipped to the published calendar."""
        cat = await clinic.catalogue()
        first, last = self._window(cat, date_from, date_to)
        providers = sorted(
            (
                p
                for p in cat["providers"]
                if (not provider_id or p["id"] == provider_id)
                and (not specialty_id or p["specialty_id"] == specialty_id)
            ),
            key=lambda p: p["id"],
        )
        specialties = {s["id"]: s for s in cat["specialties"]}
        sites = {loc["id"]: loc for loc in cat["locations"]}
        plan_ids = [plan["id"] for plan in cat["plans"]]
        if not specialty_id and not provider_id:
            raise ClinicError(422, "give specialty_id or provider_id")
        if specialty_id and specialty_id not in specialties:
            raise ClinicError(422, f"unknown specialty_id {specialty_id}")
        if provider_id and not any(p["id"] == provider_id for p in cat["providers"]):
            raise ClinicError(422, f"unknown provider_id {provider_id}")
        if not providers:
            raise ClinicError(422, f"{provider_id} does not practise {specialty_id}")
        if location_id and location_id not in sites:
            raise ClinicError(422, f"unknown location_id {location_id}")
        unknown = [plan for plan in insurers or [] if plan not in plan_ids]
        if unknown:
            raise ClinicError(422, f"unknown insurer {unknown[0]}")
        patient = self.store.patient(patient_id) if patient_id else None
        if patient_id and patient is None:
            raise ClinicError(422, f"unknown patient_id {patient_id}")

        specialty = specialties[specialty_id or providers[0]["specialty_id"]]
        kind = self._type(cat, specialty["id"], bool(patient and patient["has_visited_before"]))
        duration = kind["duration_minutes"]
        cells = math.ceil(duration / 15) * 15  # whole grid cells the type occupies
        plans = list(insurers or []) or ([patient["insurer"]] if patient else plan_ids)
        days = _days(first, last)
        ids = [p["id"] for p in providers]
        diary = self._diary(ids, first, last, patient_id, exclude_appointment_id)
        used = (
            self._used(patient, specialty["id"], exclude_appointment_id)
            if patient
            and any(
                specialty["id"]
                in cat.get("plan_rules", {}).get(plan, {}).get("annual_allowance", {})
                for plan in plans
            )
            else 0
        )
        dob = date.fromisoformat(patient["date_of_birth"]) if patient else None

        def of_age(day: date) -> bool:
            if dob is None:
                return True
            months = _age_months(dob, day)
            top = specialty["max_age_months"]
            return months >= specialty["min_age_months"] and (top is None or months <= top)

        uncovered_at = {sid: {i["id"] for i in loc["not_covered_by"]} for sid, loc in sites.items()}
        slots, blocked, out = [], [], []
        for p in providers:
            own_sites = [s["location_id"] for s in p["schedules"]]
            whole = diary["whole"].get(p["id"], set())
            out.append(self._provider_out(p, own_sites, diary["leave"].get(p["id"])))
            rule, payable_plans = self._rule(
                cat,
                p,
                specialty,
                [location_id] if location_id else own_sites,
                patient,
                plans,
                used,
                uncovered_at,
                days,
                whole,
                diary["closed"],
                of_age,
            )
            if rule:
                blocked.append({"provider_id": p["id"], "restriction": rule})
                continue
            for day in days:
                if day in diary["closed"].get(None, set()) or day in whole or not of_age(day):
                    continue
                weekday = WEEKDAYS[day.weekday()]
                busy = diary["busy"].get((p["id"], day), [])
                for schedule in p["schedules"]:
                    site = schedule["location_id"]
                    if location_id and site != location_id:
                        continue
                    if day in diary["closed"].get(site, set()):
                        continue
                    payable = [plan for plan in payable_plans if plan not in uncovered_at[site]]
                    if not payable:
                        continue
                    for a, b in _hours(schedule["days"], weekday):
                        for c, d in _hours(sites[site]["hours"], weekday):
                            lo, hi = max(a, c), min(b, d)
                            start = -(-lo // 15) * 15
                            while start + cells <= hi:
                                end = start + cells
                                if not any(s < end and start < e for s, e in busy):
                                    when = datetime.combine(
                                        day, time(start // 60, start % 60), tzinfo=config.TZ
                                    )
                                    if when > self.now and not any(
                                        s < when + timedelta(minutes=duration) and when < e
                                        for s, e in diary["patient"]
                                    ):
                                        slots.append(
                                            {
                                                "provider_id": p["id"],
                                                "provider_name": p["name"],
                                                "specialty_id": specialty["id"],
                                                "location_id": site,
                                                "appointment_type_id": kind["id"],
                                                "start_time": when.isoformat(timespec="seconds"),
                                                "duration_minutes": duration,
                                                "payable_with": payable,
                                                "_when": when,
                                            }
                                        )
                                start += 15
        slots.sort(key=lambda s: (s["_when"], s["provider_id"]))
        for s in slots:
            del s["_when"]
        return {
            "providers": out,
            "appointment_type": {
                k: kind[k]
                for k in ("id", "name", "duration_minutes", "new_patient_requirement", "guidance")
            },
            "slots": slots,
            "blocked": blocked,
        }

    def _window(self, cat: dict, date_from: str, date_to: str) -> tuple[date, date]:
        """The searched days: refused outside the calendar or over the span, else clipped to it."""
        try:
            first, last = date.fromisoformat(date_from), date.fromisoformat(date_to)
        except (TypeError, ValueError):
            raise ClinicError(422, "dates must be YYYY-MM-DD") from None
        if last < first:
            raise ClinicError(422, "date_to is before date_from")
        calendar = cat.get("calendar") or {}
        span = calendar.get("max_span_days", clinic.MAX_SPAN_DAYS)
        if (last - first).days + 1 > span:
            raise ClinicError(422, f"date range exceeds {span} days")
        starts = self.now.astimezone(config.TZ).date()
        ends = date.fromisoformat(calendar["ends"]) if calendar.get("ends") else None
        if last < starts or (ends and first > ends):
            raise ClinicError(422, "date range is outside the published calendar")
        return max(first, starts), min(last, ends) if ends else last

    @staticmethod
    def _type(cat: dict, specialty_id: str, returning: bool) -> dict:
        """A specialty's own first-visit/review type, else the universal one (GP; new gynaecology)."""
        need = "existing_only" if returning else "new_only"
        fits = [t for t in cat["appointment_types"] if t["new_patient_requirement"] == need]
        own = [t for t in fits if t["specialty_id"] == specialty_id]
        return (own or [t for t in fits if t["specialty_id"] is None])[0]

    def _diary(
        self,
        provider_ids: list[str],
        first: date,
        last: date,
        patient_id: str | None,
        exclude: str | None,
    ) -> dict:
        """What occupies the window, read once through the indexed columns: busy minutes per
        (provider, day), whole days away, closures, and the patient's own appointments."""
        span = (first.isoformat(), last.isoformat())
        marks = ",".join("?" * len(provider_ids))
        busy: dict[tuple[str, date], list[tuple[int, int]]] = {}
        whole: dict[str, set[date]] = {}
        leave: dict[str, str] = {}
        closed: dict[str | None, set[date]] = {}
        own: list[tuple[datetime, datetime]] = []
        with self.store.connect() as db:
            for row in db.execute(
                "SELECT provider_id, start_time, json_extract(data, '$.duration_minutes') "
                f"FROM appointments WHERE status='booked' AND provider_id IN ({marks}) "
                "AND start_date BETWEEN ? AND ? AND appointment_id IS NOT ?",
                (*provider_ids, *span, exclude),
            ):
                start = datetime.fromisoformat(row[1]).astimezone(config.TZ)
                minute = start.hour * 60 + start.minute
                busy.setdefault((row[0], start.date()), []).append((minute, minute + int(row[2])))
            for row in db.execute(
                "SELECT provider_id, start_date, end_date, start_time, end_time FROM absences "
                f"WHERE provider_id IN ({marks}) AND start_date <= ? AND end_date >= ?",
                (*provider_ids, span[1], span[0]),
            ):
                days = [
                    d
                    for d in _days(date.fromisoformat(row[1]), date.fromisoformat(row[2]))
                    if first <= d <= last
                ]
                if row[3] is None:
                    whole.setdefault(row[0], set()).update(days)
                    leave[row[0]] = max(leave.get(row[0], row[2]), row[2])
                else:
                    for d in days:
                        busy.setdefault((row[0], d), []).append(
                            (_minutes(row[3]), _minutes(row[4]))
                        )
            for row in db.execute(
                "SELECT date, location_id FROM closures WHERE date BETWEEN ? AND ?", span
            ):
                closed.setdefault(row[1], set()).add(date.fromisoformat(row[0]))
            if patient_id:
                for row in db.execute(
                    "SELECT start_time, json_extract(data, '$.duration_minutes') FROM appointments "
                    "WHERE status='booked' AND patient_id=? AND start_date BETWEEN ? AND ? "
                    "AND appointment_id IS NOT ?",
                    (patient_id, *span, exclude),
                ):
                    start = datetime.fromisoformat(row[0])
                    own.append((start, start + timedelta(minutes=int(row[1]))))
        return {"busy": busy, "whole": whole, "leave": leave, "closed": closed, "patient": own}

    def _used(self, patient: dict, specialty_id: str, exclude: str | None) -> int:
        """Sessions of a specialty this calendar year: outside ours on file, plus our diary's
        booked or attended rows (a no-show consumed nothing)."""
        year = self.now.astimezone(config.TZ).year
        with self.store.connect() as db:
            (count,) = db.execute(
                "SELECT COUNT(*) FROM appointments WHERE status='booked' AND patient_id=? "
                "AND start_date BETWEEN ? AND ? AND appointment_id IS NOT ? "
                "AND json_extract(data, '$.specialty_id')=? "
                "AND COALESCE(json_extract(data, '$.attendance'), '') != 'no_show'",
                (patient["patient_id"], f"{year}-01-01", f"{year}-12-31", exclude, specialty_id),
            ).fetchone()
        return count + int((patient.get("allowance_used") or {}).get(specialty_id, 0))

    @staticmethod
    def _rule(
        cat, p, specialty, where, patient, plans, used, uncovered_at, days, whole, closed, of_age
    ) -> tuple[str | None, list[str]]:
        """The first rule that stops this provider, else the candidate plans that still pay.

        Order: not_eligible_age > referral_required > provider_not_in_network >
        specialty_not_covered > location_not_covered > insurer_referral_required >
        allowance_exhausted > provider_on_leave. Each plan rule removes the plans it fails;
        the provider is blocked when none is left."""
        sid = specialty["id"]
        if patient is not None:
            if not any(of_age(day) for day in days):
                return "not_eligible_age", []
            if specialty["referral_required"] and sid not in (patient.get("referrals") or []):
                return "referral_required", []
        refused = {i["id"] for i in p.get("refused_insurers", [])}
        left = [plan for plan in plans if plan not in refused]
        if not left:
            return "provider_not_in_network", []
        not_covered = {i["id"] for i in specialty["not_covered_by"]}
        left = [plan for plan in left if plan not in not_covered]
        if not left:
            return "specialty_not_covered", []
        left = [plan for plan in left if any(plan not in uncovered_at[site] for site in where)]
        if not left:
            return "location_not_covered", []
        if patient is not None:
            rules = cat.get("plan_rules") or {}
            authorised = patient.get("insurer_authorizations") or []
            left = [
                plan
                for plan in left
                if sid not in rules.get(plan, {}).get("authorization_required", [])
                or sid in authorised
            ]
            if not left:
                return "insurer_referral_required", []
            left = [
                plan
                for plan in left
                if sid not in (allowance := rules.get(plan, {}).get("annual_allowance", {}))
                or used < allowance[sid]
            ]
            if not left:
                return "allowance_exhausted", []
        # On leave for the whole window: every day the doctor would work is a day away.
        weekdays = {d["weekday"] for s in p["schedules"] for d in s["days"]}
        working = [
            day
            for day in days
            if WEEKDAYS[day.weekday()] in weekdays and day not in closed.get(None, set())
        ]
        if whole & set(days) and all(day in whole for day in working):
            return "provider_on_leave", []
        return None, left

    @staticmethod
    def _provider_out(p: dict, own_sites: list[str], leave_end: str | None) -> dict:
        refused = {i["id"] for i in p.get("refused_insurers", [])}
        return {
            "id": p["id"],
            "name": p["name"],
            "specialty_id": p["specialty_id"],
            "languages": p.get("languages", []),
            "accepted_insurers": sorted(
                i["id"] for i in p.get("accepted_insurers", []) if i["id"] not in refused
            ),
            "locations": own_sites,
            "on_leave_until": leave_end,
        }
