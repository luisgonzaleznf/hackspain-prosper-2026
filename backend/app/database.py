"""Writable SQLite replacement for the retired Prosper clinic and submission APIs."""

from __future__ import annotations

import json
import re
import sqlite3
import time
import unicodedata
import uuid
from datetime import datetime
from typing import Any

from app import config


def _connect() -> sqlite3.Connection:
    db = sqlite3.connect(config.DATABASE_PATH, timeout=10)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys=ON")
    db.execute("PRAGMA journal_mode=WAL")
    return db


def _json(row: sqlite3.Row, key: str = "payload") -> dict[str, Any]:
    return json.loads(row[key])


def _fold(value: str) -> str:
    return unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode().casefold()


def _phone(value: str) -> str:
    digits = re.sub(r"\D", "", value)
    if digits.startswith("0034"):
        digits = digits[4:]
    elif digits.startswith("34") and len(digits) > 9:
        digits = digits[2:]
    return digits[-9:]


def catalogue() -> dict[str, Any]:
    with _connect() as db:
        row = db.execute("SELECT payload FROM catalogue WHERE id=1").fetchone()
    if row is None:
        raise RuntimeError(f"Clinic database is not initialized: {config.DATABASE_PATH}")
    return _json(row)


def directory(**filters: str) -> list[dict[str, Any]]:
    with _connect() as db:
        rows = db.execute("SELECT payload FROM patients ORDER BY patient_id").fetchall()
    patients = [_json(row) for row in rows]
    name = filters.get("name")
    if name:
        words = set(re.findall(r"[a-z]+", _fold(name)))
        patients = [
            patient for patient in patients
            if words & set(re.findall(r"[a-z]+", _fold(" ".join((patient["given_name"], patient["first_surname"], patient["second_surname"])))))
        ]
    for field in ("national_id", "date_of_birth"):
        value = filters.get(field)
        if value:
            expected = re.sub(r"\W", "", value).upper() if field == "national_id" else value
            patients = [patient for patient in patients if (re.sub(r"\W", "", patient[field]).upper() if field == "national_id" else patient[field]) == expected]
    if filters.get("phone"):
        patients = [patient for patient in patients if _phone(patient["phone"]) == _phone(filters["phone"])]
    matched = [key for key in ("name", "national_id", "phone", "date_of_birth") if filters.get(key)]
    return [{**patient, "insurer": patient["insurer"]["id"] if isinstance(patient.get("insurer"), dict) else patient.get("insurer"), "matched_fields": matched} for patient in patients[:100]]


def patient_appointments(patient_id: str, when: str = "upcoming") -> list[dict[str, Any]]:
    now = datetime.now(config.TZ).isoformat()
    condition = "AND start_time >= ?" if when == "upcoming" else "AND start_time < ?" if when == "past" else ""
    params: tuple[Any, ...] = (patient_id, now) if condition else (patient_id,)
    with _connect() as db:
        rows = db.execute(
            f"SELECT * FROM appointments WHERE patient_id=? AND status='booked' {condition} ORDER BY start_time",
            params,
        ).fetchall()
    return [
        {
            **_json(row),
            "appointment_id": row["appointment_id"],
            "patient_id": row["patient_id"],
            "provider_id": row["provider_id"],
            "location_id": row["location_id"],
            "appointment_type_id": row["appointment_type_id"],
            "start_time": row["start_time"],
            "duration_minutes": row["duration_minutes"],
        }
        for row in rows
    ]


def availability(
    date_from: str,
    date_to: str,
    *,
    specialty_id: str | None = None,
    provider_id: str | None = None,
    location_id: str | None = None,
    patient_id: str | None = None,
    insurers: list[str] | None = None,
) -> dict[str, Any]:
    cat = catalogue()
    if not patient_id:
        return {"providers": [], "appointment_type": cat["appointment_types"][0], "slots": [], "blocked": []}
    if not specialty_id and provider_id:
        specialty_id = next((provider["specialty_id"] for provider in cat["providers"] if provider["id"] == provider_id), None)
    if not specialty_id:
        raise ValueError("specialty_id or provider_id is required")
    with _connect() as db:
        row = db.execute("SELECT payload FROM availability WHERE patient_id=? AND specialty_id=?", (patient_id, specialty_id)).fetchone()
        booked = {
            (item["provider_id"], item["location_id"], item["start_time"])
            for item in db.execute("SELECT provider_id, location_id, start_time FROM appointments WHERE status='booked'")
        }
    if row is None:
        raise ValueError("patient is not in the imported clinic subset")
    payload = _json(row)
    slots = []
    plans = set(insurers or [])
    for slot in payload["slots"]:
        if not date_from <= slot["start_time"][:10] <= date_to:
            continue
        if provider_id and slot["provider_id"] != provider_id:
            continue
        if location_id and slot["location_id"] != location_id:
            continue
        if (slot["provider_id"], slot["location_id"], slot["start_time"]) in booked:
            continue
        if plans and not plans.intersection(slot.get("payable_with", [])):
            continue
        slots.append(slot)
    return {**payload, "slots": slots}


def open_call(call_id: str, stream_sid: str, from_number: str | None, started_at: float) -> None:
    with _connect() as db:
        db.execute(
            "INSERT OR REPLACE INTO calls VALUES (?, ?, NULL, ?, ?, 'in progress')",
            (call_id, started_at, from_number, stream_sid),
        )
        db.commit()


def close_call(call_id: str) -> None:
    with _connect() as db:
        db.execute("UPDATE calls SET ended_at=?, status='completed' WHERE call_id=?", (time.time(), call_id))
        db.commit()


def apply_action(call_id: str, action: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    now = time.time()
    verb = action["action"]
    with _connect() as db:
        call = db.execute("SELECT call_id FROM calls WHERE call_id=?", (call_id,)).fetchone()
        if call is None:
            return 404, {"detail": "unknown call_id"}
        if verb == "BOOK":
            appointment_id = "A" + uuid.uuid4().hex[:10].upper()
            duration = next((item["duration_minutes"] for item in catalogue()["appointment_types"] if item["id"] == action["appointment_type_id"]), 15)
            payload = {
                "appointment_id": appointment_id, "patient_id": action["patient_id"],
                "provider_id": action["provider_id"], "location_id": action["location_id"],
                "appointment_type_id": action["appointment_type_id"], "start_time": action["slot"],
                "duration_minutes": duration,
            }
            db.execute(
                "INSERT INTO appointments VALUES (?, ?, ?, ?, ?, ?, ?, 'booked', ?)",
                (appointment_id, action["patient_id"], action["provider_id"], action["location_id"], action["appointment_type_id"], action["slot"], duration, json.dumps(payload, ensure_ascii=False)),
            )
        elif verb == "RESCHEDULE":
            db.execute(
                "UPDATE appointments SET provider_id=?, location_id=?, start_time=?, payload=json_set(payload, '$.provider_id', ?, '$.location_id', ?, '$.start_time', ?) WHERE appointment_id=? AND status='booked'",
                (action["provider_id"], action["location_id"], action["slot"], action["provider_id"], action["location_id"], action["slot"], action["appointment_id"]),
            )
        elif verb == "CANCEL":
            db.execute("UPDATE appointments SET status='cancelled' WHERE appointment_id=?", (action["appointment_id"],))
        elif verb == "REGISTER":
            next_id = db.execute("SELECT COALESCE(MAX(CAST(SUBSTR(patient_id, 2) AS INTEGER)), 0) + 1 FROM patients").fetchone()[0]
            patient_id = f"P{next_id:05d}"
            payload = {
                "patient_id": patient_id, **{key: action[key] for key in ("given_name", "first_surname", "second_surname", "national_id", "date_of_birth", "phone")},
                "sex": "", "has_visited_before": False, "insurer": {"id": action["insurer"], "name": action["insurer"]},
                "secondary_insurer": None, "referrals": [], "note": "Registered by ROSARIO.", "matched_fields": [], "appointments": [],
            }
            db.execute(
                "INSERT INTO patients VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (patient_id, action["given_name"], action["first_surname"], action["second_surname"], action["national_id"], action["date_of_birth"], action["phone"], action["insurer"], json.dumps(payload, ensure_ascii=False)),
            )
        db.execute("INSERT INTO call_actions (call_id, action, payload, created_at) VALUES (?, ?, ?, ?)", (call_id, verb, json.dumps(action, ensure_ascii=False), now))
        db.commit()
        actions = [json.loads(row[0]) for row in db.execute("SELECT payload FROM call_actions WHERE call_id=? ORDER BY id", (call_id,))]
    return 200, {"call_id": call_id, "received_at": datetime.now(config.TZ).isoformat(), "record": {"actions": actions}}
