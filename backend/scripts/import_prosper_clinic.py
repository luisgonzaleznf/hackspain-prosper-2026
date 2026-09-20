"""Import a bounded, exact snapshot from the retired Prosper challenge APIs into SQLite.

Dashboard credentials are used only for export and are never stored. The resulting database
contains the first N official patient charts plus their exact agent-API availability responses.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sqlite3
from pathlib import Path
from typing import Any

import httpx
from dotenv import find_dotenv, load_dotenv

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB = ROOT / "data" / "clinic.sqlite3"
BASE_URL = "https://hackspain.getprosperapp.com"
SPECIALTIES = (
    "general_practice",
    "paediatrics",
    "dermatology",
    "orthopaedics",
    "gynaecology",
    "physiotherapy",
)


def _schema(db: sqlite3.Connection) -> None:
    db.executescript(
        """
        PRAGMA journal_mode=WAL;
        PRAGMA foreign_keys=ON;
        CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS catalogue (id INTEGER PRIMARY KEY CHECK (id = 1), payload TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS patients (
            patient_id TEXT PRIMARY KEY,
            given_name TEXT NOT NULL,
            first_surname TEXT NOT NULL,
            second_surname TEXT NOT NULL,
            national_id TEXT NOT NULL UNIQUE,
            date_of_birth TEXT NOT NULL,
            phone TEXT NOT NULL,
            insurer_id TEXT NOT NULL,
            payload TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS appointments (
            appointment_id TEXT PRIMARY KEY,
            patient_id TEXT NOT NULL REFERENCES patients(patient_id),
            provider_id TEXT NOT NULL,
            location_id TEXT NOT NULL,
            appointment_type_id TEXT,
            start_time TEXT NOT NULL,
            duration_minutes INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT 'booked',
            payload TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS availability (
            patient_id TEXT NOT NULL REFERENCES patients(patient_id),
            specialty_id TEXT NOT NULL,
            payload TEXT NOT NULL,
            PRIMARY KEY (patient_id, specialty_id)
        );
        CREATE TABLE IF NOT EXISTS calls (
            call_id TEXT PRIMARY KEY,
            started_at REAL NOT NULL,
            ended_at REAL,
            from_number TEXT,
            stream_sid TEXT,
            status TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS call_actions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            call_id TEXT NOT NULL REFERENCES calls(call_id),
            action TEXT NOT NULL,
            payload TEXT NOT NULL,
            created_at REAL NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_patients_phone ON patients(phone);
        CREATE INDEX IF NOT EXISTS idx_appointments_patient ON appointments(patient_id, start_time);
        """
    )


async def _get(client: httpx.AsyncClient, path: str, **kwargs: Any) -> dict[str, Any]:
    response = await client.get(path, **kwargs)
    response.raise_for_status()
    return response.json()


async def export(args: argparse.Namespace) -> None:
    date_windows = (("2026-09-07", "2026-09-20"), ("2026-09-21", "2026-10-04"), ("2026-10-05", "2026-10-16"))
    load_dotenv(find_dotenv(usecwd=True))
    api_key = os.environ["PLATFORM_API_KEY"]
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=45) as dashboard:
        login = await dashboard.post(
            "/leaderboard/api/session",
            json={"email": args.email, "password": args.password},
        )
        login.raise_for_status()
        catalogue = await _get(dashboard, "/leaderboard/api/clinic")
        page = await _get(
            dashboard,
            "/leaderboard/api/clinic/patients",
            params={"offset": args.offset, "limit": args.limit},
        )
        patients = await asyncio.gather(
            *(_get(dashboard, f"/leaderboard/api/clinic/patients/{row['patient_id']}") for row in page["patients"])
        )

    semaphore = asyncio.Semaphore(args.concurrency)
    async with httpx.AsyncClient(
        base_url=BASE_URL,
        headers={"X-Api-Key": api_key},
        timeout=45,
    ) as agent:
        async def availability(patient_id: str, specialty_id: str) -> tuple[str, str, dict[str, Any]]:
            async with semaphore:
                parts = await asyncio.gather(
                    *(
                        _get(
                            agent,
                            "/api/v1/availability",
                            params={
                                "date_from": date_from,
                                "date_to": date_to,
                                "patient_id": patient_id,
                                "specialty_id": specialty_id,
                            },
                        )
                        for date_from, date_to in date_windows
                    )
                )
                payload = parts[0]
                payload["slots"] = [slot for part in parts for slot in part["slots"]]
                payload["blocked"] = list(
                    {
                        json.dumps(blocked, sort_keys=True): blocked
                        for part in parts
                        for blocked in part["blocked"]
                    }.values()
                )
                return patient_id, specialty_id, payload

        rows = await asyncio.gather(
            *(
                availability(patient["patient_id"], specialty)
                for patient in patients
                for specialty in SPECIALTIES
            )
        )

    appointment_type_ids = {
        item["name"]: item["id"] for item in catalogue["appointment_types"]
    }
    args.database.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(args.database)
    _schema(db)
    with db:
        for table in ("availability", "appointments", "patients", "catalogue", "metadata"):
            db.execute(f"DELETE FROM {table}")
        db.execute(
            "INSERT INTO catalogue (id, payload) VALUES (1, ?)",
            (json.dumps(catalogue, ensure_ascii=False),),
        )
        for patient in patients:
            insurer = patient["insurer"]
            db.execute(
                "INSERT INTO patients VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    patient["patient_id"], patient["given_name"], patient["first_surname"],
                    patient["second_surname"], patient["national_id"], patient["date_of_birth"],
                    patient["phone"], insurer["id"] if isinstance(insurer, dict) else insurer,
                    json.dumps(patient, ensure_ascii=False),
                ),
            )
            for appointment in patient["appointments"]:
                appointment_type_id = appointment.get(
                    "appointment_type_id"
                ) or appointment_type_ids.get(appointment.get("appointment_type_name", ""))
                stored = {
                    **appointment,
                    "patient_id": patient["patient_id"],
                    "appointment_type_id": appointment_type_id,
                }
                db.execute(
                    "INSERT INTO appointments VALUES (?, ?, ?, ?, ?, ?, ?, 'booked', ?)",
                    (
                        appointment["appointment_id"], patient["patient_id"],
                        appointment["provider_id"], appointment["location_id"],
                        appointment_type_id, appointment["start_time"],
                        appointment["duration_minutes"], json.dumps(stored, ensure_ascii=False),
                    ),
                )
        db.executemany(
            "INSERT INTO availability VALUES (?, ?, ?)",
            (
                (patient_id, specialty_id, json.dumps(payload, ensure_ascii=False))
                for patient_id, specialty_id, payload in rows
            ),
        )
        db.executemany(
            "INSERT INTO metadata VALUES (?, ?)",
            (
                ("source", BASE_URL),
                ("patient_offset", str(args.offset)),
                ("patient_count", str(len(patients))),
                ("official_patient_total", str(page["total"])),
            ),
        )
    db.close()
    print(
        f"Imported {len(patients)} official patients and {len(rows)} availability responses "
        f"into {args.database}"
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--email", required=True)
    parser.add_argument("--password", required=True)
    parser.add_argument("--database", type=Path, default=DEFAULT_DB)
    parser.add_argument("--offset", type=int, default=0)
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--concurrency", type=int, default=12)
    asyncio.run(export(parser.parse_args()))


if __name__ == "__main__":
    main()
