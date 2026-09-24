"""Send a demo email using live clinic lookups, without a call or scorer submit.

    uv run python -m scripts.smoke_appointment_email --to you@example.org
    uv run python -m scripts.smoke_appointment_email --to you@example.org --move

Use synthetic patient details only. Defaults to the published booking demo patient.
"""

import argparse
import asyncio
from datetime import date, datetime, timedelta
from pathlib import Path
from uuid import uuid4

from app import appointment_email, clinic, config
from app.session import CallSession
from app.tools import call_tool


async def smoke(address: str, national_id: str, move: bool) -> None:
    if not appointment_email.enabled():
        raise SystemExit(
            "Set APPOINTMENT_EMAILS_ENABLED=1, RESEND_API_KEY and RESEND_FROM_EMAIL "
            "in the ignored .env."
        )
    address = appointment_email.normalize_address(address)
    # Test recipients are real; keep the smoke trace out of committed call logs.
    config.CALLS_DIR = Path("logs/email-smoke")
    session = await CallSession.start(f"email-smoke-{uuid4()}", demo_mode=True)

    async def tool(name: str, args: dict) -> dict:
        result = await call_tool(session, name, args)
        if "error" in result:
            raise SystemExit(f"{name}: {result['error']}")
        return result

    await tool("find_patient", {"national_id": national_id})
    if len(session.patients) != 1:
        raise SystemExit("The synthetic identifier must match exactly one patient.")
    patient_id, patient = next(iter(session.patients.items()))
    tomorrow = session.started_at.date() + timedelta(days=1)
    search: dict = {
        "patient_id": patient_id,
        "date_from": tomorrow.isoformat(),
        "date_to": (tomorrow + timedelta(days=13)).isoformat(),
        "specialty_id": "general_practice",
    }
    appointment = None
    if move:
        await tool("list_appointments", {"patient_id": patient_id})
        if not session.appointments:
            raise SystemExit("No upcoming appointment. Use another synthetic --national-id.")
        appointment = min(session.appointments.values(), key=lambda item: item["start_time"])
        after = datetime.fromisoformat(appointment["start_time"])
        start = max(tomorrow, after.date())
        search = {
            "patient_id": patient_id,
            "provider_id": appointment["provider_id"],
            "location_id": appointment["location_id"],
            "after": appointment["start_time"],
            "date_from": start.isoformat(),
            "date_to": (start + timedelta(days=13)).isoformat(),
        }
    calendar = (clinic.cached() or {}).get("calendar", {})
    if calendar.get("ends"):
        end = date.fromisoformat(calendar["ends"])
        if date.fromisoformat(search["date_from"]) > end:
            raise SystemExit("No later date exists in the clinic's published calendar.")
        search["date_to"] = min(date.fromisoformat(search["date_to"]), end).isoformat()
    availability = await tool("search_availability", search)
    slots = availability["earliest_slots"]
    if not slots:
        raise SystemExit("No eligible slot was returned; nothing was recorded or emailed.")
    slot = slots[0]
    args = {key: slot[key] for key in ("provider_id", "location_id", "slot")}
    args["policy_id"] = patient["insurer"]
    if appointment:
        await tool("record_reschedule", args | {"appointment_id": appointment["appointment_id"]})
    else:
        await tool(
            "record_booking",
            args
            | {
                "patient_id": patient_id,
                "appointment_type_id": slot["appointment_type_id"],
            },
        )
    # This explicit smoke-test inbox replaces only the in-memory synthetic chart.
    # Voice calls always use the real looked-up record; no stored profile is changed here.
    session.remember_patients([patient | {"email": address}])
    results = await session.finish_demo()
    trace = config.CALLS_DIR / f"{session.call_id}.jsonl"
    if not results or results[0]["status"] != "accepted":
        raise SystemExit(f"Email was not accepted; inspect {trace}")
    print(f"Resend accepted the demo email: {results[0]['email_id']}")
    print("Check the recipient's inbox/spam folder; acceptance is not proof of delivery.")
    print(f"Trace: {trace}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--to", required=True, help="Your test inbox; this sends a real email.")
    parser.add_argument("--national-id", default="48064716Y", help="Synthetic clinic patient only.")
    parser.add_argument(
        "--move", action="store_true", help="Move a looked-up upcoming appointment."
    )
    args = parser.parse_args()
    asyncio.run(smoke(args.to, args.national_id, args.move))


if __name__ == "__main__":
    main()
