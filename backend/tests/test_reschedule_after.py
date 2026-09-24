import asyncio
from datetime import datetime

import pytest
from app import config
from app.session import CallSession
from app.tools import TOOLS, call_tool
from integrations import local_clinic

NOW = datetime(2026, 9, 19, 9, 0, tzinfo=config.TZ)
AFTER = "2026-10-14T10:45:00+02:00"


def slot(start: str) -> dict:
    return {
        "provider_id": "PR11",
        "provider_name": "Dra. Isabel Montoro",
        "specialty_id": "gynaecology",
        "location_id": "centro",
        "appointment_type_id": "gynaecology_review",
        "start_time": start,
        "payable_with": ["nueva_mutua"],
    }


SLOTS = [
    slot("2026-10-14T12:15:00+02:00"),
    slot("2026-10-14T12:30:00+02:00"),
    slot("2026-10-15T10:15:00+02:00"),
    slot("2026-10-15T11:15:00+02:00"),
]


class FakeClinic:
    def __init__(self, slots):
        self.slots = slots
        self.request = None

    async def availability(self, date_from, date_to, **filters):
        self.request = (date_from, date_to, filters)
        return {
            "slots": list(self.slots),
            "blocked": [],
            "appointment_type": {
                "id": "gynaecology_review",
                "name": "Gynaecology Review",
                "guidance": "",
            },
        }


@pytest.fixture(autouse=True)
def calls_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "CALLS_DIR", tmp_path)


def search(monkeypatch, slots=SLOTS, **extra):
    fake = FakeClinic(slots)
    monkeypatch.setattr(local_clinic, "client", lambda *_, **__: fake)
    session = CallSession(call_id="00000000-0000-0000-0000-0000000000rr", started_at=NOW)
    args = {
        "provider_id": "PR11",
        "location_id": "centro",
        "patient_id": "P01320",
        "date_from": "2026-10-14",
        "date_to": "2026-10-16",
    }
    return asyncio.run(call_tool(session, "search_availability", args | extra)), fake, session


def test_search_after_starts_with_the_first_later_same_day_slot(monkeypatch):
    result, fake, _ = search(monkeypatch, after=AFTER)

    assert result["earliest_slots"][0]["slot"] == "2026-10-14T12:15:00+02:00"
    assert result["slots_found"] == 4
    assert fake.request[0] == "2026-10-14"


def test_search_after_excludes_a_slot_at_the_existing_start(monkeypatch):
    result, _, _ = search(monkeypatch, slots=[slot(AFTER), *SLOTS], after=AFTER)

    assert result["earliest_slots"][0]["slot"] == "2026-10-14T12:15:00+02:00"
    assert AFTER not in [item["slot"] for item in result["earliest_slots"]]


def test_search_without_after_keeps_the_existing_order_and_slots(monkeypatch):
    result, _, _ = search(monkeypatch, slots=[slot(AFTER), *SLOTS])

    assert result["earliest_slots"][0]["slot"] == AFTER
    assert result["slots_found"] == 5


def test_search_tool_exposes_after_as_optional():
    spec = next(tool for tool in TOOLS if tool["name"] == "search_availability")

    assert "after" in spec["parameters"]["properties"]
    assert "after" not in spec["parameters"]["required"]
