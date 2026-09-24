"""Independent checks for a seeded clinic database, plus the stats report.

Reads only the SQLite file (schema, meta.catalogue, rows) and re-derives every rule from the
catalogue: it shares no code with the generator, so a generator bug cannot hide itself.
`check(path)` returns {"errors": [...], "warnings": [...]}; `stats(path)` returns printable text.
"""

import json
import re
import sqlite3
import unicodedata
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
from itertools import pairwise
from pathlib import Path
from zoneinfo import ZoneInfo

from seed import realism as R

MADRID = ZoneInfo("Europe/Madrid")
WEEKDAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
ID_LETTERS = "TRWAGMYFPDXBNJZSQVHLCKE"
COLUMNS = {
    "meta": ["key", "value"],
    "closures": ["date", "location_id", "name"],
    "absences": ["id", "provider_id", "start_date", "end_date", "start_time", "end_time", "reason"],
    "patients": ["patient_id", "national_id", "data"],
    "appointments": ["appointment_id", "patient_id", "status", "data", "provider_id", "start_date", "start_time"],
    "changes": ["id", "call_id", "operation_key", "created_at", "action", "result"],
}
INDEXES = {"appointments_provider_day", "appointments_day", "appointments_patient"}
PATIENT_KEYS = {"patient_id": str, "given_name": str, "first_surname": str, "second_surname": str,
                "national_id": str, "date_of_birth": str, "phone": str, "sex": str, "has_visited_before": bool,
                "insurer": str, "referrals": list, "note": str, "email": str, "source": str,
                "insurer_authorizations": list, "allowance_used": dict}
APPOINTMENT_KEYS = {"provider_id": str, "provider_name": str, "specialty_id": str, "location_id": str,
                    "appointment_type_id": str, "start_time": str, "duration_minutes": int, "payable_with": list,
                    "appointment_id": str, "patient_id": str, "policy_id": str, "patient_name": str,
                    "source": str, "updated_at": float}
EMAIL = re.compile(r"^[a-z0-9._%+-]+@example\.(com|org|net)$")


def mins(text: str) -> int:
    h, m = text.split(":")
    return int(h) * 60 + int(m)


def span(text: str) -> tuple[int, int]:
    a, b = text.replace("\u2013", "-").split("-")  # en dash in the catalogue
    return mins(a), mins(b)


def id_valid(value: str) -> bool:
    m = re.fullmatch(r"([XYZ]?)(\d+)([A-Z])", value)
    if not m:
        return False
    prefix, digits, letter = m.groups()
    if len(digits) != (7 if prefix else 8):
        return False
    number = int(str("XYZ".index(prefix)) + digits) if prefix else int(digits)
    return ID_LETTERS[number % 23] == letter


def months_old(dob: date, day: date) -> int:
    return (day.year - dob.year) * 12 + day.month - dob.month - (day.day < dob.day)


def tokens(text: str) -> set[str]:
    return {"".join(c for c in unicodedata.normalize("NFKD", w) if c.isalnum()).lower() for w in text.split()}


class Clinic:
    """The seeded database, loaded once, with the catalogue rules re-derived."""

    def __init__(self, path: Path):
        db = sqlite3.connect(path)
        db.row_factory = sqlite3.Row
        try:
            self.tables = {r[0]: [c[1] for c in db.execute(f"PRAGMA table_info({r[0]})")]
                           for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            self.indexes = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='index'")}
            self.meta = {r["key"]: r["value"] for r in db.execute("SELECT key, value FROM meta")}
            self.closure_rows = [dict(r) for r in db.execute("SELECT * FROM closures")]
            self.absences = [dict(r) for r in db.execute("SELECT * FROM absences")]
            self.patient_rows = [dict(r) for r in db.execute("SELECT * FROM patients")]
            self.appointment_rows = [dict(r) for r in db.execute("SELECT * FROM appointments")]
        finally:
            db.close()
        self.cat = json.loads(self.meta["catalogue"])
        self.anchor = date.fromisoformat(self.meta["anchor"])
        self.horizon_end = date.fromisoformat(self.meta["horizon_end"])
        self.params = json.loads(self.meta["seed_params"])
        self.dense_end = self.anchor + timedelta(days=7 * self.params["dense_weeks"])
        self.providers = {p["id"]: p for p in self.cat["providers"]}
        self.specialties = {s["id"]: s for s in self.cat["specialties"]}
        self.types = {t["id"]: t for t in self.cat["appointment_types"]}
        self.locations = {x["id"]: x for x in self.cat["locations"]}
        self.plans = {p["id"] for p in self.cat["plans"]}
        self.site_hours = {(loc["id"], WEEKDAYS.index(h["weekday"])): [span(i) for i in h["intervals"]]
                           for loc in self.cat["locations"] for h in loc["hours"]}
        self.sched = defaultdict(list)  # (provider, weekday) -> [(site, start, end)]
        for p in self.cat["providers"]:
            for s in p["schedules"]:
                for d in s["days"]:
                    for i in d["intervals"]:
                        self.sched[(p["id"], WEEKDAYS.index(d["weekday"]))].append((s["location_id"], *span(i)))
        self.closed_all = {r["date"] for r in self.closure_rows if r["location_id"] is None}
        self.closed_site = {(r["date"], r["location_id"]) for r in self.closure_rows if r["location_id"]}
        self.patients = {r["patient_id"]: json.loads(r["data"]) for r in self.patient_rows}
        self.appointments = [(r, json.loads(r["data"])) for r in self.appointment_rows]
        self.type_by_spec = {}  # (specialty, returning) -> type id, from the catalogue's own naming rule
        for spec in self.specialties:
            own = [t for t in self.types.values() if t["specialty_id"] == spec]
            for returning, requirement in ((False, "new_only"), (True, "existing_only")):
                mine = [t["id"] for t in own if t["new_patient_requirement"] == requirement]
                universal = "review" if returning else "first_visit"
                self.type_by_spec[(spec, returning)] = mine[0] if mine else universal

    def closed(self, day: str, site: str) -> bool:
        return day in self.closed_all or (day, site) in self.closed_site

    def open_cells(self, provider: str, day: date) -> tuple[str, list[int]] | None:
        """Site and 15-minute cell starts a provider can see patients in on a day."""
        entries = self.sched.get((provider, day.weekday()), [])
        if not entries:
            return None
        site, lo, hi = entries[0]
        if self.closed(day.isoformat(), site):
            return None
        hours = self.site_hours.get((site, day.weekday()), [])
        out = []
        for m in range(lo, hi, 15):
            if not any(a <= m and m + 15 <= b for a, b in hours):
                continue
            if any(self.absent(a, provider, day, m, m + 15) for a in self.absences):
                continue
            out.append(m)
        return site, out

    @staticmethod
    def absent(a: dict, provider: str, day: date, start: int, end: int) -> bool:
        if a["provider_id"] != provider or not (a["start_date"] <= day.isoformat() <= a["end_date"]):
            return False
        if a["start_time"] is None:
            return True
        return start < mins(a["end_time"]) and mins(a["start_time"]) < end

    def busy(self) -> dict:
        taken = defaultdict(set)
        for row, data in self.appointments:
            if row["status"] != "booked":
                continue
            start = datetime.fromisoformat(data["start_time"])
            m = start.hour * 60 + start.minute
            for k in range(0, data["duration_minutes"], 15):
                taken[(data["provider_id"], start.date())].add(m + k)
        return taken

    def free_cells(self, provider: str, day: date, taken: dict) -> list[int]:
        got = self.open_cells(provider, day)
        if not got:
            return []
        return [m for m in got[1] if m not in taken.get((provider, day), set())]


def days(a: date, b: date):
    while a <= b:
        yield a
        a += timedelta(days=1)


def check(path: Path) -> dict:
    errors: list[str] = []
    warnings: list[str] = []
    c = Clinic(Path(path))
    err = errors.append

    # schema and meta
    for table, cols in COLUMNS.items():
        if c.tables.get(table) != cols:
            err(f"table {table} has columns {c.tables.get(table)}, expected {cols}")
    for name in INDEXES - c.indexes:
        err(f"missing index {name}")
    for key in ("catalogue", "anchor", "horizon_end", "seed_params", "seeded_at"):
        if key not in c.meta:
            err(f"meta.{key} missing")
    for key in ("clinic_name", "restrictions", "providers", "specialties", "appointment_types", "locations", "plans", "plan_rules"):
        if key not in c.cat:
            err(f"catalogue.{key} missing")
    if "calendar" in c.cat or "patient_count" in c.cat:
        err("catalogue carries live parts (calendar/patient_count)")
    if any("leave" in p for p in c.cat["providers"]) or any("holders" in p for p in c.cat["plans"]):
        err("catalogue carries providers[].leave or plans[].holders")

    # closures and absences
    for r in c.closure_rows:
        if r["location_id"] not in (None, *c.locations):
            err(f"closure {r} has an unknown site")
    for a in c.absences:
        if a["provider_id"] not in c.providers or a["start_date"] > a["end_date"]:
            err(f"absence {a} is malformed")
        if (a["start_time"] is None) != (a["end_time"] is None) or (
                a["start_time"] and mins(a["start_time"]) >= mins(a["end_time"])):
            err(f"absence {a} has a bad time range")

    # patients
    seen_ids: set[str] = set()
    for row in c.patient_rows:
        p = c.patients[row["patient_id"]]
        pid = row["patient_id"]
        for key, kind in PATIENT_KEYS.items():
            if not isinstance(p.get(key), kind):
                err(f"{pid}: {key} is {p.get(key)!r}")
        if not isinstance(p.get("national_id"), str):
            continue
        if p["patient_id"] != pid or p["national_id"] != row["national_id"]:
            err(f"{pid}: columns differ from data")
        if not re.fullmatch(r"P\d{5}", pid):
            err(f"{pid}: bad patient id")
        nid = p["national_id"]
        if re.sub(r"[^0-9A-Za-z]", "", nid).upper() != nid or not id_valid(nid):
            err(f"{pid}: national id {nid} invalid")
        if nid in seen_ids:
            err(f"{pid}: national id {nid} duplicated")
        seen_ids.add(nid)
        if nid in R.FORBIDDEN_NATIONAL_IDS or p["phone"] in R.FORBIDDEN_PHONES:
            err(f"{pid}: forbidden identity on file ({nid} / {p['phone']})")
        full = " ".join((p["given_name"], p["first_surname"], p["second_surname"]))
        if full in R.FORBIDDEN_NAMES:
            err(f"{pid}: forbidden person {full}")
        if not all((p["given_name"], p["first_surname"], p["second_surname"])) or "-" in p["first_surname"] + p["second_surname"]:
            err(f"{pid}: incomplete or hyphenated name {full!r}")
        if not re.fullmatch(r"[6789]\d{8}", p["phone"]):
            err(f"{pid}: phone {p['phone']}")
        if p["sex"] not in ("F", "M") or p["insurer"] not in c.plans or p["source"] != "seed":
            err(f"{pid}: sex/insurer/source {p['sex']}/{p['insurer']}/{p['source']}")
        if not set(p["referrals"]) <= set(c.specialties) or not set(p["insurer_authorizations"]) <= set(c.specialties):
            err(f"{pid}: unknown specialty in referrals/authorizations")
        if p["email"] and not EMAIL.match(p["email"]):
            err(f"{pid}: email {p['email']} is not on a reserved domain")
        try:
            if date.fromisoformat(p["date_of_birth"]) > c.anchor:
                err(f"{pid}: born after the anchor")
        except ValueError:
            err(f"{pid}: date_of_birth {p['date_of_birth']}")

    # appointments
    by_patient = defaultdict(list)
    by_provider = defaultdict(list)
    seeded_cutoff = datetime(c.anchor.year, c.anchor.month, c.anchor.day, 23, 59, tzinfo=MADRID).timestamp()
    rows = []
    for row, a in c.appointments:
        aid = row["appointment_id"]
        bad = [k for k, kind in APPOINTMENT_KEYS.items() if not isinstance(a.get(k), kind)]
        if bad or "call_id" not in a:
            err(f"{aid}: bad keys {bad}")
            continue
        if row["status"] not in ("booked", "cancelled"):
            err(f"{aid}: status {row['status']}")
        if not re.fullmatch(r"A\d{6}", aid) or a["appointment_id"] != aid or a["patient_id"] != row["patient_id"]:
            err(f"{aid}: id/patient columns differ from data")
        if (row["provider_id"], row["start_date"], row["start_time"]) != (a["provider_id"], a["start_time"][:10], a["start_time"]):
            err(f"{aid}: denormalised columns differ")
        if a["call_id"] is not None or a["source"] != "seed":
            err(f"{aid}: call_id/source")
        p = c.patients.get(a["patient_id"])
        prov = c.providers.get(a["provider_id"])
        atype = c.types.get(a["appointment_type_id"])
        if not p or not prov or not atype:
            err(f"{aid}: unknown patient/provider/type")
            continue
        start = datetime.fromisoformat(a["start_time"])
        rebuilt = datetime(start.year, start.month, start.day, start.hour, start.minute, tzinfo=MADRID).isoformat(timespec="seconds")
        if rebuilt != a["start_time"] or start.second or start.minute % 15:
            err(f"{aid}: start_time {a['start_time']} is not Madrid wall time on the grid")
        day, m, dur = start.date(), start.hour * 60 + start.minute, a["duration_minutes"]
        spec, site = a["specialty_id"], a["location_id"]
        if prov["name"] != a["provider_name"] or prov["specialty_id"] != spec:
            err(f"{aid}: provider name/specialty mismatch")
        if dur != atype["duration_minutes"]:
            err(f"{aid}: duration {dur} != {atype['duration_minutes']}")
        if a["appointment_type_id"] not in (c.type_by_spec[(spec, False)], c.type_by_spec[(spec, True)]):
            err(f"{aid}: type {a['appointment_type_id']} not offered in {spec}")
        if a["patient_name"] != " ".join((p["given_name"], p["first_surname"], p["second_surname"])).strip():
            err(f"{aid}: patient_name")
        if day > c.horizon_end:
            err(f"{aid}: after horizon_end")
        if not any(s == site and lo <= m and m + dur <= hi for s, lo, hi in c.sched.get((a["provider_id"], day.weekday()), [])):
            err(f"{aid}: outside {a['provider_id']}'s schedule at {site} ({a['start_time']})")
        if not any(lo <= m and m + dur <= hi for lo, hi in c.site_hours.get((site, day.weekday()), [])):
            err(f"{aid}: outside {site} opening hours")
        if c.closed(day.isoformat(), site):
            err(f"{aid}: on a closure day ({day} {site})")
        if any(Clinic.absent(x, a["provider_id"], day, m, m + dur) for x in c.absences):
            err(f"{aid}: provider absent ({a['start_time']})")
        if not (a["updated_at"] < start.timestamp() and a["updated_at"] <= seeded_cutoff):
            err(f"{aid}: updated_at {a['updated_at']} not before the appointment and the seed day")
        past = day < c.anchor
        attendance = a.get("attendance")
        if row["status"] == "cancelled":
            if attendance is not None:
                err(f"{aid}: cancelled row with attendance")
            continue
        if past and attendance not in ("attended", "no_show"):
            err(f"{aid}: past booked row without attendance")
        if not past and attendance is not None:
            err(f"{aid}: attendance on a row that has not happened")
        # the booking rules the engine applies
        sp = c.specialties[spec]
        age = months_old(date.fromisoformat(p["date_of_birth"]), day)
        if age < sp["min_age_months"] or (sp["max_age_months"] is not None and age > sp["max_age_months"]):
            err(f"{aid}: {a['patient_id']} is {age} months old for {spec}")
        if sp["referral_required"] and spec not in p["referrals"]:
            err(f"{aid}: {a['patient_id']} has no {spec} referral")
        policy = a["policy_id"]
        if a["payable_with"] != [policy] or policy not in (p["insurer"], "privado"):
            err(f"{aid}: policy {policy} / payable_with {a['payable_with']} for insurer {p['insurer']}")
        if (policy in {x["id"] for x in prov["refused_insurers"]} or policy in {x["id"] for x in sp["not_covered_by"]}
                or policy in {x["id"] for x in c.locations[site]["not_covered_by"]}):
            err(f"{aid}: {policy} cannot pay {spec} with {a['provider_id']} at {site}")
        if spec in c.cat["plan_rules"].get(policy, {}).get("authorization_required", []) and spec not in p["insurer_authorizations"]:
            err(f"{aid}: {policy} needs an insurer authorisation for {spec}")
        rows.append((a, row, start, m, dur))
        by_patient[a["patient_id"]].append((start, start + timedelta(minutes=dur), a))
        by_provider[a["provider_id"]].append((start, start + timedelta(minutes=dur), aid))

    for key, spans in list(by_patient.items()) + list(by_provider.items()):
        spans.sort(key=lambda x: x[0])
        for (_, e1, x1), (s2, _, x2) in pairwise(spans):
            if s2 < e1:
                err(f"overlap for {key}: {x1 if isinstance(x1, str) else x1['appointment_id']} and "
                    f"{x2 if isinstance(x2, str) else x2['appointment_id']}")

    # history: types follow has_visited_before, the flag follows attended visits, allowances hold
    for pid, p in c.patients.items():
        mine = sorted(by_patient.get(pid, []), key=lambda x: x[0])
        attended = [s for s, _, a in mine if a.get("attendance") == "attended"]
        if p["has_visited_before"] != bool(attended):
            err(f"{pid}: has_visited_before={p['has_visited_before']} but {len(attended)} attended visits")
        for s, _, a in mine:
            before = any(t < s for t in attended)
            need = c.types[a["appointment_type_id"]]["new_patient_requirement"]
            if (need == "new_only" and before) or (need == "existing_only" and not before):
                err(f"{a['appointment_id']}: {a['appointment_type_id']} for {pid} (seen before: {before})")
        per_year = Counter((a["specialty_id"], s.year) for s, _, a in mine)
        for (spec, year), n in per_year.items():
            allowance = c.cat["plan_rules"].get(p["insurer"], {}).get("annual_allowance", {}).get(spec)
            paid_by_plan = any(a["policy_id"] == p["insurer"] and a["specialty_id"] == spec for _, _, a in mine)
            if allowance is not None and paid_by_plan and p["allowance_used"].get(spec, 0) + n > allowance:
                err(f"{pid}: {spec} allowance exceeded in {year}")

    guarantees(c, errors, warnings)
    return {"errors": errors, "warnings": warnings}


def guarantees(c: Clinic, errors: list, warnings: list) -> None:
    err = errors.append
    by_nid = {p["national_id"]: p for p in c.patients.values()}
    for pid, want in R.DEMO_PERSONAS.items():
        got = c.patients.get(pid, {})
        diff = {k: got.get(k) for k, v in want.items() if got.get(k) != v}
        if diff:
            err(f"demo persona {pid} differs: {diff}")
    amelia = by_nid.get(R.AMELIA_WILLIAMS["national_id"])
    if not amelia or amelia["phone"] != R.AMELIA_WILLIAMS["phone"] or amelia["given_name"] != "Amelia":
        err("Amelia Williams Williams (X8148593S / 607034486) is not on file")
    rosario = [p for p in c.patients.values()
               if {"rosario", "sanz"} <= tokens(" ".join((p["given_name"], p["first_surname"], p["second_surname"])))]
    if len(rosario) != 4:
        err(f"'Rosario Sanz' matches {len(rosario)} patients, expected 4")

    # Ignacio: exactly one upcoming appointment, A001101, on the first workable Tuesday >= anchor+14
    spec = R.IGNACIO_APPOINTMENT
    upcoming = [(r, a) for r, a in c.appointments if a["patient_id"] == spec["patient_id"]
                and r["status"] == "booked" and a["start_time"][:10] >= c.anchor.isoformat()]
    day = c.anchor + timedelta(days=spec["min_days_ahead"])
    day += timedelta(days=(spec["weekday"] - day.weekday()) % 7)
    for _ in range(12):
        got = c.open_cells(spec["provider_id"], day)
        if got and got[0] == spec["location_id"] and mins(spec["time"]) in got[1]:
            break
        day += timedelta(days=7)
    hour, minute = (int(x) for x in spec["time"].split(":"))
    expected = datetime(day.year, day.month, day.day, hour, minute, tzinfo=MADRID).isoformat(timespec="seconds")
    ok = (len(upcoming) == 1 and upcoming[0][1]["appointment_id"] == spec["appointment_id"]
          and upcoming[0][1]["provider_id"] == spec["provider_id"] and upcoming[0][1]["location_id"] == spec["location_id"]
          and upcoming[0][1]["appointment_type_id"] == spec["appointment_type_id"]
          and upcoming[0][1]["start_time"] == expected and upcoming[0][1]["policy_id"] == spec["policy_id"])
    if not ok:
        err(f"Ignacio should have exactly {spec['appointment_id']} at {expected}; has {[a['appointment_id'] + ' ' + a['start_time'] for _, a in upcoming]}")

    taken = c.busy()
    d1 = c.anchor + timedelta(days=1)

    def gaps(providers, first, last, n):
        out: list[tuple] = []
        for day in days(first, last):
            for prov in providers:
                free = set(c.free_cells(prov, day, taken))
                out += [(prov, day, m) for m in sorted(free) if all(m + 15 * k in free for k in range(n))]
        return out

    by_spec = defaultdict(list)
    for pid, p in sorted(c.providers.items()):
        by_spec[p["specialty_id"]].append(pid)
    if not gaps(by_spec["general_practice"], d1, c.anchor + timedelta(days=7), 1):
        err("no free General Practice slot in the first 7 bookable days")
    for spec_id, provs in by_spec.items():
        # both the returning and the new-patient type (dermatology: reviews only, see below)
        for returning in (True,) if spec_id == "dermatology" else (True, False):
            type_id = c.type_by_spec[(spec_id, returning)]
            if gaps(provs, d1, c.anchor + timedelta(days=14), c.types[type_id]["duration_minutes"] // 15):
                continue
            away = [a for a in c.absences if a["provider_id"] in provs and a["start_date"] <= (c.anchor + timedelta(days=14)).isoformat()
                    and a["end_date"] >= d1.isoformat()]
            (warnings if away else errors).append(f"no free {type_id} slot in {spec_id} within 14 days"
                                                  + (" (absence explains it)" if away else ""))
    derm = by_spec["dermatology"]
    if len(gaps(derm, d1, c.anchor + timedelta(days=14), 1)) < 2:
        err("dermatology has fewer than 2 free review slots within 14 days")
    if not gaps(derm, d1, c.anchor + timedelta(days=21), 2):
        err("dermatology has no free 30-minute gap within 21 days")
    full = []
    for prov in c.providers:
        open_n = sum(len((c.open_cells(prov, d) or (None, []))[1]) for d in days(d1, c.dense_end))
        free_n = sum(len(c.free_cells(prov, d, taken)) for d in days(d1, c.dense_end))
        if open_n and not free_n:
            full.append(prov)
    if not full:
        err("no provider is fully booked for the dense window")


# ── Stats report ─────────────────────────────────────────────────────────────────────────────


def stats(path: Path) -> str:
    c = Clinic(Path(path))
    taken = c.busy()
    out: list[str] = []
    add = out.append
    patients = list(c.patients.values())
    n = len(patients)

    def pct(k, total):
        return f"{100 * k / total:.0f}%" if total else "-"

    def band(p):
        age = months_old(date.fromisoformat(p["date_of_birth"]), c.anchor) // 12
        return next(label for limit, label in ((13, "0-13"), (17, "14-17"), (44, "18-44"), (64, "45-64"),
                                               (79, "65-79"), (200, "80+")) if age <= limit)

    booked = [(r, a) for r, a in c.appointments if r["status"] == "booked"]
    usual = {}
    for pid in c.patients:
        sites = Counter(a["location_id"] for r, a in booked if a["patient_id"] == pid)
        usual[pid] = sites.most_common(1)[0][0] if sites else "none"
    add(f"Seed anchor {c.anchor} · horizon_end {c.horizon_end} · {n} patients · params {c.params}")
    add("\nPatients by age band: " + ", ".join(f"{k} {v} ({pct(v, n)})" for k, v in sorted(Counter(map(band, patients)).items())))
    add("Patients by insurer:  " + ", ".join(f"{k} {v}" for k, v in Counter(p["insurer"] for p in patients).most_common()))
    add("Patients by usual site (most frequent site of their rows): " + ", ".join(f"{k} {v}" for k, v in Counter(usual.values()).most_common()))
    add(f"has_visited_before {pct(sum(p['has_visited_before'] for p in patients), n)} · referral held {pct(sum(bool(p['referrals']) for p in patients), n)}"
        f" · email {pct(sum(bool(p['email']) for p in patients), n)} · NIE {pct(sum(p['national_id'][0] in 'XYZ' for p in patients), n)}"
        f" · female {pct(sum(p['sex'] == 'F' for p in patients), n)}")
    past = [a for r, a in c.appointments if a["start_time"][:10] < c.anchor.isoformat()]
    status = Counter("cancelled" if r["status"] == "cancelled" else a.get("attendance", "upcoming") for r, a in c.appointments
                     if a["start_time"][:10] < c.anchor.isoformat())
    future = Counter(r["status"] for r, a in c.appointments if a["start_time"][:10] >= c.anchor.isoformat())
    add(f"\nAppointments: {len(c.appointments)} rows. Past {len(past)}: " + ", ".join(f"{k} {v} ({pct(v, len(past))})" for k, v in status.most_common())
        + ". From the anchor on: " + ", ".join(f"{k} {v}" for k, v in future.most_common()))
    upcoming = Counter(a["patient_id"] for r, a in booked if a["start_time"][:10] > c.anchor.isoformat())
    dist = Counter(min(upcoming.get(pid, 0), 9) for pid in c.patients)
    add("Upcoming rows per patient: " + ", ".join(f"{'9+' if k == 9 else k}: {v} ({pct(v, n)})" for k, v in sorted(dist.items()))
        + f" · max {max(upcoming.values(), default=0)}")

    weeks = c.params["dense_weeks"] + c.params["tail_weeks"]
    add("\nOccupancy per provider per week (booked cells / open cells; weeks count from the day after the anchor):")
    add("       " + " ".join(f"  W{w + 1:<3}" for w in range(weeks)))
    spec_week: dict[tuple, list[int]] = defaultdict(lambda: [0, 0])
    for prov in sorted(c.providers):
        cellsw = []
        for w in range(weeks):
            open_n = free_n = 0
            for d in days(c.anchor + timedelta(days=1 + 7 * w), c.anchor + timedelta(days=7 * (w + 1))):
                open_n += len((c.open_cells(prov, d) or (None, []))[1])
                free_n += len(c.free_cells(prov, d, taken))
            spec_week[(c.providers[prov]["specialty_id"], w)][0] += open_n - free_n
            spec_week[(c.providers[prov]["specialty_id"], w)][1] += open_n
            cellsw.append(f"{pct(open_n - free_n, open_n):>6}" if open_n else "     -")
        add(f"{prov}  " + " ".join(cellsw) + f"   {c.providers[prov]['specialty_id']}")
    add("\nOccupancy per specialty, weeks 1-4:")
    for spec in c.specialties:
        add(f"  {spec:<17}" + " ".join(f"{pct(*spec_week[(spec, w)]):>6}" for w in range(min(4, weeks))))
    add("\nFree 15-min cells per specialty (first 7 / 14 bookable days):")
    for spec in c.specialties:
        provs = [p for p in c.providers if c.providers[p]["specialty_id"] == spec]
        f7 = sum(len(c.free_cells(p, d, taken)) for p in provs for d in days(c.anchor + timedelta(days=1), c.anchor + timedelta(days=7)))
        f14 = sum(len(c.free_cells(p, d, taken)) for p in provs for d in days(c.anchor + timedelta(days=1), c.anchor + timedelta(days=14)))
        add(f"  {spec:<17} {f7:>4} / {f14:>4}")
    add("\nAbsences from a week before the anchor to horizon_end:")
    for a in c.absences:
        if a["end_date"] >= (c.anchor - timedelta(days=7)).isoformat() and a["start_date"] <= c.horizon_end.isoformat():
            times = f" {a['start_time']}-{a['end_time']}" if a["start_time"] else ""
            add(f"  {a['provider_id']} {a['start_date']} to {a['end_date']}{times}: {a['reason']}")
    add("Closures in [anchor, horizon_end]: " + ", ".join(
        f"{r['date']} {r['location_id'] or 'all'} ({r['name']})" for r in sorted(c.closure_rows, key=lambda r: r["date"])
        if c.anchor.isoformat() <= r["date"] <= c.horizon_end.isoformat()))
    return "\n".join(out)
