"""SQLite patient profiles and appointment overlay. Never writes to Prosper."""

import json
import os
import sqlite3
import time
import unicodedata
import uuid
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path


def database_path() -> Path:
    return Path(
        os.getenv(
            "LOCAL_CLINIC_DB", str(Path(__file__).resolve().parents[1] / "data/clinic.sqlite3")
        )
    )


def normalized(value: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", value).lower() if c.isalnum())


def full_name(person: dict) -> str:
    return normalized(
        " ".join(
            str(person.get(k) or "") for k in ("given_name", "first_surname", "second_surname")
        )
    )


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


class LocalStore:
    def __init__(self, path: Path | None = None):
        self.path = path or database_path()

    @contextmanager
    def connect(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        try:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS patients (
                    patient_id TEXT PRIMARY KEY, national_id TEXT NOT NULL UNIQUE,
                    data TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS appointments (
                    appointment_id TEXT PRIMARY KEY, patient_id TEXT NOT NULL,
                    status TEXT NOT NULL, data TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS changes (
                    id INTEGER PRIMARY KEY, call_id TEXT NOT NULL,
                    operation_key TEXT NOT NULL UNIQUE, created_at REAL NOT NULL,
                    action TEXT NOT NULL, result TEXT NOT NULL
                );
            """)
            with db:
                yield db
        finally:
            db.close()

    def patients(self) -> list[dict]:
        with self.connect() as db:
            return [json.loads(row[0]) for row in db.execute("SELECT data FROM patients")]

    def patient(self, patient_id: str) -> dict | None:
        return next((p for p in self.patients() if p["patient_id"] == patient_id), None)

    def directory(self, **query) -> list[dict]:
        matches = []
        for patient in self.patients():
            name = " ".join(patient[k] for k in ("given_name", "first_surname", "second_surname"))
            # A name-only registration holds no DNI/NIE or date of birth (None): it never matches them.
            checks = {
                "name": all(
                    normalized(w) in normalized(name) for w in query.get("name", "").split()
                ),
                "national_id": bool(normalized(query.get("national_id", "")))
                and normalized(query.get("national_id", ""))
                == normalized(patient.get("national_id") or ""),
                "phone": bool(phone_digits(query.get("phone", "")))
                and phone_digits(query.get("phone", ""))
                == phone_digits(patient.get("phone") or ""),
                "date_of_birth": query.get("date_of_birth") == patient.get("date_of_birth"),
            }
            fields = [k for k, v in query.items() if v and k in checks]
            if fields and all(checks[k] for k in fields):
                matches.append({**patient, "matched_fields": fields, "match_score": 1.0})
        return matches

    def appointments(self, patient_id: str | None = None, include_cancelled=False) -> list[dict]:
        with self.connect() as db:
            rows = db.execute("SELECT data, status FROM appointments").fetchall()
        return sorted(
            [
                {**json.loads(row["data"]), "status": row["status"]}
                for row in rows
                if (include_cancelled or row["status"] == "booked")
                and (patient_id is None or json.loads(row["data"])["patient_id"] == patient_id)
            ],
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
                if action.get("national_id"):
                    existing = db.execute(
                        "SELECT patient_id FROM patients WHERE national_id=?",
                        (action["national_id"],),
                    ).fetchone()
                    if existing and existing[0] != patient_id:
                        raise ValueError(
                            "This DNI/NIE is already registered. Use find_patient to verify the existing profile."
                        )
                elif action.get("phone"):
                    # Without a DNI/NIE, the same name from the same phone is the same person.
                    rows = db.execute(
                        "SELECT data FROM patients WHERE patient_id != ?", (patient_id,)
                    )
                    if any(
                        full_name(other) == full_name(action)
                        and phone_digits(other.get("phone") or "") == phone_digits(action["phone"])
                        for other in (json.loads(row[0]) for row in rows)
                    ):
                        raise ValueError(
                            "This patient is already registered from this phone. Verify them with find_patient: full name and phone number."
                        )
                record = {k: v for k, v in action.items() if k != "action"}
                record.update(
                    patient_id=patient_id,
                    has_visited_before=False,
                    referrals=[],
                    note="",
                    sex="",
                    source="local",
                )
                previous = db.execute(
                    "SELECT data FROM patients WHERE patient_id=?", (patient_id,)
                ).fetchone()
                if previous and json.loads(previous[0]) == record:
                    return {"patient_id": patient_id, "patient": record}
                db.execute(
                    "INSERT INTO patients VALUES (?, ?, ?) ON CONFLICT(patient_id) DO UPDATE SET national_id=excluded.national_id, data=excluded.data",
                    # The column is NOT NULL UNIQUE in existing databases: a name-only
                    # registration keys it by its own patient_id until reception adds the DNI/NIE.
                    (patient_id, record.get("national_id") or patient_id, json.dumps(record)),
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
                    record = dict(appointment or {})
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
                    for row in db.execute(
                        "SELECT data FROM appointments WHERE status='booked' AND appointment_id != ?",
                        (appointment_id,),
                    ):
                        other = json.loads(row[0])
                        if (
                            other["provider_id"] == record["provider_id"]
                            or other["patient_id"] == record["patient_id"]
                        ) and overlaps(record, other):
                            raise ValueError(
                                "That time was just booked or overlaps another appointment. Search again and offer another time."
                            )
                    status = "booked"
                record.update(
                    patient_name=" ".join(
                        patient[k]
                        for k in ("given_name", "first_surname", "second_surname")
                        if patient.get(k)
                    ),
                    source="local",
                    call_id=call_id,
                    updated_at=time.time(),
                )
                db.execute(
                    "INSERT INTO appointments VALUES (?, ?, ?, ?) ON CONFLICT(appointment_id) DO UPDATE SET status=excluded.status, data=excluded.data",
                    (appointment_id, patient["patient_id"], status, json.dumps(record)),
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
