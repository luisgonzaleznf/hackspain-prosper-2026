"""Step-1 fixes from the 73-case sweep: the evidence-based fallback, the calendar end, staging
that absorbs a duplicate delegation, and what the codex voice logs. Offline: the clinic is faked."""

import asyncio
import json
from datetime import datetime

import pytest
from app import clinic, config
from app.session import FALLBACK, CallSession
from app.tools import call_tool
from app.voice.codex.service import _worth_logging
from integrations import local_clinic

NOW = datetime(2026, 9, 18, 9, 0, tzinfo=config.TZ)


@pytest.fixture(autouse=True)
def calls_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "CALLS_DIR", tmp_path)


class FakeClinic:
    """Answers one availability search."""

    def __init__(self, slots=(), blocked=()):
        self.slots, self.blocked = list(slots), list(blocked)

    async def availability(self, date_from, date_to, **filters):
        return {
            "slots": self.slots,
            "blocked": self.blocked,
            "appointment_type": {"id": "review", "name": "Review", "guidance": ""},
        }


def outcome(s: CallSession) -> list[dict]:
    """The actions the call's log says it ended with."""
    lines = (config.CALLS_DIR / f"{s.call_id}.jsonl").read_text().splitlines()
    return next(e for e in map(json.loads, lines) if e["kind"] == "call_ended")["actions"]


def run(coro):
    return asyncio.run(coro)


def session() -> CallSession:
    return CallSession(call_id="00000000-0000-0000-0000-0000000000aa", started_at=NOW)


def search(s: CallSession, **extra) -> dict:
    args = {"specialty_id": "gynaecology", "date_from": "2026-09-19", "date_to": "2026-09-30"}
    return run(call_tool(s, "search_availability", args | extra))


SLOT = {
    "provider_id": "PR11",
    "provider_name": "Dra. Isabel Montoro",
    "specialty_id": "gynaecology",
    "location_id": "centro",
    "appointment_type_id": "gynaecology_review",
    "start_time": "2026-09-23T09:00:00+02:00",
    "payable_with": ["mapfre"],
}


# ── fallback: what an unstaged call reports ─────────────────────────


def test_a_call_that_never_searched_keeps_the_old_fallback():
    assert session().fallback() == FALLBACK


def test_an_empty_search_with_nothing_blocked_is_no_availability(monkeypatch):
    monkeypatch.setattr(local_clinic, "client", lambda *_, **__: FakeClinic())
    s = session()
    search(s)
    assert s.fallback() == {"action": "NO_ACTION", "reason": "no_availability"}


def test_the_rules_460d_one_rule_blocking_everyone_is_logged_as_that_reason(monkeypatch):
    # the_rules-460d in the sweep: search blocked by specialty_not_covered, nothing staged,
    # the old fallback said out_of_scope where specialty_not_covered was expected.
    fake = FakeClinic(blocked=[{"provider_id": "PR11", "restriction": "specialty_not_covered"}])
    monkeypatch.setattr(local_clinic, "client", lambda *_, **__: fake)
    s = session()
    search(s)
    run(s.finish())
    assert outcome(s) == [{"action": "NO_ACTION", "reason": "specialty_not_covered"}]


def test_mixed_rules_or_a_search_that_found_slots_stay_out_of_scope(monkeypatch):
    mixed = FakeClinic(
        blocked=[
            {"provider_id": "PR01", "restriction": "provider_not_in_network"},
            {"provider_id": "PR02", "restriction": "provider_on_leave"},
        ]
    )
    monkeypatch.setattr(local_clinic, "client", lambda *_, **__: mixed)
    s = session()
    search(s)
    assert s.fallback() == FALLBACK
    monkeypatch.setattr(local_clinic, "client", lambda *_, **__: FakeClinic(slots=[SLOT]))
    search(s)
    assert s.fallback() == FALLBACK


def test_an_unknown_restriction_is_never_logged_as_a_reason(monkeypatch):
    fake = FakeClinic(blocked=[{"provider_id": "PR11", "restriction": "not_a_reason"}])
    monkeypatch.setattr(local_clinic, "client", lambda *_, **__: fake)
    s = session()
    search(s)
    assert s.fallback() == FALLBACK


def test_the_latest_search_is_the_evidence(monkeypatch):
    s = session()
    monkeypatch.setattr(local_clinic, "client", lambda *_, **__: FakeClinic())
    search(s)
    monkeypatch.setattr(local_clinic, "client", lambda *_, **__: FakeClinic(slots=[SLOT]))
    search(s)
    assert s.fallback() == FALLBACK  # slots were found last: out_of_scope, not no_availability


def test_a_part_of_day_filter_that_empties_the_search_counts_as_empty(monkeypatch):
    monkeypatch.setattr(local_clinic, "client", lambda *_, **__: FakeClinic(slots=[SLOT]))  # 09:00 only
    s = session()
    search(s, part_of_day="afternoon")
    assert s.fallback() == {"action": "NO_ACTION", "reason": "no_availability"}


def test_anything_staged_beats_the_fallback(monkeypatch):
    fake = FakeClinic()
    monkeypatch.setattr(local_clinic, "client", lambda *_, **__: fake)
    s = session()
    search(s)
    s.stage({"action": "CANCEL", "appointment_id": "A1"})
    run(s.finish())
    assert [a["action"] for a in outcome(s)] == ["CANCEL"]


# ── the calendar end is always stated ───────────────────────────────


def test_the_calendar_end_is_stated_even_when_the_day_list_stops_on_it():
    # Pinned eval time Fri 18 Sep + 28 listed days lands exactly on the last day (16 Oct), so
    # the old "after X: the calendar ends" line never printed and the brain searched past it.
    cat = {
        "calendar": {"ends": "2026-10-16", "closure_days": ["2026-10-12"]},
        "locations": [{"id": "centro", "hours": [{"weekday": "saturday", "intervals": []}]}],
    }
    text = clinic.calendar_text(NOW, cat)
    assert "The bookable calendar ends Friday 16 October 2026 (2026-10-16)" in text


def test_a_search_past_the_calendar_end_is_cut_there_with_a_note(monkeypatch):
    asked = []

    class Recording(FakeClinic):
        async def availability(self, date_from, date_to, **filters):
            asked.append((date_from, date_to))
            return await super().availability(date_from, date_to, **filters)

    cat = {"calendar": {"ends": "2026-09-25"}, "providers": [], "locations": []}
    monkeypatch.setattr(clinic, "_catalogue", cat)
    monkeypatch.setattr(local_clinic, "client", lambda *_, **__: Recording())
    result = search(session(), date_from="2026-09-21", date_to="2026-10-04")
    assert asked == [("2026-09-21", "2026-09-25")]
    assert result["window"] == ["2026-09-21", "2026-09-25"]
    assert "The bookable calendar ends 2026-09-25, so this search stops there." in result["notes"]


# ── a duplicate delegation cannot double-record ─────────────────────


def test_the_same_action_staged_twice_is_recorded_once():
    s = session()
    booking = {
        "action": "BOOK",
        "patient_id": "P00001",
        "provider_id": "PR11",
        "location_id": "centro",
        "appointment_type_id": "gynaecology_review",
        "slot": "2026-09-23T09:00:00+02:00",
        "policy_id": "mapfre",
    }
    s.stage(dict(booking))
    s.stage(dict(booking))
    s.stage({"action": "CANCEL", "appointment_id": "A1"})
    s.stage({"action": "CANCEL", "appointment_id": "A1"})
    assert [a["action"] for a in s.actions] == ["BOOK", "CANCEL"]


# ── what the codex voice writes to the call log ─────────────────────


@pytest.mark.parametrize(
    "event,logged",
    [
        ({"source": "oai", "type": "turn.created", "turn": {"role": "user"}}, True),
        ({"source": "oai", "type": "turn.done"}, True),
        ({"source": "oai", "type": "error", "error": {"message": "x"}}, True),
        ({"source": "oai", "type": "session.usage.updated"}, True),
        ({"source": "oai", "type": "delegation.created"}, True),
        ({"source": "oai", "type": "turn.delta"}, False),
        ({"source": "oai", "type": "input_transcript.added"}, False),
        ({"source": "oai", "type": "output_transcript.added"}, False),
        ({"source": "oai", "type": "delegation.context.appended"}, False),
        ({"source": "codex", "method": "turn/completed"}, True),
        ({"source": "codex", "method": "thread/realtime/transcript/done"}, False),
        ({"source": "brain", "type": "brain.continue"}, True),
    ],
)
def test_the_voice_events_that_explain_a_stall_are_logged(event, logged):
    assert _worth_logging(event) is logged

