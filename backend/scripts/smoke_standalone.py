"""Exercise the standalone call lifecycle and prove a booking mutates SQLite."""

from __future__ import annotations

import asyncio
import json
import shutil
import sqlite3
import tempfile
import uuid
from pathlib import Path

from app import clinic, config, database, prosper
from app.session import CallSession
from app.tools import call_tool


async def main() -> None:
    source = config.DATABASE_PATH
    with tempfile.TemporaryDirectory() as directory:
        database_path = Path(directory) / "clinic.sqlite3"
        calls_path = Path(directory) / "calls"
        shutil.copy2(source, database_path)
        config.DATABASE_PATH = database_path
        config.CALLS_DIR = calls_path
        clinic._catalogue = None
        await clinic.catalogue()

        call_id = "SM" + uuid.uuid4().hex
        database.open_call(call_id, "MZ" + uuid.uuid4().hex, "+34711330529", 1789812000.0)
        session = await CallSession.start(
            call_id=call_id,
            from_number="+34711330529",
        )
        patient = await call_tool(
            session,
            "find_patient",
            {"name": "Josefa Domínguez Navarro", "national_id": "48064716Y"},
        )
        assert patient["count"] == 1
        offered = await call_tool(
            session,
            "search_availability",
            {
                "date_from": "2026-09-20",
                "date_to": "2026-09-30",
                "specialty_id": "general_practice",
                "patient_id": "P00001",
            },
        )
        slot = offered["earliest_slots"][0]
        staged = await call_tool(
            session,
            "record_booking",
            {
                "patient_id": "P00001",
                "provider_id": slot["provider_id"],
                "location_id": slot["location_id"],
                "appointment_type_id": slot["appointment_type_id"],
                "slot": slot["slot"],
                "policy_id": "mapfre",
            },
        )
        assert staged["recorded"]["action"] == "BOOK"
        results = await session.finish()
        database.close_call(call_id)
        assert results[0]["status"] == 200

        with sqlite3.connect(database_path) as db:
            row = db.execute(
                "SELECT appointment_id, start_time FROM appointments WHERE patient_id='P00001' AND start_time=? AND status='booked'",
                (slot["slot"],),
            ).fetchone()
        assert row is not None
        events = [json.loads(line) for line in (calls_path / f"{call_id}.jsonl").read_text().splitlines()]
        assert any(event.get("kind") == "submit" and event.get("status") == 200 for event in events)
        print(json.dumps({"call_id": call_id, "appointment_id": row[0], "slot": row[1], "submit": 200}))
        prosper._client = None


if __name__ == "__main__":
    asyncio.run(main())
