"""Seed the clinic database: patients, a realistic diary, absences and public holidays.

    uv run --project . python scripts/seed_clinic.py [--db PATH] [--anchor YYYY-MM-DD] [--patients 3000]
        [--seed 7] [--dense-weeks 4] [--tail-weeks 4] [--force | --if-unseeded]

Deterministic for (anchor, seed, patients, weeks). The anchor (default: today in Madrid) is the
day the diary is built around: ~8 weeks of history before it, `dense` busy weeks after it, then
`tail` lighter weeks up to `horizon_end`. Older visits (back to 2025) back every
`has_visited_before`. Every seeded row is checked by an independent validator
(`seed/validate.py`) and the run exits non-zero if any check or demo guarantee fails.
"""

import argparse
import json
import math
import os
import random
import re
import sqlite3
import sys
import unicodedata
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from seed import realism as R  # noqa: E402
from seed import validate  # noqa: E402

MADRID = ZoneInfo("Europe/Madrid")
WEEKDAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
SEED_DIR = BACKEND / "seed"
GENERATOR = "seed_clinic v1"
FIRST_NEW_PATIENT = 3001
FIRST_APPOINTMENT = 100001
ROUNDS = (0.4, 0.7, 0.85, 1.0)  # fill every day to these shares of its target, one pass each

SCHEMA = """
CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS closures (date TEXT NOT NULL, location_id TEXT, name TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS absences (
  id INTEGER PRIMARY KEY, provider_id TEXT NOT NULL,
  start_date TEXT NOT NULL, end_date TEXT NOT NULL,
  start_time TEXT, end_time TEXT,
  reason TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS patients (patient_id TEXT PRIMARY KEY, national_id TEXT NOT NULL UNIQUE, data TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS appointments (
  appointment_id TEXT PRIMARY KEY, patient_id TEXT NOT NULL, status TEXT NOT NULL, data TEXT NOT NULL,
  provider_id TEXT, start_date TEXT, start_time TEXT
);
CREATE INDEX IF NOT EXISTS appointments_provider_day ON appointments(provider_id, start_date);
CREATE INDEX IF NOT EXISTS appointments_day ON appointments(start_date);
CREATE INDEX IF NOT EXISTS appointments_patient ON appointments(patient_id);
CREATE TABLE IF NOT EXISTS changes (
  id INTEGER PRIMARY KEY, call_id TEXT NOT NULL,
  operation_key TEXT NOT NULL UNIQUE, created_at REAL NOT NULL,
  action TEXT NOT NULL, result TEXT NOT NULL
);
"""
TABLES = ("meta", "closures", "absences", "patients", "appointments", "changes")


def minutes(hhmm: str) -> int:
    h, m = hhmm.split(":")
    return int(h) * 60 + int(m)


def hhmm(m: int) -> str:
    return f"{m // 60:02d}:{m % 60:02d}"


def interval(text: str) -> tuple[int, int]:
    a, b = text.replace("\u2013", "-").split("-")  # the catalogue separates times with an en dash
    return minutes(a), minutes(b)


def start_iso(day: date, minute: int) -> str:
    return datetime(day.year, day.month, day.day, minute // 60, minute % 60, tzinfo=MADRID).isoformat(timespec="seconds")


def age_months(dob: date, day: date) -> int:
    return (day.year - dob.year) * 12 + day.month - dob.month - (day.day < dob.day)


def fold(text: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", text) if c.isascii() and c.isalnum()).lower()


def weighted(rng: random.Random, table: dict):
    keys = list(table)
    return rng.choices(keys, weights=[table[k] for k in keys])[0]


def days(a: date, b: date):
    while a <= b:
        yield a
        a += timedelta(days=1)


def next_weekday(d: date, weekday: int) -> date:
    return d + timedelta(days=(weekday - d.weekday()) % 7)


# ── The static catalogue ─────────────────────────────────────────────────────────────────────


class Catalogue:
    def __init__(self, cat: dict):
        self.data = cat
        self.providers = {p["id"]: p for p in cat["providers"]}
        self.specialties = {s["id"]: s for s in cat["specialties"]}
        self.types = {t["id"]: t for t in cat["appointment_types"]}
        self.locations = {loc["id"]: loc for loc in cat["locations"]}
        self.plan_ids = [p["id"] for p in cat["plans"]]
        self.rules = cat.get("plan_rules", {})
        self.refused = {pid: {r["id"] for r in p["refused_insurers"]} for pid, p in self.providers.items()}
        self.spec_uncovered = {sid: {x["id"] for x in s["not_covered_by"]} for sid, s in self.specialties.items()}
        self.site_uncovered = {lid: {x["id"] for x in loc["not_covered_by"]} for lid, loc in self.locations.items()}
        self.by_spec = defaultdict(list)
        for pid in sorted(self.providers):
            self.by_spec[self.providers[pid]["specialty_id"]].append(pid)
        site_hours = {}
        for lid, loc in self.locations.items():
            for day in loc["hours"]:
                site_hours[(lid, WEEKDAYS.index(day["weekday"]))] = [interval(i) for i in day["intervals"]]
        self.schedule = {}  # (provider, weekday) -> (site, start_min, end_min) inside the site's hours
        for pid, p in self.providers.items():
            for sched in p["schedules"]:
                for day in sched["days"]:
                    wd = WEEKDAYS.index(day["weekday"])
                    for text in day["intervals"]:
                        a, b = interval(text)
                        for ha, hb in site_hours.get((sched["location_id"], wd), []):
                            lo, hi = max(a, ha), min(b, hb)
                            if lo < hi:
                                self.schedule[(pid, wd)] = (sched["location_id"], lo, hi)
        self.sites_of = defaultdict(set)
        for (pid, _), (site, _, _) in self.schedule.items():
            self.sites_of[pid].add(site)

    def plan_ok(self, plan: str, provider: str, spec: str, site: str) -> bool:
        return (plan not in self.refused[provider] and plan not in self.spec_uncovered[spec]
                and plan not in self.site_uncovered[site])

    def spec_of(self, provider: str) -> str:
        return self.providers[provider]["specialty_id"]


# ── People ───────────────────────────────────────────────────────────────────────────────────


@dataclass
class Person:
    idx: int
    patient_id: str
    given: str
    first: str
    second: str
    sex: str
    dob: date
    national_id: str = ""
    phone: str = ""
    email: str = ""
    insurer: str = ""
    home: str = "centro"
    origin: str = "es_general"
    group: str | None = None                        # name pool for foreigners (latam, en, fr, it, ...)
    language: str = "es"
    known_as: str = ""
    recovered: bool = False
    case: bool = False
    referrals: set = field(default_factory=set)
    authorizations: set = field(default_factory=set)
    allowance_used: dict = field(default_factory=dict)
    private_pay: set = field(default_factory=set)
    relatives: list = field(default_factory=list)   # (idx, label, same_phone, calls_for_them)
    notes: list = field(default_factory=list)       # fixed sentences (featured / recovered hints)
    prosper_hints: list = field(default_factory=list)
    seen_intent: bool = True
    recent_first: bool = False
    first_attended: date | None = None
    past_budget: int = 0
    future_budget: int = 0
    old_plan: list = field(default_factory=list)    # [(specialty, provider|None)] for personas
    usual_gp: str = ""
    no_email: bool = False
    phone_kind: str = "mobile"
    in_course: bool = False
    rows: list = field(default_factory=list)
    days_taken: set = field(default_factory=set)

    @property
    def full_name(self) -> str:
        return " ".join(x for x in (self.given, self.first, self.second) if x)

    def age(self, day: date) -> int:
        return age_months(self.dob, day) // 12


class World:
    """Everything the generator builds; written to SQLite at the end."""

    def __init__(self, args, cat: Catalogue):
        self.cat = cat
        self.anchor: date = args.anchor
        self.dense_end = self.anchor + timedelta(days=7 * args.dense_weeks)
        self.horizon_end = self.anchor + timedelta(days=7 * (args.dense_weeks + args.tail_weeks))
        self.history_start = self.anchor - timedelta(days=56)
        self.old_start = max(R.CALENDAR_FIRST + timedelta(days=1), self.anchor - timedelta(days=600))
        self.args = args
        self.rng = random.Random(f"clinic:{args.seed}:{self.anchor.isoformat()}:{args.patients}")
        self.people: list[Person] = []
        self.appointments: list[dict] = []
        self.absences: list[dict] = []
        self.closed_all: dict[date, str] = {}
        self.closed_site: dict[tuple[date, str], str] = {}
        self.grid: dict = {}
        self.used_ids: set[str] = set(R.FORBIDDEN_NATIONAL_IDS)
        self.used_phones: set[str] = set(R.FORBIDDEN_PHONES)
        self.names_taken: set[str] = set(R.FORBIDDEN_NAMES)
        self.s_past = self.s_future = 1.0
        self.skipped: list[str] = []
        self.closure_rows: list[tuple] = []


# ── Calendar: closures, absences, the cell grid ─────────────────────────────────────────────


def build_closures(w: World) -> list[tuple]:
    rows = []
    for day, scope, name in R.HOLIDAYS:
        for site in R.HOLIDAY_SITES[scope]:
            rows.append((day.isoformat(), site, name))
            if site is None:
                w.closed_all[day] = name
            else:
                w.closed_site[(day, site)] = name
    return rows


def closed(w: World, day: date, site: str) -> bool:
    return day in w.closed_all or (day, site) in w.closed_site


def works(w: World, provider: str, day: date) -> tuple[str, int, int] | None:
    """Where and when the provider sits that day, or None (not scheduled, holiday, whole-day absence)."""
    sched = w.cat.schedule.get((provider, day.weekday()))
    if not sched or closed(w, day, sched[0]):
        return None
    for a in w.absences:
        if a["provider_id"] == provider and a["start"] <= day <= a["end"] and a["start_time"] is None:
            return None
    return sched


def build_absences(w: World) -> None:
    a0, rng_end = w.anchor, w.horizon_end

    def add(pid, start, end, reason, t0=None, t1=None):
        for a in w.absences:
            if a["provider_id"] == pid and a["start"] <= end and start <= a["end"]:
                return
        w.absences.append({"provider_id": pid, "start": start, "end": end, "start_time": t0,
                           "end_time": t1, "reason": reason})

    def working_day(pid, day):
        for _ in range(21):
            if works(w, pid, day):
                return day
            day += timedelta(days=1)
        return None

    def congress(pid, fallback, length):
        for start, end, reason in R.CONGRESSES.get(pid, []):
            if start <= w.dense_end and end > a0:
                return start, end, reason
        return fallback, fallback + timedelta(days=length - 1), "congress"

    # the anchor-relative plan (for 2026-09-24 it is exactly realism.md §5.2)
    add("PR02", a0 - timedelta(days=10), next_weekday(a0 + timedelta(days=6), 2), "sick leave")
    add("PR05", *congress("PR05", next_weekday(a0 + timedelta(days=6), 2), 3))
    add("PR10", *congress("PR10", next_weekday(a0 + timedelta(days=6), 2), 3))
    add("PR01", *congress("PR01", next_weekday(a0 + timedelta(days=13), 2), 4))
    vac = next_weekday(a0 + timedelta(days=15), 4)
    add("PR06", vac, vac + timedelta(days=7), "annual leave")
    course = next_weekday(a0 + timedelta(days=22), 4)
    add("PR09", course, course, "training course")
    tail_congress = next_weekday(a0 + timedelta(days=36), 2)
    add("PR11", tail_congress, tail_congress + timedelta(days=1), "congress")
    personal = next_weekday(a0 + timedelta(days=43), 0)
    add("PR03", personal, personal, "personal")
    # summer and Christmas leave, every year the seeded range touches
    for year in range(w.old_start.year, rng_end.year + 1):
        for pid, (wk1, wk2) in R.SUMMER_LEAVE_WEEKS.items():
            add(pid, date.fromisocalendar(year, wk1, 1), date.fromisocalendar(year, wk2, 5), "annual leave")
        for pid in R.CHRISTMAS_LEAVE:
            add(pid, date(year, 12, 28), date(year + 1, 1, 4), "annual leave")
    # half-day blocks (after the whole days, so they land on a day the provider really works)
    for pid, offset, weekday, t0, t1, reason in (
        ("PR04", 8, None, "12:00", "14:00", "personal"),
        ("PR07", 12, 1, "11:30", "14:00", "personal"),
        ("PR12", 25, 0, "10:00", "12:00", "personal"),
        ("PR11", 28, 3, "09:00", "11:00", "hospital teaching session"),
    ):
        day = a0 + timedelta(days=offset)
        day = working_day(pid, next_weekday(day, weekday) if weekday is not None else day)
        sched = works(w, pid, day) if day else None
        if day and sched:
            lo, hi = max(minutes(t0), sched[1]), min(minutes(t1), sched[2])
            if lo < hi:
                add(pid, day, day, reason, hhmm(lo), hhmm(hi))
    w.absences = [a for a in w.absences if a["end"] >= w.old_start and a["start"] <= rng_end]
    w.absences.sort(key=lambda a: (a["start"], a["provider_id"]))


def cells(w: World, provider: str, day: date):
    """[site, first_minute, state] for a provider-day; state: 0 free, 1 booked, 2 blocked, 3 hole."""
    key = (provider, day)
    if key not in w.grid:
        sched = works(w, provider, day)
        if not sched:
            w.grid[key] = None
        else:
            site, lo, hi = sched
            state = bytearray((hi - lo) // 15)
            for a in w.absences:
                if a["provider_id"] == provider and a["start"] <= day <= a["end"] and a["start_time"]:
                    for i in range(len(state)):
                        m = lo + 15 * i
                        if minutes(a["start_time"]) <= m < minutes(a["end_time"]):
                            state[i] = 2
            w.grid[key] = [site, lo, state]
    return w.grid[key]


def fits(state, i: int, n: int) -> bool:
    return i >= 0 and i + n <= len(state) and all(state[j] == 0 for j in range(i, i + n))


# ── Patients ─────────────────────────────────────────────────────────────────────────────────


def cohort(year: int) -> str:
    for lo, hi, label in R.GIVEN_NAME_COHORTS:
        if (lo is None or year >= lo) and year <= hi:
            return label
    return "2010-2026"


def draw_given(rng, sex: str, dob: date, origin: str, group: str | None) -> str:
    if origin in R.REGIONAL_GIVEN:
        share = {"es_catalan": 0.5, "es_galician": 0.25, "es_basque": 0.4}[origin]
        if rng.random() < share:
            return rng.choice(R.REGIONAL_GIVEN[origin][sex])
    if group:
        return rng.choice(R.FOREIGN_NAMES[group][0 if sex == "M" else 1])
    c = cohort(dob.year)
    top = (R.GIVEN_NAMES_M if sex == "M" else R.GIVEN_NAMES_F)[c]
    tail = (R.GIVEN_NAMES_TAIL_M if sex == "M" else R.GIVEN_NAMES_TAIL_F)[c]
    if rng.random() < R.GIVEN_TOP_SHARE[sex][c]:
        name = rng.choices([n for n, _ in top], weights=[wt for _, wt in top])[0]
    else:
        name = rng.choice(tail)
    if name in R.COMPOUND_GIVEN_NAME_ALT and rng.random() < 0.4:
        name = R.COMPOUND_GIVEN_NAME_ALT[name]
    return name


def foreign_group(origin: str, rng) -> str | None:
    return {"latam_dni": "latam", "latam_nie": "latam", "expat_en": "en", "maghreb": "maghreb",
            "china": "china"}.get(origin) or (
        rng.choice(["fr", "it", "de", "pt"]) if origin == "expat_eu" else
        rng.choice(["ro", "ro", "ua"]) if origin == "ro_ua" else None)


def draw_surname(rng, origin: str, group: str | None) -> str:
    if origin in R.REGIONAL_SURNAMES and rng.random() < 0.6:
        return rng.choice(R.REGIONAL_SURNAMES[origin])
    if group:
        return rng.choice(R.FOREIGN_NAMES[group][2])
    if rng.random() < R.EXTRA_COMPOUND_SHARE:
        return rng.choice(R.EXTRA_COMPOUND_SURNAMES)
    if rng.random() < R.SURNAME_TIERS["SURNAMES"]:
        return rng.choices([n for n, _ in R.SURNAMES], weights=[wt for _, wt in R.SURNAMES])[0]
    return rng.choice(R.SURNAMES_TAIL)


def name_ok(w: World, given: str, first: str, second: str) -> bool:
    full = f"{given} {first} {second}"
    return full not in w.names_taken and not ({"rosario", "sanz"} <= {fold(t) for t in full.split()})


def new_national_id(w: World, rng, nie_prefix: str | None = None) -> str:
    while True:
        if nie_prefix:
            value = R.nie(nie_prefix, rng.randrange(0, 10_000_000))
        else:
            value = R.dni(rng.randrange(*R.DNI_NUMBER_RANGE))
        if value not in w.used_ids:
            w.used_ids.add(value)
            return value


def new_phone(w: World, rng, age: int, home: str, kind: str = "mobile") -> str:
    while True:
        if kind == "landline":
            value = rng.choice(R.LANDLINE_PREFIX_BY_SITE[home]) + f"{rng.randrange(1_000_000):06d}"
        else:
            share7 = R.MOBILE_7X_SHARE_BY_AGE["<40" if age < 40 else "40-64" if age < 65 else "65+"]
            value = (rng.choice(["71", "72", "73", "74"]) + f"{rng.randrange(10_000_000):07d}"
                     if rng.random() < share7 else "6" + f"{rng.randrange(100_000_000):08d}")
        if value not in w.used_phones:
            w.used_phones.add(value)
            return value


def new_email(rng, p: Person) -> str:
    pattern = rng.choices([x for x, _ in R.EMAIL_LOCAL_PATTERNS], weights=[wt for _, wt in R.EMAIL_LOCAL_PATTERNS])[0]
    given = fold(p.given.split()[0]) or "x"
    local = pattern.format(given=given, g1=given[0], surname1=fold(p.first) or "x",
                           surname2=fold(p.second) or "x", yy=f"{p.dob.year % 100:02d}", nn=rng.randint(1, 99))
    return f"{local}@{weighted(rng, R.EMAIL_DOMAINS)}"


def email_share(age: int) -> float:
    return (R.EMAIL_ON_FILE["14-17"] if age < 18 else R.EMAIL_ON_FILE["18-44"] if age < 45 else
            R.EMAIL_ON_FILE["45-64"] if age < 65 else R.EMAIL_ON_FILE["65-79"] if age < 80 else R.EMAIL_ON_FILE["80+"])


def draw_insurer(rng, age: int, home: str, origin: str) -> str:
    weights = dict(R.INSURER_BASE)
    for key in (("age_65+" if age >= 65 else None), f"home_{home}", origin):
        for plan, factor in R.INSURER_MULTIPLIERS.get(key or "", {}).items():
            weights[plan] *= factor
    return weighted(rng, weights)


def insurer_fits_home(plan: str, home: str, cat: Catalogue) -> bool:
    return plan not in cat.site_uncovered[home]


def usual_gp(rng, home: str) -> str:
    return weighted(rng, {"centro": {"PR01": 0.5, "PR07": 0.35, "PR03": 0.15},
                          "norte": {"PR02": 0.6, "PR07": 0.4}, "sur": {"PR03": 1.0}}[home])


def years_before(d: date, years: int) -> date:
    try:
        return d.replace(year=d.year - years)
    except ValueError:  # 29 February
        return date(d.year - years, 2, 28)


def random_dob(rng, anchor: date, min_age: int, max_age: int) -> date:
    """A birthday that makes the person min_age..max_age years old on the anchor day."""
    latest = years_before(anchor, min_age)
    earliest = years_before(anchor, max_age + 1) + timedelta(days=1)
    return earliest + timedelta(days=rng.randrange((latest - earliest).days + 1))


def finish_person(w: World, p: Person, rng) -> None:
    """Budgets, visit intent, usual doctor, private-pay habits. Shared by every kind of person."""
    p.usual_gp = usual_gp(rng, p.home)
    p.future_budget = weighted(rng, R.FUTURE_BUDGET)
    p.past_budget = weighted(rng, R.PAST_BUDGET) if p.seen_intent else 0
    if p.seen_intent and not p.recovered and rng.random() < R.RECENT_FIRST_SHARE:
        p.recent_first = True
    if p.recovered and p.seen_intent and rng.random() < R.RECENT_FIRST_SHARE:
        p.recent_first = True
    if p.recent_first:
        p.past_budget = max(1, p.past_budget)
    for spec, plans in R.PRIVATE_PAY.items():
        if p.insurer in plans and rng.random() < R.PRIVATE_PAY_SHARE:
            p.private_pay.add(spec)
    if p.age(w.anchor) >= 18 and not p.recovered:
        for spec, share in R.PENDING_REFERRAL.items():
            if rng.random() < share:
                p.referrals.add(spec)


def add_person(w: World, p: Person) -> Person:
    w.people.append(p)
    w.names_taken.add(p.full_name)
    return p


def load_recovered(w: World) -> None:
    rng = w.rng
    doc = json.loads((SEED_DIR / "recovered_patients.json").read_text())
    for rec in doc["patients"]:
        if date.fromisoformat(rec["date_of_birth"]) > w.anchor:
            w.skipped.append(rec["patient_id"])  # not born yet on an early anchor
            continue
        age = age_months(date.fromisoformat(rec["date_of_birth"]), w.anchor) // 12
        insurer = rec["insurer"] or draw_insurer(rng, age, "centro", "es_general")
        homes = [h for h in ("centro", "norte", "sur") if insurer_fits_home(insurer, h, w.cat)]
        home = rng.choices(homes, weights=[R.HOME_SITE[h] for h in homes])[0]
        p = Person(idx=len(w.people), patient_id=rec["patient_id"], given=rec["given_name"],
                   first=rec["first_surname"], second=rec["second_surname"], sex=rec["sex"],
                   dob=date.fromisoformat(rec["date_of_birth"]), national_id=rec["national_id"],
                   insurer=insurer, home=home, recovered=True, case=rec["case_identity"],
                   referrals=set(rec["referrals"] or []),
                   seen_intent=True if rec["has_visited_before"] is None else rec["has_visited_before"])
        p.prosper_hints = prosper_hints(rec["note"])
        w.used_ids.add(p.national_id)
        if rec["phone"]:
            p.phone = rec["phone"]
            w.used_phones.add(p.phone)
        add_person(w, p)
    for p in w.people:  # phones the recovery could not keep
        if not p.phone:
            p.phone = new_phone(w, rng, p.age(w.anchor), p.home)
        p.email = new_email(rng, p) if rng.random() < email_share(p.age(w.anchor)) else ""
        finish_person(w, p, rng)
    by_id = {p.patient_id: p for p in w.people}
    for patient, relative, rel_label, pat_label in R.RECOVERED_LINKS:
        a, b = by_id[patient], by_id[relative]
        a.relatives.append((b.idx, rel_label, a.phone == b.phone, True))
        b.relatives.append((a.idx, pat_label, a.phone == b.phone, False))
    # demo personas: light, fixed diaries
    josefa, lucas, ignacio = by_id["P00001"], by_id["P00003"], by_id["P00005"]
    josefa.old_plan, josefa.past_budget, josefa.future_budget = [("general_practice", "PR01")], 0, 0
    lucas.old_plan, lucas.past_budget, lucas.future_budget = [("orthopaedics", "PR10")] * 2, 1, 1
    ignacio.old_plan, ignacio.past_budget, ignacio.future_budget = [("orthopaedics", "PR06")] * 3, 1, 0
    for p in (josefa, lucas, ignacio):
        p.recent_first, p.private_pay = False, set()


DROP_HINT = (r"\b(19|20)\d\d\b|visit|seen|attend|first contact|record is empty|chart|new to the clinic|"
             r"no history|history|appointments? (on file|ahead)|on the books|on the diary|known to the clinic|"
             r"existing patient|a regular of|goes back to|coming here since|usual place|lapsed|old patient|"
             r"nothing since|not been in|quiet after|on file, never|appointment ahead")


def prosper_hints(note: str) -> list[str]:
    """The platform's notes mixed stale history with caller-handling hints; keep only the hints
    (and the referral sentences, which match the referrals kept on file)."""
    protected = re.sub(r"\b(Dra?|D)\. ", lambda m: m.group(1) + "§ ", note)
    out = []
    for sentence in re.split(r"(?<=[.!?])\s+", protected):
        sentence = sentence.replace("§", ".").strip()
        if sentence and not re.search(DROP_HINT, sentence, re.I):
            out.append(sentence)
    return out


def add_featured(w: World) -> None:
    rng = w.rng
    a0 = w.anchor

    def person(spec: dict, home: str, insurer: str, language: str = "es") -> Person:
        dob = spec["date_of_birth"]
        if dob == "turns_14":
            dob = years_before(a0 + timedelta(days=13), 14)
        else:
            dob = date.fromisoformat(dob)
        p = Person(idx=len(w.people), patient_id="", given=spec["given_name"], first=spec["first_surname"],
                   second=spec["second_surname"], sex=spec["sex"], dob=dob,
                   insurer=spec.get("insurer", insurer), home=home, language=language,
                   known_as=spec.get("known_as", ""), no_email=spec.get("no_email", False),
                   phone_kind=spec.get("phone_kind", "mobile"))
        p.national_id = spec.get("national_id") or new_national_id(w, rng, spec.get("nie"))
        w.used_ids.add(p.national_id)
        if spec.get("note"):
            p.notes.append(spec["note"])
        return add_person(w, p)

    amelia = dict(R.AMELIA_WILLIAMS)
    p = person(amelia, amelia["home"], amelia["insurer"], amelia["language"])
    p.phone = amelia["phone"]
    w.used_phones.add(p.phone)
    by_key: dict[str, Person] = {}
    for spec in R.ROSARIO_SANZ:
        by_key[spec["key"]] = person(spec, spec["home"], spec["insurer"])
    families = [(fam, [person(m, fam["site"], fam["insurer"], fam.get("language", "es")) for m in fam["members"]])
                for fam in R.FAMILIES]
    for fam, members in families:
        for spec, p in zip(fam["members"], members, strict=True):
            by_key[spec["key"]] = p
    for spec in R.ROSARIO_SANZ + [m for fam in R.FAMILIES for m in fam["members"]]:
        p = by_key[spec["key"]]
        for other_key, label, back in spec.get("relatives", []):
            other = by_key[other_key]
            p.relatives.append((other.idx, label, False, False))
            other.relatives.append((p.idx, back, False, spec.get("carer_of") == other_key))
    # phones: the owner first, children share the owner's (teenagers keep a mobile of their own)
    for fam, members in families:
        owner = next((p for spec, p in zip(fam["members"], members, strict=True) if spec.get("phone_owner")), None)
        for p in members:
            if owner and p is not owner and p.age(a0) < 14:
                continue
            p.phone = new_phone(w, rng, p.age(a0), p.home, p.phone_kind)
        if owner:
            owner.phone = owner.phone or new_phone(w, rng, owner.age(a0), owner.home)
            for p in members:
                if p.age(a0) < 14:
                    p.phone = owner.phone
    for p in w.people:
        if not p.phone:
            p.phone = new_phone(w, rng, p.age(a0), p.home, p.phone_kind)
    for p in w.people:
        if p.recovered or p.email:
            continue
        if p.age(a0) < 14:
            continue
        p.email = "" if p.no_email or rng.random() >= email_share(p.age(a0)) else new_email(rng, p)
    for p in w.people:
        if not p.recovered and p.age(a0) < 14:
            guardian = next((w.people[i] for i, label, _, _ in p.relatives if label in ("Mother", "Father")
                             and w.people[i].phone == p.phone), None)
            p.email = guardian.email if guardian and rng.random() < 0.7 else ""
        if not p.recovered and not p.usual_gp:
            finish_person(w, p, rng)
    # shared-phone flags now that phones are known
    for p in w.people:
        p.relatives = [(i, label, w.people[i].phone == p.phone, calls) for i, label, _, calls in p.relatives]


def add_generated(w: World, total: int) -> None:
    rng, a0 = w.rng, w.anchor
    n = total - len(w.people)
    counts = [round(n * share) for _, _, share, _ in R.AGE_BRACKETS]
    counts[6] += n - sum(counts)  # rounding slack on the 45-64 bracket
    adults: list[Person] = []
    children: list[tuple[int, int, float]] = []
    for (lo, hi, _, female), count in zip(R.AGE_BRACKETS, counts, strict=True):
        for _ in range(count):
            if lo >= 18:
                adults.append(make_adult(w, rng, lo, hi, female))
            else:
                children.append((lo, hi, female))
    # partners
    pool = [p for p in adults if 25 <= p.age(a0) <= 85]
    rng.shuffle(pool)
    single = {p.idx for p in pool}
    for p in pool:
        if p.idx not in single or rng.random() > 0.35:
            continue
        for q in rng.sample(pool, min(40, len(pool))):
            if (q.idx in single and q is not p and q.sex != p.sex and abs(q.age(a0) - p.age(a0)) <= 8
                    and (q.origin.startswith("es")) == (p.origin.startswith("es"))):
                single -= {p.idx, q.idx}
                p.relatives.append((q.idx, "Partner", False, False))
                q.relatives.append((p.idx, "Partner", False, False))
                q.home = p.home if insurer_fits_home(q.insurer, p.home, w.cat) else q.home
                break
    # adult children who ring for a parent aged 80+
    elders = [p for p in adults if p.age(a0) >= 80]
    helpers = [p for p in adults if 40 <= p.age(a0) <= 65 and p.origin == "es_general"]
    rng.shuffle(helpers)
    for elder in elders:
        if elder.origin != "es_general" or rng.random() > 0.35 or not helpers:
            continue
        child = helpers.pop()
        if child.age(a0) + 18 > elder.age(a0):
            continue
        first, second = (elder.first, child.second) if elder.sex == "M" else (child.first, elder.first)
        if not name_ok(w, child.given, first, second):
            continue
        w.names_taken.discard(child.full_name)
        child.first, child.second = first, second
        w.names_taken.add(child.full_name)
        label = "Son" if child.sex == "M" else "Daughter"
        elder.relatives.append((child.idx, label, False, True))
        child.relatives.append((elder.idx, "Father" if elder.sex == "M" else "Mother", False, False))
    # children, attached to a registered parent where one fits
    other_surname: dict[int, str] = {}
    kids_of: Counter = Counter()
    for lo, hi, female in children:
        dob = random_dob(rng, a0, lo, hi)
        sex = "F" if rng.random() < female else "M"
        mother_side = rng.random() < 0.7
        fitting = [p for p in adults if p.sex == ("F" if mother_side else "M")
                   and 20 <= dob.year - p.dob.year <= (45 if mother_side else 50) and kids_of[p.idx] < 3]
        with_kids = [p for p in fitting if kids_of[p.idx]]
        guardian = (rng.choice(with_kids) if with_kids and rng.random() < 0.5 else
                    rng.choice(fitting) if fitting and rng.random() < 0.9 else None)
        origin = guardian.origin if guardian else weighted(rng, R.ORIGIN)
        group = guardian.group if guardian else foreign_group(origin, rng)
        partner = next((w.people[i] for i, label, _, _ in guardian.relatives if label == "Partner"), None) if guardian else None
        for _ in range(20):
            given = draw_given(rng, sex, dob, origin, group)
            if guardian:
                other = partner.first if partner else other_surname.setdefault(guardian.idx, draw_surname(rng, origin, group))
                first, second = (other, guardian.first) if guardian.sex == "F" else (guardian.first, other)
            else:
                first, second = draw_surname(rng, origin, group), draw_surname(rng, origin, group)
            siblings = {w.people[i].given for i, label, _, _ in (guardian.relatives if guardian else [])
                        if label in ("Son", "Daughter")}
            if name_ok(w, given, first, second) and given not in siblings:
                break
        p = Person(idx=len(w.people), patient_id="", given=given, first=first, second=second, sex=sex, dob=dob,
                   origin=origin, group=group, home=guardian.home if guardian else weighted(rng, R.HOME_SITE))
        p.language = guardian.language if guardian else draw_language(rng, origin, group)
        p.national_id = new_national_id(w, rng, nie_for(rng, origin))
        age = p.age(a0)
        if guardian:
            roll = rng.random()
            p.insurer = (guardian.insurer if roll < R.CHILD_INSURER["same_as_guardian"] else "privado"
                         if roll < 0.97 else draw_insurer(rng, age, p.home, origin))
            if not insurer_fits_home(p.insurer, p.home, w.cat):
                p.insurer = guardian.insurer
            own_phone = age >= 14 and rng.random() < 0.5
            p.phone = new_phone(w, rng, age, p.home) if own_phone else guardian.phone
            p.email = guardian.email if guardian.email and rng.random() < 0.7 else ""
            kids_of[guardian.idx] += 1
            label = "Son" if sex == "M" else "Daughter"
            parent_label = "Mother" if guardian.sex == "F" else "Father"
            p.relatives.append((guardian.idx, parent_label, p.phone == guardian.phone, False))
            guardian.relatives.append((p.idx, label, p.phone == guardian.phone, False))
            if partner:
                p.relatives.append((partner.idx, "Father" if partner.sex == "M" else "Mother", False, False))
                partner.relatives.append((p.idx, label, False, False))
        else:
            p.insurer = draw_insurer(rng, age, p.home, origin)
            p.phone = new_phone(w, rng, max(age, 30), p.home)
            p.email = new_email(rng, p) if rng.random() < R.EMAIL_ON_FILE["0-13"] else ""
        p.seen_intent = rng.random() < R.HAS_VISITED_BEFORE
        add_person(w, p)
        finish_person(w, p, rng)
    for p in adults:
        finish_person(w, p, rng)


def nie_for(rng, origin: str) -> str | None:
    return weighted(rng, R.NIE_PREFIX) if origin in ("latam_nie", "expat_en", "expat_eu", "ro_ua", "maghreb", "china") else None


def draw_language(rng, origin: str, group: str | None = None) -> str:
    if group in ("fr", "it", "de", "pt"):
        return group
    if group == "ua":
        return weighted(rng, {"uk": 0.8, "es": 0.2})
    if group == "ro":
        return weighted(rng, {"ro": 0.7, "es": 0.3})
    return weighted(rng, R.PREFERRED_LANGUAGE[origin])


def make_adult(w: World, rng, lo: int, hi: int, female: float) -> Person:
    a0 = w.anchor
    dob = random_dob(rng, a0, lo, hi)
    sex = "F" if rng.random() < female else "M"
    origin = weighted(rng, R.ORIGIN)
    group = foreign_group(origin, rng)
    for _ in range(50):
        given = draw_given(rng, sex, dob, origin, group)
        first, second = draw_surname(rng, origin, group), draw_surname(rng, origin, group)
        if name_ok(w, given, first, second):
            break
    home = weighted(rng, R.HOME_SITE)
    age = age_months(dob, a0) // 12
    p = Person(idx=len(w.people), patient_id="", given=given, first=first, second=second, sex=sex, dob=dob,
               origin=origin, group=group, home=home)
    p.language = draw_language(rng, origin, group)
    p.insurer = draw_insurer(rng, age, home, origin)
    if not insurer_fits_home(p.insurer, home, w.cat):
        p.insurer = "privado"
    p.national_id = new_national_id(w, rng, nie_for(rng, origin))
    landline = R.LANDLINE_PRIMARY_SHARE["80+" if age >= 80 else "65-79" if age >= 65 else "other_adults"]
    p.phone_kind = "landline" if rng.random() < landline else "mobile"
    p.phone = new_phone(w, rng, age, home, p.phone_kind)
    p.email = new_email(rng, p) if rng.random() < email_share(age) else ""
    p.seen_intent = rng.random() < R.HAS_VISITED_BEFORE
    if age >= 45 and p.given in R.KNOWN_AS and rng.random() < 0.15:
        p.known_as = R.KNOWN_AS[p.given]
    return add_person(w, p)


# ── Placing appointments ─────────────────────────────────────────────────────────────────────


def type_for(spec: str, returning: bool) -> tuple[str, int]:
    return R.TYPE_FOR[(spec, returning)]


def policy_for(w: World, p: Person, provider: str, spec: str, site: str, day: date) -> str | None:
    s = w.cat.specialties[spec]
    months = age_months(p.dob, day)
    if months < 0 or months < s["min_age_months"] or (s["max_age_months"] is not None and months > s["max_age_months"]):
        return None
    if spec == "gynaecology" and p.sex != "F":
        return None
    if s["referral_required"] and spec not in p.referrals and p.recovered:
        return None
    for plan in (p.insurer, "privado" if spec in p.private_pay else None):
        if not plan or not w.cat.plan_ok(plan, provider, spec, site):
            continue
        allowance = w.cat.rules.get(plan, {}).get("annual_allowance", {}).get(spec)
        if allowance is not None:
            used = p.allowance_used.get(spec, 0) + sum(
                1 for r in p.rows if r["spec"] == spec and r["status"] == "booked" and r["date"].year == day.year)
            if used >= allowance:
                continue
        return plan
    return None


def place(w: World, p: Person, provider: str, day: date, start: int, spec: str, returning: bool,
          policy: str, status: str = "booked", attendance: str | None = None, fixed_id: str | None = None,
          mark: int = 1) -> dict:
    type_id, dur = type_for(spec, returning)
    site, lo, state = cells(w, provider, day)
    if status == "booked" or mark == 3:
        for j in range((start - lo) // 15, (start - lo) // 15 + dur // 15):
            state[j] = mark
    row = {"patient": p.idx, "provider": provider, "site": site, "spec": spec, "type": type_id, "dur": dur,
           "date": day, "start": start, "status": status, "attendance": attendance, "policy": policy,
           "fixed_id": fixed_id}
    w.appointments.append(row)
    if status == "booked":
        p.rows.append(row)
        p.days_taken.add(day)
        if w.cat.specialties[spec]["referral_required"]:
            p.referrals.add(spec)
        if spec in w.cat.rules.get(policy, {}).get("authorization_required", []):
            p.authorizations.add(spec)
        if attendance == "attended" and (p.first_attended is None or day < p.first_attended):
            p.first_attended = day
    return row


def upcoming(p: Person, anchor: date, spec: str | None = None) -> list:
    return [r for r in p.rows if r["date"] >= anchor and (spec is None or r["spec"] == spec)]


def candidate_ok(w: World, p: Person, provider: str, day: date, start: int, dur: int, spec: str,
                 phase: str) -> str | None:
    """Policy when this person can take this block in this phase, else None."""
    if day in p.days_taken:
        return None
    if phase == "future":
        if p.future_budget <= 0:
            return None
        mine = upcoming(p, w.anchor, spec)
        if len(upcoming(p, w.anchor)) >= R.MAX_UPCOMING or len(mine) >= R.MAX_UPCOMING_PER_SPECIALTY.get(spec, 1):
            return None
        if any(abs((r["date"] - day).days) < 21 for r in mine):
            return None
    else:
        if p.past_budget <= 0:
            return None
        mine = [r for r in p.rows if r["spec"] == spec and w.history_start <= r["date"] < w.anchor]
        if len(mine) >= 2 or any(abs((r["date"] - day).days) < 7 for r in mine):
            return None
    return policy_for(w, p, provider, spec, cells(w, provider, day)[0], day)


def tod_weight(spec: str, provider: str, day: date, minute: int) -> float:
    table = R.TOD_MORNING if minute < 14 * 60 else R.TOD_AFTERNOON
    weight = 1.0
    for key in sorted(table):
        if minutes(key) <= minute:
            weight = table[key]
    if spec == "paediatrics":
        for key in sorted(R.TOD_PAEDIATRICS):
            if minutes(key) <= minute:
                weight = R.TOD_PAEDIATRICS[key]
    if provider == "PR10" and day.weekday() == 4 and minute >= 14 * 60:
        weight *= 0.5  # the Friday-afternoon soft spot where 45-minute first visits still fit
    return weight


class Pools:
    """Candidate lists per (specialty, kind, site) with lazy removal of people who ran out of budget."""

    def __init__(self, w: World, phase: str):
        self.w, self.phase = w, phase
        self.lists: dict = {}
        a0 = w.anchor
        for spec in w.cat.specialties:
            s = w.cat.specialties[spec]
            for p in w.people:
                if p.case and p.patient_id in R.DEMO_PERSONAS:
                    continue
                months = age_months(p.dob, a0)
                if months < s["min_age_months"] - 3 or (s["max_age_months"] is not None and months > s["max_age_months"] + 3):
                    continue
                if phase == "future":
                    kind = "returning" if p.first_attended else "new"
                else:
                    if not p.seen_intent:
                        continue
                    kind = "new" if p.recent_first and p.first_attended is None else "returning"
                for key in ((spec, kind, p.home), (spec, kind, "all")):
                    self.lists.setdefault(key, []).append(p)
                if spec == "general_practice":
                    self.lists.setdefault((spec, kind, p.usual_gp), []).append(p)

    def pick(self, provider: str, day: date, start: int, spec: str, returning: bool, tries: int = 40):
        w, rng = self.w, self.w.rng
        kind = "returning" if returning else "new"
        site = cells(w, provider, day)[0]
        dur = type_for(spec, returning)[1]
        for _ in range(tries):
            roll = rng.random()
            key = ((spec, kind, provider) if spec == "general_practice" and roll < 0.5 else
                   (spec, kind, site) if roll < 0.85 else (spec, kind, "all"))
            lst = self.lists.get(key) or self.lists.get((spec, kind, "all"))
            if not lst:
                return None
            i = rng.randrange(len(lst))
            p = lst[i]
            budget = p.future_budget if self.phase == "future" else p.past_budget
            if budget <= 0:
                lst[i] = lst[-1]
                lst.pop()
                continue
            if self.phase == "past":
                if returning and not (p.first_attended and p.first_attended < day):
                    continue
                if not returning and p.first_attended is not None:
                    lst[i] = lst[-1]
                    lst.pop()
                    continue
            elif returning != bool(p.first_attended):
                continue
            policy = candidate_ok(w, p, provider, day, start, dur, spec, self.phase)
            if policy:
                return p, policy
        return None


def fill_day(w: World, pools: Pools, provider: str, day: date, target: float, phase: str,
             sequential: bool = False) -> None:
    g = cells(w, provider, day)
    if not g or target <= 0:
        return
    _, lo, state = g
    rng = w.rng
    spec = w.cat.spec_of(provider)
    open_cells = sum(1 for v in state if v in (0, 1, 3))
    goal = min(open_cells, round(target * open_cells))
    booked = sum(1 for v in state if v == 1)
    if sequential:
        order = list(range(len(state)))
    else:
        keyed = [(-(rng.random() ** (1 / tod_weight(spec, provider, day, lo + 15 * i))), i) for i in range(len(state))]
        order = [i for _, i in sorted(keyed)]
    queue = list(reversed(order))
    requeued = 0
    while booked < goal and queue:
        i = queue.pop()
        if state[i] != 0:
            continue
        new_first = rng.random() < (0.35 if sequential else R.NEW_PATIENT_SHARE[spec])
        placed = False
        for returning in ((False, True) if new_first else (True, False)):
            n = type_for(spec, returning)[1] // 15
            for start_i in (i, i - 1, i - 2)[:n]:
                if not fits(state, start_i, n):
                    continue
                start = lo + 15 * start_i
                got = pools.pick(provider, day, start, spec, returning, tries=120 if sequential else 40)
                if not got:
                    continue
                p, policy = got
                status, attendance, mark = "booked", None, 1
                if phase == "past":
                    roll = rng.random()
                    no_show = R.PAST_STATUS["no_show"] * (2 if p.sex == "M" and p.age(day) < 35 else 1)
                    if returning and roll < R.PAST_STATUS["cancelled"]:
                        status = "cancelled"
                    elif returning and roll < R.PAST_STATUS["cancelled"] + no_show:
                        attendance = "no_show"
                    else:
                        attendance = "attended"
                elif not sequential and rng.random() < R.FUTURE_CANCELLED_SHARE:
                    status, mark = "cancelled", (3 if rng.random() < 0.7 else 0)
                place(w, p, provider, day, start, spec, returning, policy, status, attendance, mark=mark)
                if status == "booked":
                    booked += n
                    if phase == "past":
                        p.past_budget -= 1
                    else:
                        p.future_budget -= 1
                elif phase == "past" and rng.random() < 0.6 and requeued < 50:
                    queue.insert(0, i)
                    requeued += 1
                placed = True
                break
            if placed:
                break


def target_for(w: World, provider: str, day: date) -> float:
    spec = w.cat.spec_of(provider)
    if day < w.anchor:
        before = (w.anchor - day).days
        base = next(occ for limit, occ in R.PAST_OCCUPANCY if before <= limit)
        return base * (R.AUGUST_FACTOR if day.month == 8 else 1) * w.s_past
    if day == w.anchor:
        return R.TODAY_OCCUPANCY * w.s_future
    if provider == R.FULL_PROVIDER and day <= w.dense_end:
        return 1.0
    offset = (day - w.anchor).days - 1
    week = offset // 7
    if day <= w.dense_end:
        table = R.FUTURE_OCCUPANCY[spec]
        base = table[min(week, len(table) - 1)]
        if spec in ("general_practice", "paediatrics"):
            base += 0.05 if day.weekday() == 0 else -0.05 if day.weekday() == 4 else 0
        if (day - timedelta(days=1)) in w.closed_all:
            base += 0.08
    else:
        tail_weeks = max(1, w.args.tail_weeks)
        k = week - w.args.dense_weeks
        hi, lo = R.TAIL_OCCUPANCY
        base = hi - (hi - lo) * (k / max(1, tail_weeks - 1))
    for a in w.absences:  # a diary reopened after a whole-day absence fills up late
        if a["provider_id"] == provider and a["reason"] == "sick leave" and 0 < (day - a["end"]).days <= 4:
            base *= 0.6
    return min(1.0, base) * w.s_future


def demand_rows(w: World, first: date, last: date) -> float:
    total = 0.0
    for provider in w.cat.providers:
        spec = w.cat.spec_of(provider)
        avg = (R.NEW_PATIENT_SHARE[spec] * type_for(spec, False)[1] + (1 - R.NEW_PATIENT_SHARE[spec]) * type_for(spec, True)[1]) / 15
        per_episode = 5 if spec == "physiotherapy" else 1
        for day in days(first, last):
            g = cells(w, provider, day)
            if g:
                total += target_for(w, provider, day) * len(g[2]) / avg / per_episode
    return total


# ── Diary phases ─────────────────────────────────────────────────────────────────────────────


def ignacio_and_holes(w: World) -> None:
    rng, a0 = w.rng, w.anchor
    spec = R.IGNACIO_APPOINTMENT
    ignacio = next(p for p in w.people if p.patient_id == spec["patient_id"])
    day = next_weekday(a0 + timedelta(days=spec["min_days_ahead"]), spec["weekday"])
    start = minutes(spec["time"])
    while True:
        g = cells(w, spec["provider_id"], day)
        if g and g[0] == spec["location_id"] and fits(g[2], (start - g[1]) // 15, 1):
            break
        day += timedelta(days=7)
    place(w, ignacio, spec["provider_id"], day, start, "dermatology", True, spec["policy_id"],
          fixed_id=spec["appointment_id"])

    def hole(specialty: str, first: date, last: date, n_cells: int, avoid: set) -> bool:
        providers = [p for p in w.cat.by_spec[specialty] if p != R.FULL_PROVIDER]
        options = []
        for day in days(first, last):
            for provider in providers:
                g = cells(w, provider, day)
                if g and (provider, day) not in avoid:
                    options += [(provider, day, i) for i in range(len(g[2])) if fits(g[2], i, n_cells)]
        if not options:
            return False
        provider, day, i = rng.choice(options)
        site, lo, _ = cells(w, provider, day)
        returning = n_cells == type_for(specialty, True)[1] // 15
        for p in rng.sample(w.people, min(60, len(w.people))):
            if p.patient_id in R.DEMO_PERSONAS or (p.seen_intent != returning):
                continue
            policy = policy_for(w, p, provider, specialty, site, day)
            if policy:
                place(w, p, provider, day, lo + 15 * i, specialty, returning, policy, "cancelled", mark=3)
                break
        for j in range(i, i + n_cells):
            cells(w, provider, day)[2][j] = 3
        avoid.add((provider, day))
        return True

    d1, d7, d14, d21 = (a0 + timedelta(days=k) for k in (1, 7, 14, 21))
    avoid: set = set()
    for _ in range(2):
        hole("general_practice", d1, d7, 1, avoid)
        hole("dermatology", d1, d14, 1, avoid)
    hole("dermatology", d14 + timedelta(days=1), d21, 2, avoid) or hole("dermatology", d1, d21, 2, avoid)
    # one gap per specialty long enough for its new-patient type (dermatology: see above)
    for specialty, n_cells in (("general_practice", 2), ("paediatrics", 2), ("orthopaedics", 3),
                               ("gynaecology", 2), ("physiotherapy", 3)):
        hole(specialty, d1, d14, n_cells, avoid)


def old_visits(w: World, p: Person, count: int, plan: list | None = None) -> None:
    """Visits before the 8-week history window; the first is a new-patient type."""
    rng = w.rng
    first = max(w.old_start, p.dob + timedelta(days=7))
    span = (w.history_start - timedelta(days=1) - first).days
    if span <= 0:
        return
    last = w.history_start - timedelta(days=1 + int(span * rng.random() ** 1.5))
    targets = [last]
    for _ in range(count - 1):
        targets.append(max(first, targets[-1] - timedelta(days=rng.randint(30, 200))))
    targets = sorted(set(targets))
    for n, target in enumerate(targets):
        returning = p.first_attended is not None
        spec, provider = plan[n] if plan and n < len(plan) else (None, None)
        for shift in [0, 1, -1, 2, -2, 3, -3, 5, -5, 7, -7, 10, -10, 14, -14, 21, -21, 28, -28]:
            day = target + timedelta(days=shift)
            if not (w.old_start <= day < w.history_start) or day in p.days_taken:
                continue
            if returning and not (p.first_attended < day):
                continue
            s = spec or old_specialty(w, p, day)
            if not s:
                continue
            choices = [provider] if provider else sorted(w.cat.by_spec[s], key=lambda x: (
                0 if (s == "general_practice" and x == p.usual_gp) or p.home in w.cat.sites_of[x] else 1, rng.random()))
            done = False
            for prov in choices:
                g = cells(w, prov, day)
                if not g:
                    continue
                site, lo, state = g
                ok = policy_for(w, p, prov, s, site, day) or (
                    "privado" if policy_ok_private(w, p, prov, s, site, day) else None)
                if not ok:
                    continue
                n_cells = type_for(s, returning)[1] // 15
                free = [i for i in range(len(state)) if fits(state, i, n_cells)]
                if not free:
                    continue
                i = rng.choice(free)
                place(w, p, prov, day, lo + 15 * i, s, returning, ok, attendance="attended")
                done = True
                break
            if done:
                break


def policy_ok_private(w: World, p: Person, provider: str, spec: str, site: str, day: date) -> bool:
    saved = p.private_pay
    p.private_pay = saved | {spec}
    try:
        return policy_for(w, p, provider, spec, site, day) == "privado"
    finally:
        p.private_pay = saved


def old_specialty(w: World, p: Person, day: date) -> str | None:
    rng = w.rng
    if age_months(p.dob, day) < 0:
        return None
    if age_months(p.dob, day) < 168:
        options = {"paediatrics": 0.8, "orthopaedics": 0.1, "dermatology": 0.1}
    else:
        options = {"general_practice": 0.55, "orthopaedics": 0.15, "dermatology": 0.12}
        if p.sex == "F":
            options["gynaecology"] = 0.18
    if p.recovered and "dermatology" not in p.referrals:
        options.pop("dermatology", None)
    return weighted(rng, options)


def physio_courses(w: World) -> None:
    rng, a0 = w.rng, w.anchor
    provider = "PR09"
    week = w.history_start - timedelta(days=w.history_start.weekday())
    candidates = [p for p in w.people if p.patient_id not in R.DEMO_PERSONAS and p.age(a0) >= 14
                  and (not p.recovered or "physiotherapy" in p.referrals)]
    while week <= w.horizon_end - timedelta(days=7):
        week_days = [d for d in days(week, week + timedelta(days=6)) if w.history_start <= d <= w.horizon_end]
        goal = sum(target_for(w, provider, d) * len(cells(w, provider, d)[2]) for d in week_days if cells(w, provider, d))
        for _ in range(80):
            booked = sum(sum(1 for v in cells(w, provider, d)[2] if v == 1) for d in week_days if cells(w, provider, d))
            if booked >= goal:
                break
            pair = rng.choice(R.PHYSIO_PAIRS)
            day0 = week + timedelta(days=pair[0])
            if not (w.history_start <= day0 <= w.horizon_end):
                continue
            p = rng.choice(candidates)
            if p.in_course:
                continue
            past = day0 < a0
            if past:
                if p.past_budget <= 0:
                    continue
                if p.first_attended and p.first_attended < day0:
                    assessment = False
                elif p.recent_first and p.first_attended is None:
                    assessment = True
                else:
                    continue
            else:
                if p.future_budget <= 0 or (p.recent_first and p.first_attended is None):
                    continue
                assessment = p.first_attended is None
            if not policy_for(w, p, provider, "physiotherapy", "sur", day0):
                continue
            time = 9 * 60 + 15 * rng.randrange(0, 30)
            if assessment:
                window = list(days(max(w.history_start, day0 - timedelta(days=7)), day0 - timedelta(days=1))) if past else [day0]
                spot = find_spot(w, p, provider, window, time, 3)
                if not spot:
                    continue
                d, start = spot
                policy = policy_for(w, p, provider, "physiotherapy", "sur", d)
                if not policy:
                    continue
                place(w, p, provider, d, start, "physiotherapy", False, policy,
                      attendance="attended" if past else None)
                p.in_course = True
                if not past:
                    p.future_budget -= 1
                    continue
            sessions = rng.randint(*R.PHYSIO_SESSIONS)
            d = day0
            placed = 0
            while placed < sessions and d <= w.horizon_end:
                if d.weekday() in pair and d >= day0:
                    spot = find_spot(w, p, provider, [d], time, 2)
                    policy = spot and policy_for(w, p, provider, "physiotherapy", "sur", d)
                    if spot and policy and (d < a0 or len(upcoming(p, a0, "physiotherapy")) < R.MAX_UPCOMING_PER_SPECIALTY["physiotherapy"]):
                        status, attendance = "booked", None
                        if d < a0:
                            roll = rng.random()
                            status, attendance = (("cancelled", None) if roll < 0.05 else ("booked", "no_show")
                                                  if roll < 0.10 else ("booked", "attended"))
                        place(w, p, provider, d, spot[1], "physiotherapy", True, policy, status, attendance)
                        p.in_course = True
                        placed += 1
                d += timedelta(days=1)
            if past:
                p.past_budget -= 1
                if placed and any(r["date"] >= a0 for r in p.rows if r["spec"] == "physiotherapy"):
                    p.future_budget = max(0, p.future_budget - 1)
            else:
                p.future_budget -= 1
        week += timedelta(days=7)
    # a few course patients have spent their whole year's allowance elsewhere (allowance_exhausted)
    for p in w.people:
        if not p.in_course:
            continue
        allowance = w.cat.rules.get(p.insurer, {}).get("annual_allowance", {}).get("physiotherapy")
        per_year = Counter(r["date"].year for r in p.rows if r["spec"] == "physiotherapy" and r["status"] == "booked")
        if allowance and per_year and rng.random() < 0.15:
            # sessions already used elsewhere this year: exactly what is left, so the next one is refused
            p.allowance_used["physiotherapy"] = allowance - max(per_year.values())


def find_spot(w: World, p: Person, provider: str, window: list, time: int, n: int):
    for d in window:
        if d in p.days_taken:
            continue
        g = cells(w, provider, d)
        if not g:
            continue
        _, lo, state = g
        for start in (time, time + 15, time - 15, time + 30, time - 30):
            i = (start - lo) // 15
            if fits(state, i, n):
                return d, start
    return None


def build_diary(w: World) -> None:
    a0 = w.anchor
    ignacio_and_holes(w)
    # 1. older history for everyone the clinic has seen (except those first seen in the window)
    for p in w.people:
        if p.seen_intent and not p.recent_first and p.dob + timedelta(days=7) >= w.history_start:
            p.recent_first, p.past_budget = True, max(1, p.past_budget)  # too young for older visits
        if p.seen_intent and not p.recent_first:
            count = len(p.old_plan) or weighted(w.rng, R.OLD_VISITS)
            old_visits(w, p, count, p.old_plan or None)
    # 2. supply vs demand: scale the targets down when there are not enough patients
    past_supply = sum(p.past_budget for p in w.people)
    w.s_past = min(1.0, past_supply / max(1.0, demand_rows(w, w.history_start, a0 - timedelta(days=1))))
    full_rows = sum(len(cells(w, R.FULL_PROVIDER, d)[2]) for d in days(a0 + timedelta(days=1), w.dense_end)
                    if cells(w, R.FULL_PROVIDER, d)) / 1.5
    future_supply = sum(p.future_budget for p in w.people) - full_rows
    future_demand = demand_rows(w, a0, w.horizon_end) - full_rows
    w.s_future = max(0.05, min(1.0, future_supply / max(1.0, future_demand)))
    # 3. physiotherapy courses (they straddle past and future)
    physio_courses(w)
    # 4. the 8-week history, day by day so "seen before" is always true at the time
    # (in rounds, so when patients run out every day ends up a little emptier, not some days bare)
    pools = Pools(w, "past")
    for share in ROUNDS:
        for day in days(w.history_start, a0 - timedelta(days=1)):
            for provider in sorted(w.cat.providers):
                if provider != "PR09":
                    fill_day(w, pools, provider, day, share * target_for(w, provider, day), "past")
    for p in w.people:  # a planned first visit that found no room becomes an older one
        if p.seen_intent and p.first_attended is None:
            old_visits(w, p, weighted(w.rng, R.OLD_VISITS))
    # 5. the fully booked provider, then everyone else
    pools = Pools(w, "future")
    for day in days(a0 + timedelta(days=1), w.dense_end):
        fill_day(w, pools, R.FULL_PROVIDER, day, 1.0, "future", sequential=True)
    slots = [(provider, day) for day in days(a0, w.horizon_end) for provider in sorted(w.cat.providers)
             if not (provider == R.FULL_PROVIDER and a0 < day <= w.dense_end)]
    w.rng.shuffle(slots)
    for share in ROUNDS:
        for provider, day in slots:
            fill_day(w, pools, provider, day, share * target_for(w, provider, day), "future")


# ── Notes, ids, output ──────────────────────────────────────────────────────────────────────


def history_sentence(w: World, p: Person) -> str:
    visits = sorted((r for r in p.rows if r["attendance"] == "attended"), key=lambda r: (r["date"], r["start"]))
    if not visits:
        return "New to the clinic; no visit history yet."
    last = visits[-1]
    doctor = w.cat.providers[last["provider"]]["name"]
    site = w.cat.locations[last["site"]]["name"]
    count = "One visit on file" if len(visits) == 1 else f"{len(visits)} visits on file"
    text = f"Last seen {last['date'].strftime('%B %Y')}, by {doctor} at {site}. {count}."
    sites = {r["site"] for r in visits}
    if len(visits) > 1 and len(sites) == 1:
        text += f" Every visit so far has been at {site}."
    return text


def relative_sentences(w: World, p: Person) -> list[str]:
    out, children = [], []
    for i, label, same_phone, calls in p.relatives:
        other = w.people[i]
        if label in ("Son", "Daughter") and other.age(w.anchor) < 18 and p.age(w.anchor) >= 18:
            children.append((other, same_phone))
            continue
        text = f"{label}: {other.full_name} ({other.patient_id})"
        if same_phone:
            text += ", same phone"
        if calls:
            text += ", usually calls on his behalf" if p.sex == "M" else ", usually calls on her behalf"
        out.append(text + ".")
    if children:
        names = ", ".join(f"{c.given} ({c.patient_id})" for c, _ in children)
        shared = " -- same phone" if all(s for _, s in children) else ""
        out.append(f"Children on file: {names}{shared}.")
    return out


def build_note(w: World, p: Person) -> str:
    rng = w.rng
    parts = [history_sentence(w, p)]
    parts += relative_sentences(w, p)
    if p.language != "es" and p.language in R.LANGUAGE_NOTE:
        parts.append(R.LANGUAGE_NOTE[p.language])
    if p.known_as:
        parts.append(f"Known as {p.known_as}.")
    parts += p.notes
    if p.recovered:
        parts += p.prosper_hints
    elif rng.random() < R.HINT_SHARE:
        age = p.age(w.anchor)
        pool = R.CHILD_HINTS if age < 14 else R.ELDERLY_HINTS if age >= 80 else R.GENERIC_HINTS
        hint = rng.choice(pool)
        if not (hint.startswith("Does not use email") and p.email):
            parts.append(hint)
    return " ".join(parts)


def created_at(w: World, row: dict, start: datetime) -> float:
    median, p90 = R.LEAD_DAYS[row["spec"]]
    sigma = math.log(p90 / median) / 1.2816
    lead = max(0.2, median * math.exp(w.rng.gauss(0, sigma)))
    created = start - timedelta(days=lead, minutes=w.rng.randrange(600))
    cutoff = datetime(w.anchor.year, w.anchor.month, w.anchor.day, 7, 30, tzinfo=MADRID) - timedelta(minutes=w.rng.randrange(1, 900))
    return round(min(created, cutoff).timestamp(), 3)


def finalize(w: World) -> tuple[list, list]:
    next_id = FIRST_NEW_PATIENT
    for p in w.people:
        if not p.patient_id:
            p.patient_id = f"P{next_id:05d}"
            next_id += 1
    patients = []
    for p in w.people:
        visited = any(r["attendance"] == "attended" for r in p.rows)
        patients.append({
            "patient_id": p.patient_id, "given_name": p.given, "first_surname": p.first,
            "second_surname": p.second, "national_id": p.national_id, "date_of_birth": p.dob.isoformat(),
            "phone": p.phone, "sex": p.sex, "has_visited_before": visited, "insurer": p.insurer,
            "referrals": sorted(p.referrals), "note": build_note(w, p), "email": p.email, "source": "seed",
            "insurer_authorizations": sorted(p.authorizations), "allowance_used": dict(p.allowance_used),
        })
    rows = sorted(w.appointments, key=lambda r: (r["date"], r["start"], r["provider"], r["status"] != "booked"))
    out, n = [], FIRST_APPOINTMENT
    for r in rows:
        p = w.people[r["patient"]]
        appointment_id = r["fixed_id"] or f"A{n:06d}"
        if not r["fixed_id"]:
            n += 1
        start = datetime(r["date"].year, r["date"].month, r["date"].day, r["start"] // 60, r["start"] % 60, tzinfo=MADRID)
        data = {
            "provider_id": r["provider"], "provider_name": w.cat.providers[r["provider"]]["name"],
            "specialty_id": r["spec"], "location_id": r["site"], "appointment_type_id": r["type"],
            "start_time": start_iso(r["date"], r["start"]), "duration_minutes": r["dur"],
            "payable_with": [r["policy"]], "appointment_id": appointment_id, "patient_id": p.patient_id,
            "policy_id": r["policy"], "patient_name": p.full_name, "source": "seed", "call_id": None,
            "updated_at": created_at(w, r, start),
        }
        if r["attendance"]:
            data["attendance"] = r["attendance"]
        out.append((appointment_id, p.patient_id, r["status"], data))
    return patients, out


def write_db(path: Path, w: World, patients: list, appointments: list, closures: list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path)
    try:
        with db:
            for table in TABLES:
                db.execute(f"DROP TABLE IF EXISTS {table}")
            db.executescript(SCHEMA)
            params = {"anchor": w.anchor.isoformat(), "patients": w.args.patients, "seed": w.args.seed,
                      "dense_weeks": w.args.dense_weeks, "tail_weeks": w.args.tail_weeks,
                      "history_start": w.history_start.isoformat(), "old_start": w.old_start.isoformat(),
                      "generator": GENERATOR}
            meta = {"catalogue": json.dumps(w.cat.data, ensure_ascii=False), "anchor": w.anchor.isoformat(),
                    "horizon_end": w.horizon_end.isoformat(), "seed_params": json.dumps(params),
                    "seeded_at": datetime.now(MADRID).isoformat(timespec="seconds")}
            db.executemany("INSERT INTO meta VALUES (?, ?)", meta.items())
            db.executemany("INSERT INTO closures VALUES (?, ?, ?)", closures)
            db.executemany(
                "INSERT INTO absences (provider_id, start_date, end_date, start_time, end_time, reason) VALUES (?, ?, ?, ?, ?, ?)",
                [(a["provider_id"], a["start"].isoformat(), a["end"].isoformat(), a["start_time"], a["end_time"], a["reason"])
                 for a in w.absences])
            db.executemany("INSERT INTO patients VALUES (?, ?, ?)",
                           [(p["patient_id"], p["national_id"], json.dumps(p, ensure_ascii=False)) for p in patients])
            db.executemany("INSERT INTO appointments VALUES (?, ?, ?, ?, ?, ?, ?)",
                           [(aid, pid, status, json.dumps(data, ensure_ascii=False), data["provider_id"],
                             data["start_time"][:10], data["start_time"]) for aid, pid, status, data in appointments])
    finally:
        db.close()


def db_has_rows(path: Path) -> bool:
    if not path.exists() or path.stat().st_size == 0:
        return False
    db = sqlite3.connect(path)
    try:
        tables = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        return any(db.execute(f"SELECT 1 FROM {t} LIMIT 1").fetchone() for t in tables if t in TABLES)
    finally:
        db.close()


def is_seeded(path: Path) -> bool:
    """A database this script built: it holds the clinic catalogue in `meta`."""
    if not path.exists() or path.stat().st_size == 0:
        return False
    db = sqlite3.connect(path)
    try:
        if not db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='meta'").fetchone():
            return False
        return db.execute("SELECT 1 FROM meta WHERE key='catalogue'").fetchone() is not None
    finally:
        db.close()


def build(args) -> World:
    cat = Catalogue(json.loads((SEED_DIR / "catalogue.json").read_text()))
    w = World(args, cat)
    if w.old_start >= w.history_start or w.horizon_end > R.CALENDAR_LAST:
        raise SystemExit(f"anchor {w.anchor} needs holidays outside the table ({R.CALENDAR_FIRST}..{R.CALENDAR_LAST})")
    w.closure_rows = build_closures(w)
    build_absences(w)
    load_recovered(w)
    add_featured(w)
    minimum = len(w.people) + 1
    if args.patients < minimum:
        raise SystemExit(f"--patients must be at least {minimum} (recovered and hand-shaped people)")
    add_generated(w, args.patients)
    build_diary(w)
    return w


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--db", type=Path, default=Path(os.getenv("LOCAL_CLINIC_DB", str(BACKEND / "data/clinic.sqlite3"))))
    parser.add_argument("--anchor", type=date.fromisoformat, default=datetime.now(MADRID).date())
    parser.add_argument("--patients", type=int, default=3000)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--dense-weeks", type=int, default=4)
    parser.add_argument("--tail-weeks", type=int, default=4)
    parser.add_argument("--force", action="store_true", help="overwrite a database that already has rows")
    parser.add_argument(
        "--if-unseeded",
        action="store_true",
        help="deploy-safe: do nothing if the database is already seeded, else rebuild it (like --force)",
    )
    parser.add_argument("--quiet", action="store_true", help="only print failures")
    return parser.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    if args.if_unseeded:
        if is_seeded(args.db):
            print(f"{args.db} is already seeded; leaving it untouched.")
            return 0
        args.force = True  # an empty or pre-seed (old overlay) database is replaced
    if db_has_rows(args.db) and not args.force:
        print(f"{args.db} already has data; pass --force to rebuild it.", file=sys.stderr)
        return 2
    w = build(args)
    patients, appointments = finalize(w)
    write_db(args.db, w, patients, appointments, w.closure_rows)
    report = validate.check(args.db)
    if not args.quiet:
        print(validate.stats(args.db))
        print(f"\nscale factors: past {w.s_past:.2f}, future {w.s_future:.2f}")
    if w.skipped:
        print(f"skipped (born after the anchor): {', '.join(w.skipped)}")
    changed = [p.patient_id for p in w.people if p.recovered and p.seen_intent != any(
        r["attendance"] == "attended" for r in p.rows)]
    if changed:
        print(f"WARNING recovered people whose has_visited_before could not be kept: {', '.join(changed)}")
    for warning in report["warnings"]:
        print(f"WARNING {warning}")
    for error in report["errors"][:50]:
        print(f"FAIL {error}", file=sys.stderr)
    if report["errors"]:
        print(f"{len(report['errors'])} check(s) failed; the database at {args.db} is NOT valid.", file=sys.stderr)
        return 1
    print(f"OK {len(patients)} patients, {len(appointments)} appointments -> {args.db} "
          f"(anchor {w.anchor}, horizon {w.horizon_end})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
