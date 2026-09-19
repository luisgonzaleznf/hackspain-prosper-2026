"""Walk public case simple_booking-14a8720daa02 through the real tools, no voice, live API.

    uv run python scripts/smoke_tools.py

Josefa Domínguez Navarro (DNI 48064716Y) wants the earliest General Practice appointment.
The script plays the model: find_patient -> search_availability -> record_booking, then
finish() POSTs it with a made-up call_id. The platform answers 404 ("never called you on"),
which proves the route, the key and the body are right: a malformed body would be a 422.
"""

import asyncio
import json
import uuid
from datetime import timedelta

from app.session import CallSession
from app.tools import call_tool


def show(label: str, data: object) -> None:
    print(f"\n── {label}\n{json.dumps(data, indent=2, ensure_ascii=False)[:1500]}")


async def main() -> None:
    # call_id must be a UUID (Prosper validates the shape: anything else is a 422).
    session = await CallSession.start(call_id=str(uuid.uuid4()), from_number="+34711330529")
    show("caller id", [m["patient_id"] for m in session.caller_matches])

    found = await call_tool(
        session, "find_patient", {"name": "Josefa Dominguez", "national_id": "48064716-y"}
    )
    show("find_patient", found)
    patient = found["matches"][0]

    tomorrow = session.started_at.date() + timedelta(days=1)
    avail = await call_tool(
        session,
        "search_availability",
        {
            "specialty_id": "general_practice",
            "patient_id": patient["patient_id"],
            "date_from": tomorrow.isoformat(),
            "date_to": (tomorrow + timedelta(days=6)).isoformat(),
        },
    )
    show("search_availability", avail)
    slot = avail["earliest_slots"][0]

    rejected = await call_tool(
        session,
        "record_booking",
        {
            **{k: slot[k] for k in ("provider_id", "location_id", "appointment_type_id")},
            "patient_id": patient["patient_id"],
            "slot": "2026-09-19T07:00:00+02:00",
            "policy_id": patient["plan_on_file"],
        },
    )
    show("record_booking with an invented slot (must be refused)", rejected)
    assert "error" in rejected

    booked = await call_tool(
        session,
        "record_booking",
        {
            "patient_id": patient["patient_id"],
            "provider_id": slot["provider_id"],
            "location_id": slot["location_id"],
            "appointment_type_id": slot["appointment_type_id"],
            "slot": slot["slot"],
            "policy_id": patient["plan_on_file"],
        },
    )
    show("record_booking", booked)
    assert "error" not in booked

    results = await session.finish()
    show("finish() -> Prosper", results)
    status = results[0]["status"]
    assert status == 404, f"expected 404 for a call_id Prosper never placed, got {status}"
    print(
        f"\nOK: staged {booked['recorded']['action']} and Prosper accepted the body shape (404 = unknown call)."
    )
    print(
        "Public answer: BOOK P00001 PR01 centro review 2026-09-19T11:00:00+02:00 mapfre (Friday anchor)."
    )


if __name__ == "__main__":
    asyncio.run(main())
