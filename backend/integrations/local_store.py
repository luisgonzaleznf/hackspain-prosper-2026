"""The clinic database (SQLite): patients, the diary, closures, absences and the catalogue.

`make seed` fills it; calls write registrations and appointment changes to it as they happen.
"""

import json
import os
import sqlite3
import time
import unicodedata
import uuid
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Europe/Madrid")

SCHEMA = """
CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS closures (date TEXT NOT NULL, location_id TEXT, name TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS absences (
    id INTEGER PRIMARY KEY, provider_id TEXT NOT NULL,
    start_date TEXT NOT NULL, end_date TEXT NOT NULL,
    start_time TEXT, end_time TEXT,
    reason TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS patients (
    patient_id TEXT PRIMARY KEY, national_id TEXT NOT NULL UNIQUE,
    data TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS appointments (
    appointment_id TEXT PRIMARY KEY, patient_id TEXT NOT NULL,
    status TEXT NOT NULL, data TEXT NOT NULL,
    provider_id TEXT, start_date TEXT, start_time TEXT
);
CREATE TABLE IF NOT EXISTS changes (
    id INTEGER PRIMARY KEY, call_id TEXT NOT NULL,
    operation_key TEXT NOT NULL UNIQUE, created_at REAL NOT NULL,
    action TEXT NOT NULL, result TEXT NOT NULL
);
"""
INDEXES = """
CREATE INDEX IF NOT EXISTS appointments_provider_day ON appointments(provider_id, start_date);
CREATE INDEX IF NOT EXISTS appointments_day ON appointments(start_date);
CREATE INDEX IF NOT EXISTS appointments_patient ON appointments(patient_id);
"""
# Copies of data.* on each appointment row, so the diary can be read by provider and day.
DENORMALISED = ("provider_id", "start_date", "start_time")


def database_path() -> Path:
    return Path(
        os.getenv(
            "LOCAL_CLINIC_DB", str(Path(__file__).resolve().parents[1] / "data/clinic.sqlite3")
        )
    )


def normalized(value: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", value).lower() if c.isalnum())


def phone_digits(value: str) -> str:
    digits = "".join(c for c in value if c.isdigit())
    if digits.startswith("00"):
        digits = digits[2:]
    return digits[2:] if len(digits) == 11 and digits.startswith("34") else digits


def overlaps(a: dict, b: dict) -> bool:
    start_a, start_b = (datetime.fromisoformat(x["start_time"]) for x in (a, b))
    return start_a < start_b + timedelta(
        minutes=b["duration_minutes"]
    ) and start_b < start_a + timedelta(minutes=a["duration_minutes"])


def madrid_day(start_time: str) -> str:
    return datetime.fromisoformat(start_time).astimezone(TZ).date().isoformat()


def columns(record: dict) -> tuple[str | None, str | None, str | None]:
    """The denormalised (provider_id, start_date, start_time) of an appointment record."""
    start = record.get("start_time")
    return record.get("provider_id"), madrid_day(start) if start else None, start


def full_name(patient: dict) -> str:
    parts = (patient.get(k) or "" for k in ("given_name", "first_surname", "second_surname"))
    return " ".join(part for part in parts if part)


class LocalStore:
    def __init__(self, path: Path | None = None):
        self.path = path or database_path()

    @contextmanager
    def connect(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        try:
            db.executescript(SCHEMA)
            self._migrate(db)
            db.executescript(INDEXES)
            with db:
                yield db
        finally:
            db.close()

    @staticmethod
    def _migrate(db: sqlite3.Connection) -> None:
        """A database from before the denormalised columns gets them, filled from the JSON."""
        have = {row[1] for row in db.execute("PRAGMA table_info(appointments)")}
        missing = [c for c in DENORMALISED if c not in have]
        if not missing:
            return
        with db:
            for column in missing:
                db.execute(f"ALTER TABLE appointments ADD COLUMN {column} TEXT")
            for row in db.execute("SELECT appointment_id, data FROM appointments").fetchall():
                db.execute(
                    "UPDATE appointments SET provider_id=?, start_date=?, start_time=? "
                    "WHERE appointment_id=?",
                    (*columns(json.loads(row["data"])), row["appointment_id"]),
                )

    # ── reads ───────────────────────────────────────────────────────

    def meta(self) -> dict[str, str]:
        with self.connect() as db:
            return {row["key"]: row["value"] for row in db.execute("SELECT key, value FROM meta")}

    def patients(self) -> list[dict]:
        with self.connect() as db:
            return [json.loads(row[0]) for row in db.execute("SELECT data FROM patients")]

    def patient(self, patient_id: str) -> dict | None:
        with self.connect() as db:
            row = db.execute(
                "SELECT data FROM patients WHERE patient_id=?", (patient_id,)
            ).fetchone()
        return json.loads(row[0]) if row else None

    def appointments(
        self,
        patient_id: str | None = None,
        include_cancelled=False,
        *,
        date_from: str | None = None,
        date_to: str | None = None,
    ) -> list[dict]:
        """Diary rows, earliest first. Madrid days `date_from`..`date_to` (inclusive) narrow it."""
        where, params = [], []
        if not include_cancelled:
            where.append("status='booked'")
        if patient_id is not None:
            where.append("patient_id=?")
            params.append(patient_id)
        if date_from:
            where.append("start_date>=?")
            params.append(date_from)
        if date_to:
            where.append("start_date<=?")
            params.append(date_to)
        sql = "SELECT data, status FROM appointments"
        if where:
            sql += " WHERE " + " AND ".join(where)
        with self.connect() as db:
            rows = db.execute(sql, params).fetchall()
        return sorted(
            [{**json.loads(row["data"]), "status": row["status"]} for row in rows],
            key=lambda a: datetime.fromisoformat(a["start_time"]),
        )

    def existing_booking(self, call_id: str, action: dict) -> dict | None:
        for a in self.appointments(action["patient_id"]):
            if (
                a.get("call_id") == call_id
                and all(
                    a.get(key) == action.get(key)
                    for key in ("provider_id", "location_id", "policy_id")
                )
                and datetime.fromisoformat(a["start_time"])
                == datetime.fromisoformat(action["slot"])
            ):
                return {
                    "appointment_id": a["appointment_id"],
                    "patient_id": a["patient_id"],
                    "appointment": a,
                }
        return None

    # ── writes ──────────────────────────────────────────────────────

    def save(
        self,
        call_id: str,
        action: dict,
        *,
        patient: dict | None = None,
        appointment: dict | None = None,
        slot: dict | None = None,
        registration_id: str | None = None,
    ) -> dict:
        """Commit a checked write and its audit event atomically; retries are idempotent."""
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            verb = action["action"]
            if verb == "REGISTER":
                patient_id = registration_id or "LP" + uuid.uuid4().hex
                existing = db.execute(
                    "SELECT patient_id FROM patients WHERE national_id=?", (action["national_id"],)
                ).fetchone()
                if existing and existing[0] != patient_id:
                    raise ValueError(
                        "This DNI/NIE is already registered. Use find_patient to verify the existing profile."
                    )
                record = {k: v for k, v in action.items() if k != "action"}
                record.update(
                    patient_id=patient_id,
                    has_visited_before=False,
                    referrals=[],
                    note="",
                    sex="",
                    source="local",
                    insurer_authorizations=[],
                    allowance_used={},
                )
                previous = db.execute(
                    "SELECT data FROM patients WHERE patient_id=?", (patient_id,)
                ).fetchone()
                if previous and json.loads(previous[0]) == record:
                    return {"patient_id": patient_id, "patient": record}
                db.execute(
                    "INSERT INTO patients VALUES (?, ?, ?) ON CONFLICT(patient_id) DO UPDATE SET national_id=excluded.national_id, data=excluded.data",
                    (patient_id, record["national_id"], json.dumps(record)),
                )
                result = {"patient_id": patient_id, "patient": record}
            elif verb in {"BOOK", "RESCHEDULE", "CANCEL"}:
                if patient is None:
                    raise ValueError("Verify the patient before changing their calendar.")
                if verb == "BOOK":
                    previous = self.existing_booking(call_id, action)
                    if previous:
                        return previous
                appointment_id = (appointment or {}).get(
                    "appointment_id"
                ) or "LA" + uuid.uuid4().hex
                held = db.execute(
                    "SELECT data, status FROM appointments WHERE appointment_id=?",
                    (appointment_id,),
                ).fetchone()
                if held and verb != "BOOK":
                    assert appointment is not None
                    if held["status"] != "booked":
                        raise ValueError(
                            "This appointment is already cancelled. Refresh the diary."
                        )
                    if json.loads(held["data"])["start_time"] != appointment["start_time"]:
                        raise ValueError(
                            "This appointment changed during the call. Refresh the diary before changing it."
                        )
                if verb == "CANCEL":
                    # The status lives in its column; the call's copy may still say "booked".
                    record = {k: v for k, v in (appointment or {}).items() if k != "status"}
                    status = "cancelled"
                else:
                    if slot is None:
                        raise ValueError("Search for a fresh available slot before booking.")
                    record = {
                        **slot,
                        "appointment_id": appointment_id,
                        "patient_id": patient["patient_id"],
                        "policy_id": action["policy_id"],
                    }
                    _, day, _ = columns(record)
                    for row in db.execute(
                        "SELECT data FROM appointments WHERE status='booked' AND appointment_id != ? "
                        "AND start_date=? AND (provider_id=? OR patient_id=?)",
                        (appointment_id, day, record["provider_id"], record["patient_id"]),
                    ):
                        if overlaps(record, json.loads(row[0])):
                            raise ValueError(
                                "That time was just booked or overlaps another appointment. Search again and offer another time."
                            )
                    status = "booked"
                record.update(
                    patient_name=full_name(patient),
                    source="local",
                    call_id=call_id,
                    updated_at=time.time(),
                )
                db.execute(
                    "INSERT INTO appointments VALUES (?, ?, ?, ?, ?, ?, ?) ON CONFLICT(appointment_id) "
                    "DO UPDATE SET status=excluded.status, data=excluded.data, "
                    "provider_id=excluded.provider_id, start_date=excluded.start_date, "
                    "start_time=excluded.start_time",
                    (
                        appointment_id,
                        patient["patient_id"],
                        status,
                        json.dumps(record),
                        *columns(record),
                    ),
                )
                result = {
                    "appointment_id": appointment_id,
                    "patient_id": patient["patient_id"],
                    "appointment": {**record, "status": status},
                }
            else:
                raise ValueError("Unsupported local write")
            db.execute(
                "INSERT INTO changes(call_id,operation_key,created_at,action,result) VALUES (?,?,?,?,?)",
                (call_id, uuid.uuid4().hex, time.time(), json.dumps(action), json.dumps(result)),
            )
            return result
