import asyncio
from datetime import datetime

from app import clinic, config
from app.prompt import RULES
from app.session import CallSession
from app.tools import call_tool
from integrations import local_clinic


def test_second_policy_is_forwarded_and_billed_without_changing_chart(monkeypatch, tmp_path):
    monkeypatch.setattr(config, "CALLS_DIR", tmp_path)
    monkeypatch.setattr(clinic, "_catalogue", None)

    class Quotes:
        async def availability(self, start, end, **filters):
            assert filters["patient_id"] == "P1"
            assert filters["insurers"] == ["sanitas"]
            return {
                "blocked": [],
                "appointment_type": {"id": "review", "name": "Review", "guidance": ""},
                "slots": [
                    {
                        "provider_id": "PR03",
                        "provider_name": "Doctor",
                        "location_id": "sur",
                        "appointment_type_id": "review",
                        "start_time": "2026-09-21T09:00:00+02:00",
                        "payable_with": ["sanitas"],
                    }
                ],
            }

    monkeypatch.setattr(local_clinic, "client", lambda *_, **__: Quotes())
    session = CallSession(
        call_id="second-policy", started_at=datetime(2026, 9, 19, tzinfo=config.TZ)
    )
    session.remember_patients([{"patient_id": "P1", "insurer": "asisa"}])
    result = asyncio.run(
        call_tool(
            session,
            "search_availability",
            {
                "patient_id": "P1",
                "specialty_id": "general_practice",
                "location_id": "sur",
                "date_from": "2026-09-21",
                "date_to": "2026-09-21",
                "insurers": ["sanitas"],
            },
        )
    )
    offered = result["earliest_slots"][0]
    args = {
        "patient_id": "P1",
        "provider_id": offered["provider_id"],
        "location_id": "sur",
        "slot": offered["slot"],
        "policy_id": "asisa",
    }
    assert "error" in asyncio.run(call_tool(session, "record_booking", args))
    recorded = asyncio.run(call_tool(session, "record_booking", args | {"policy_id": "sanitas"}))
    assert recorded["recorded"]["policy_id"] == "sanitas"
    assert session.patients["P1"]["insurer"] == "asisa"


def test_vague_second_policy_requires_card_and_valid_primary_stays_primary():
    assert "ask them to find the card and read its insurer" in RULES
    assert "on file already covers a fitting slot, use it" in RULES
