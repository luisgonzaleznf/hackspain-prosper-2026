"""Doctor & Site, call 0882e594: Dr. Requena is on leave 14-30 Sep, yet a search for him returns
his slots from 1 Oct with `blocked` empty. The case (twin doctor_and_site-d5b4f04886c5) accepts only
another doctor of the same specialty at the same site, so the search result has to say so."""

import asyncio
from datetime import datetime

import pytest
from app import clinic, config
from app.prompt import RULES
from app.session import CallSession
from app.tools import call_tool
from integrations import local_clinic

NOW = datetime(2026, 9, 18, 9, 0, tzinfo=config.TZ)
CATALOGUE = {
    "providers": [
        {
            "id": "PR02",
            "name": "Dr. Pablo Requena",
            "specialty_id": "general_practice",
            "languages": ["es"],
            "schedules": [{"location_id": "norte"}],
            "leave": {"start": "2026-09-14", "end": "2026-09-30", "reason": "sick leave"},
        },
        {
            "id": "PR07",
            "name": "Dra. Laura Benítez Roca",
            "specialty_id": "general_practice",
            "languages": ["es"],
            "schedules": [{"location_id": "norte"}, {"location_id": "centro"}],
            "leave": None,
        },
    ],
    "locations": [{"id": "norte", "name": "Arenal Norte"}],
}


def slot(provider: str, start: str) -> dict:
    return {
        "provider_id": provider,
        "provider_name": provider,
        "specialty_id": "general_practice",
        "location_id": "norte",
        "appointment_type_id": "review",
        "start_time": start,
        "payable_with": ["caser"],
    }


class FakeClinic:
    def __init__(self, slots):
        self.slots = slots

    async def availability(self, date_from, date_to, **filters):
        return {
            "slots": list(self.slots),
            "blocked": [],
            "appointment_type": {"id": "review", "name": "Review", "guidance": ""},
        }


@pytest.fixture(autouse=True)
def setup(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "CALLS_DIR", tmp_path)
    monkeypatch.setattr(clinic, "_catalogue", CATALOGUE)


def search(monkeypatch, slots, **args):
    monkeypatch.setattr(local_clinic, "client", lambda *_, **__: FakeClinic(slots))
    session = CallSession(call_id="00000000-0000-0000-0000-0000000000cc", started_at=NOW)
    window = {"date_from": "2026-09-20", "date_to": "2026-10-03"}
    return asyncio.run(call_tool(session, "search_availability", window | args))


def test_a_doctor_on_leave_with_slots_after_it_is_flagged(monkeypatch):
    result = search(monkeypatch, [slot("PR02", "2026-10-01T09:00:00+02:00")], provider_id="PR02")
    assert result["provider_on_leave"]["provider_id"] == "PR02"
    assert result["provider_on_leave"]["end"] == "2026-09-30"
    note = " ".join(result["notes"])
    assert "on leave until 2026-09-30" in note
    assert "specialty_id=general_practice" in note and "without provider_id" in note


def test_a_doctor_who_is_not_on_leave_gets_no_leave_note(monkeypatch):
    result = search(monkeypatch, [slot("PR07", "2026-09-22T09:00:00+02:00")], provider_id="PR07")
    assert "provider_on_leave" not in result
    assert "on leave" not in " ".join(result.get("notes", []))


def test_an_absence_outside_the_window_says_nothing(monkeypatch):
    # PR02's leave ended 30 Sep: a search from 1 Oct must not send the caller elsewhere.
    result = search(
        monkeypatch,
        [slot("PR02", "2026-10-01T09:00:00+02:00")],
        provider_id="PR02",
        date_from="2026-10-01",
        date_to="2026-10-09",
    )
    assert "provider_on_leave" not in result
    assert "on leave" not in " ".join(result.get("notes", []))


def test_a_future_absence_inside_the_window_is_named_with_its_dates(monkeypatch):
    away = {"start": "2026-09-30", "end": "2026-10-02", "reason": "congress"}
    partial = {
        "start": "2026-09-22",
        "end": "2026-09-22",
        "start_time": "12:00",
        "end_time": "14:00",
        "reason": "personal",
    }
    providers = [
        dict(
            CATALOGUE["providers"][1],
            absences=[{**partial}, {**away, "start_time": None, "end_time": None}],
        )
    ]
    monkeypatch.setattr(clinic, "_catalogue", CATALOGUE | {"providers": providers})
    result = search(monkeypatch, [slot("PR07", "2026-09-22T09:00:00+02:00")], provider_id="PR07")
    assert result["provider_on_leave"] | {} == {
        **away,
        "provider_id": "PR07",
        "provider_name": "Dra. Laura Benítez Roca",
    }
    note = " ".join(result["notes"])
    assert "is away from 2026-09-30 to 2026-10-02 (congress)" in note
    assert "on leave until" not in note
    # Part of a day away never triggers the redirect: its hours simply have no slots.
    providers[0]["absences"] = [partial]
    assert "provider_on_leave" not in search(
        monkeypatch, [slot("PR07", "2026-09-22T09:00:00+02:00")], provider_id="PR07"
    )


def test_prompt_moves_a_caller_off_a_doctor_on_leave_and_needs_a_real_yes():
    assert "A doctor who is AWAY (catalogue) now or on the day the caller needs: say they" in RULES
    assert "even if they have slots after the leave" in RULES
    assert "A doctor who is not at that site on that day" in RULES
    assert "said while you are still speaking is not a yes" in RULES
