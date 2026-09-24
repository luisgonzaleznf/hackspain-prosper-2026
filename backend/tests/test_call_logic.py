"""The logic that decides what a call records: check letters, staging rules, pre-write checks,
and the outcome logged at hang-up. Offline: no clinic database is read."""

import asyncio
import json
from datetime import datetime

import pytest
from app import clinic, config
from app.session import FALLBACK, CallSession
from app.tools import call_tool

NOW = datetime(2026, 9, 18, 19, 30, tzinfo=config.TZ)
SLOT = {
    "provider_id": "PR01",
    "provider_name": "Dra. Carmen Ortiz Vidal",
    "specialty_id": "general_practice",
    "location_id": "centro",
    "appointment_type_id": "review",
    "start_time": "2026-09-19T11:00:00+02:00",
    "duration_minutes": 15,
    "payable_with": ["mapfre"],
}
PATIENT = {
    "patient_id": "P00001",
    "given_name": "Josefa",
    "first_surname": "Domínguez",
    "second_surname": "Navarro",
    "national_id": "48064716Y",
    "date_of_birth": "2001-09-19",
    "phone": "711330529",
    "has_visited_before": True,
    "insurer": "mapfre",
    "referrals": [],
    "note": "",
}


@pytest.fixture(autouse=True)
def calls_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "CALLS_DIR", tmp_path)


def session_with_slot() -> CallSession:
    s = CallSession(call_id="00000000-0000-0000-0000-000000000001", started_at=NOW)
    s.remember_patients([PATIENT])
    s.remember_slots([SLOT])
    return s


def book_args(**over) -> dict:
    return {
        "patient_id": "P00001",
        "provider_id": "PR01",
        "location_id": "centro",
        "appointment_type_id": "review",
        "slot": "2026-09-19T11:00:00+02:00",
        "policy_id": "mapfre",
    } | over


def run(coro):
    return asyncio.run(coro)


# ── national id ─────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "raw", ["48064716Y", "48064716-y", "4806 4716 Y", "Z5361712A", "x-8148593-s"]
)
def test_valid_ids(raw):
    assert clinic.national_id_valid(raw)


@pytest.mark.parametrize("raw", ["48064716X", "4806471Y", "Z53617120A", "", "Q5361712A"])
def test_invalid_ids(raw):
    assert not clinic.national_id_valid(raw)


# ── staging ─────────────────────────────────────────────────────────


def test_new_booking_for_same_patient_replaces_old():
    s = CallSession(call_id="c")
    s.stage({"action": "BOOK", "patient_id": "P1", "slot": "a"})
    s.stage({"action": "BOOK", "patient_id": "P1", "slot": "b"})
    s.stage({"action": "BOOK", "patient_id": "P2", "slot": "c"})
    assert [(a["patient_id"], a["slot"]) for a in s.actions] == [("P1", "b"), ("P2", "c")]


def test_no_action_replaces_everything_and_a_write_drops_it():
    s = CallSession(call_id="c")
    s.stage({"action": "BOOK", "patient_id": "P1", "slot": "a"})
    s.stage({"action": "NO_ACTION", "reason": "no_availability"})
    assert s.actions == [{"action": "NO_ACTION", "reason": "no_availability"}]
    s.stage({"action": "CANCEL", "appointment_id": "A1"})
    assert s.actions == [{"action": "CANCEL", "appointment_id": "A1"}]


def test_two_cancellations_both_stay_but_a_move_replaces_a_cancel_of_the_same_appointment():
    s = CallSession(call_id="c")
    s.stage({"action": "CANCEL", "appointment_id": "A1"})
    s.stage({"action": "CANCEL", "appointment_id": "A2"})
    s.stage({"action": "RESCHEDULE", "appointment_id": "A1", "slot": "x"})
    assert [(a["action"], a["appointment_id"]) for a in s.actions] == [
        ("CANCEL", "A2"),
        ("RESCHEDULE", "A1"),
    ]


# ── pre-write checks ────────────────────────────────────────────────


def test_booking_an_offered_slot_is_staged_with_the_offered_type():
    s = session_with_slot()
    out = run(call_tool(s, "record_booking", book_args(appointment_type_id="first_visit")))
    assert "error" not in out
    assert s.actions == [{"action": "BOOK", **book_args()}]


@pytest.mark.parametrize(
    "over",
    [
        {"patient_id": "P09999"},  # never looked up
        {"slot": "2026-09-19T07:00:00+02:00"},  # never offered
        {"provider_id": "PR07"},  # offered, but for another provider
        {"slot": "2026-09-19T11:00:00"},  # no offset
        {"policy_id": "sanitas"},  # slot not payable with that plan
    ],
)
def test_booking_is_refused_unless_it_matches_a_lookup(over):
    s = session_with_slot()
    out = run(call_tool(s, "record_booking", book_args(**over)))
    assert "error" in out
    assert s.actions == []


def test_same_day_slot_is_refused():
    s = session_with_slot()
    s.started_at = datetime(2026, 9, 19, 8, 0, tzinfo=config.TZ)
    assert "error" in run(call_tool(s, "record_booking", book_args()))


def test_utc_slot_matches_the_madrid_one():
    s = session_with_slot()
    out = run(call_tool(s, "record_booking", book_args(slot="2026-09-19T09:00:00+00:00")))
    assert out["recorded"]["slot"] == "2026-09-19T11:00:00+02:00"


def test_registration_rejects_a_bad_check_letter_and_normalizes_a_good_one():
    s = CallSession(call_id="c")
    fields = {
        "given_name": "Ana",
        "first_surname": "García",
        "second_surname": "López",
        "national_id": "48064716X",
        "date_of_birth": "1988-03-14",
        "phone": "+34 612 345 678",
        "email": "Ana.Garcia @Gmail.com",
        "insurer": "adeslas",
    }
    assert "error" in run(call_tool(s, "record_registration", fields))
    out = run(call_tool(s, "record_registration", fields | {"national_id": "48064716-y"}))
    assert out["recorded"]["national_id"] == "48064716Y"
    assert out["recorded"]["email"] == "ana.garcia@gmail.com"
    assert out["recorded"]["phone"] == "612345678"


def _register_fields(**over) -> dict:
    return {
        "given_name": "Ana",
        "first_surname": "García",
        "second_surname": "López",
        "national_id": "48064716Y",
        "date_of_birth": "1988-03-14",
        "phone": "612345678",
        "email": "ana.garcia@gmail.com",
        "insurer": "adeslas",
    } | over


# ── phone sanity ────────────────────────────────────────────────────


def test_record_registration_rejects_an_eight_digit_phone():
    # Call b9c5b361-ad3d-450d-b46f-d5dd42f59637: the voice cut the caller off one digit early
    # ("seven eight three eight six nine one three" -> the answer was 783869132) and 78386913
    # (8 digits) was staged. A Spanish phone number is always 9 digits.
    s = CallSession(call_id="c")
    out = run(call_tool(s, "record_registration", _register_fields(phone="78386913")))
    assert "error" in out
    assert "9" in out["error"]
    assert s.actions == []


@pytest.mark.parametrize("raw", ["+34 612 345 678", "0034612345678", "612-345-678"])
def test_record_registration_normalizes_a_country_code_and_dashes(raw):
    s = CallSession(call_id="c")
    out = run(call_tool(s, "record_registration", _register_fields(phone=raw)))
    assert "error" not in out
    assert out["recorded"]["phone"] == "612345678"


def test_record_registration_flags_a_phone_one_digit_off_caller_id_then_accepts_a_retry():
    s = CallSession(call_id="c", from_number="+34731169716")
    first = run(call_tool(s, "record_registration", _register_fields(phone="731169717")))
    assert "error" in first
    assert "731 169 716" in first["error"]
    assert s.phone_mismatch_flagged is True
    assert s.actions == []
    second = run(call_tool(s, "record_registration", _register_fields(phone="731169717")))
    assert "error" not in second
    assert second["recorded"]["phone"] == "731169717"


def test_reason_must_be_in_the_closed_vocabulary():
    s = CallSession(call_id="c")
    assert "error" in run(call_tool(s, "record_no_action", {"reason": "because"}))
    assert "error" not in run(call_tool(s, "record_no_action", {"reason": "referral_required"}))


def test_unknown_tool_and_missing_args_do_not_raise():
    s = CallSession(call_id="c")
    assert "error" in run(call_tool(s, "nope", {}))
    assert "error" in run(call_tool(s, "record_cancellation", {}))


# ── hang-up outcome ─────────────────────────────────────────────────


def outcome(s: CallSession) -> list[dict]:
    """The actions the call's log says it ended with."""
    lines = (config.CALLS_DIR / f"{s.call_id}.jsonl").read_text().splitlines()
    return next(e["actions"] for e in map(json.loads, lines) if e["kind"] == "call_ended")


def test_corrected_registration_replaces_the_staged_register_and_is_logged_once():
    s = CallSession(call_id="c")
    first = run(call_tool(s, "record_registration", _register_fields()))
    second = run(
        call_tool(s, "record_registration", _register_fields(email="ana.corrected@gmail.com"))
    )
    assert "error" not in first
    assert "error" not in second
    assert s.actions == [
        {
            "action": "REGISTER",
            "given_name": "Ana",
            "first_surname": "García",
            "second_surname": "López",
            "national_id": "48064716Y",
            "date_of_birth": "1988-03-14",
            "phone": "612345678",
            "email": "ana.corrected@gmail.com",
            "insurer": "adeslas",
        }
    ]
    run(s.finish())
    sent = outcome(s)
    assert len(sent) == 1
    assert sent[0]["action"] == "REGISTER"
    assert sent[0]["email"] == "ana.corrected@gmail.com"


def test_finish_logs_every_staged_action_once():
    s = CallSession(call_id="c")
    s.stage({"action": "CANCEL", "appointment_id": "A1"})
    s.stage({"action": "CANCEL", "appointment_id": "A2"})
    run(s.finish())
    assert run(s.finish()) == []
    assert outcome(s) == [
        {"action": "CANCEL", "appointment_id": "A1"},
        {"action": "CANCEL", "appointment_id": "A2"},
    ]
    lines = (config.CALLS_DIR / "c.jsonl").read_text().splitlines()
    assert sum(json.loads(line)["kind"] == "call_ended" for line in lines) == 1


def test_finish_with_nothing_staged_still_states_a_reason():
    s = CallSession(call_id="c")
    run(s.finish())
    assert outcome(s) == [FALLBACK]


# ── calendar ────────────────────────────────────────────────────────


def test_calendar_marks_tomorrow_sundays_and_the_holiday():
    cat = {
        "calendar": {"ends": "2026-10-16", "closure_days": ["2026-10-12"]},
        "locations": [{"id": "centro", "hours": [{"weekday": "saturday", "intervals": []}]}],
    }
    text = clinic.calendar_text(NOW, cat)
    assert "Sat 19 Sep 2026 (2026-09-19) = tomorrow — Saturday: only centro is open" in text
    assert "Sun 20 Sep 2026 (2026-09-20) = the day after tomorrow — closed (Sunday)" in text
    assert "Mon 12 Oct 2026 (2026-10-12) — CLOSED everywhere (public holiday)" in text
