"""Persistent clinic calendar view consumed by the ROSARIO console."""

import json
import sqlite3
from typing import Any

from fastapi import APIRouter

from app import config

router = APIRouter(prefix="/api", tags=["calendar"])


@router.get("/calendar")
def calendar() -> dict[str, Any]:
    db = sqlite3.connect(config.DATABASE_PATH)
    db.row_factory = sqlite3.Row
    rows = db.execute(
        """
        SELECT a.*, p.given_name, p.first_surname, p.second_surname
        FROM appointments a JOIN patients p USING (patient_id)
        WHERE a.status='booked' ORDER BY a.start_time
        """
    ).fetchall()
    catalogue = json.loads(db.execute("SELECT payload FROM catalogue WHERE id=1").fetchone()[0])
    db.close()
    providers = {provider["id"]: provider["name"] for provider in catalogue["providers"]}
    locations = {location["id"]: location["name"] for location in catalogue["locations"]}
    return {
        "appointments": [
            {
                "appointment_id": row["appointment_id"],
                "patient_id": row["patient_id"],
                "patient_name": " ".join(
                    (row["given_name"], row["first_surname"], row["second_surname"])
                ),
                "provider_id": row["provider_id"],
                "provider_name": providers.get(row["provider_id"], row["provider_id"]),
                "location_id": row["location_id"],
                "location_name": locations.get(row["location_id"], row["location_id"]),
                "appointment_type_id": row["appointment_type_id"],
                "start_time": row["start_time"],
                "duration_minutes": row["duration_minutes"],
                "status": row["status"],
            }
            for row in rows
        ]
    }
