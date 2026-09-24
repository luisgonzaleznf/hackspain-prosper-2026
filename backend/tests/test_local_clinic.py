import asyncio
import json
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import datetime

import pytest
from app import clinic, config, prompt, prosper
from app.session import CallSession
from app.tools import REGISTER_FIELDS, TOOLS, call_tool
from integrations import clinic_api
from integrations.local_store import LocalStore
from integrations.twilio import TwilioCallSession

NOW = datetime(2026, 9, 20, 10, tzinfo=config.TZ)
PROFILE = {
    "given_name": "Ana",
    "first_surname": "García",
    "second_surname": "López",
    "national_id": "48064716Y",
    "date_of_birth": "1988-03-14",
    "phone": "612345678",
    "email": "ana@example.test",
    "insurer": "privado",
}
# A new local patient gives only a name; the phone comes from caller ID, never asked.
NEW_PATIENT = {"given_name": "Ana", "first_surname": "García", "second_surname": "López"}
PHONE = "+34612345678"
REMOTE_PATIENT = {
    **PROFILE,
    "patient_id": "P001",
    "national_id": "12345678Z",
    "phone": "600123456",
    "has_visited_before": False,
    "referrals": [],
    "note": "",
}
TYPE = {
    "id": "first_visit",
    "name": "First Visit",
    "duration_minutes": 30,
    "guidance": "New patients",
    "new_patient_requirement": "new_only",
}
SLOTS = [
    {
        "provider_id": "PR03",
        "provider_name": "Doctor Sáez",
        "location_id": "sur",
        "specialty_id": "general_practice",
        "appointment_type_id": "first_visit",
        "start_time": f"2026-09-21T{time}:00+02:00",
        "duration_minutes": 30,
        "payable_with": ["privado"],
    }
    for time in ["09:00", "09:15", "09:30", "10:00"]
]
CATALOGUE = {
    "providers": [{"id": "PR03", "name": "Doctor Sáez", "specialty_id": "general_practice"}],
    "locations": [{"id": "sur", "name": "Arenal Sur"}],
    "specialties": [
        {
            "id": "general_practice",
            "min_age_months": 168,
            "max_age_months": None,
            "referral_required": False,
        }
    ],
}


class Remote:
    def __init__(self):
        self.slots = deepcopy(SLOTS)
        self.diary = []
        self.submits = []
        self.searches = []
        self.submissions_feed = []

    async def directory(self, **query):
        if query.get("national_id") == REMOTE_PATIENT["national_id"] or query.get("phone") in {
            REMOTE_PATIENT["phone"],
            "+34" + REMOTE_PATIENT["phone"],
        }:
            return [dict(REMOTE_PATIENT)]
        return []

    async def availability(self, *args, **kwargs):
        self.searches.append(kwargs)
        return {
            "slots": deepcopy(self.slots),
            "blocked": [],
            "providers": [],
            "appointment_type": TYPE,
        }

    async def appointments(self, patient_id, when="upcoming"):
        return deepcopy(self.diary)

    async def submit(self, payload):
        self.submits.append(payload)
        return 200, {}

    async def submissions(self, limit=200):
        return deepcopy(self.submissions_feed)


@pytest.fixture
def setup(tmp_path, monkeypatch):
    monkeypatch.setenv("LOCAL_CLINIC_DB", str(tmp_path / "clinic.sqlite3"))
    monkeypatch.setattr(config, "CALLS_DIR", tmp_path / "calls")
    monkeypatch.setattr(clinic, "_catalogue", deepcopy(CATALOGUE))
    remote = Remote()
    monkeypatch.setattr(prosper, "client", lambda: remote)
    # The console calendar caches Prosper's feed and the persona name directory per process.
    monkeypatch.setattr(clinic_api, "_names", None)
    monkeypatch.setattr(clinic_api, "_submissions", None)
    monkeypatch.setattr(clinic_api, "PUBLIC_CASES", tmp_path / "public-cases.json")
    return remote


def run(session, tool_name, **args):
    return asyncio.run(call_tool(session, tool_name, args))


def register(session, **overrides):
    result = run(session, "record_registration", **{**NEW_PATIENT, "confirmed": True, **overrides})
    assert "error" not in result, result
    return result["patient_id"]


def search(session, patient):
    result = run(
        session,
        "search_availability",
        patient_id=patient,
        specialty_id="general_practice",
        date_from="2026-09-21",
        date_to="2026-09-21",
    )
    assert "error" not in result, result
    return result


def book(session, patient, at="09:00", **overrides):
    return run(
        session,
        "record_booking",
        **{
            "patient_id": patient,
            "provider_id": "PR03",
            "location_id": "sur",
            "appointment_type_id": "first_visit",
            "slot": f"2026-09-21T{at}:00+02:00",
            "policy_id": "privado",
            "confirmed": True,
            **overrides,
        },
    )


def identify(session, national_id=PROFILE["national_id"]):
    return run(
        session,
        "find_patient",
        name="Ana García López",
        national_id=national_id,
        date_of_birth=PROFILE["date_of_birth"],
    )


def identify_by_phone(session):
    return run(session, "find_patient", name="Ana García López", phone="612345678")


def test_register_book_and_recall_in_new_call(setup):
    first = TwilioCallSession(call_id="CA-first", started_at=NOW, from_number=PHONE)
    assert "error" in run(first, "record_registration", **NEW_PATIENT)
    patient = register(first)
    saved = first.store.patient(patient)
    assert saved["registration_pending"] is True
    assert saved["insurer"] == "privado"
    assert saved["phone"] == "612345678"
    assert saved["national_id"] is None and saved["date_of_birth"] is None
    assert search(first, patient)["slots_found"] == 4
    booked = book(first, patient)
    assert booked["persisted"] is True
    assert book(first, patient)["appointment_id"] == booked["appointment_id"]
    assert len(first.store.appointments()) == 1
    assert [s["slot"][11:16] for s in search(first, patient)["earliest_slots"]] == [
        "09:30",
        "10:00",
    ]
    asyncio.run(first.finish())
    second = asyncio.run(
        TwilioCallSession.start(call_id="CA-second", from_number="+34612345678", started_at=NOW)
    )
    assert second.caller_matches[0]["patient_id"] == patient
    assert '"registration_pending": true' in prompt._caller_id(second)
    assert "error" in run(second, "list_appointments", patient_id=patient)
    # A chart without a date of birth can't be verified by one; name + phone verifies it.
    unverified = run(second, "find_patient", name="Ana García López", date_of_birth="1988-03-14")
    assert unverified["verified_patient_ids"] == []
    assert identify_by_phone(second)["verified_patient_ids"] == [patient]
    diary = run(second, "list_appointments", patient_id=patient)["appointments"]
    assert diary[0]["appointment_id"] == booked["appointment_id"]
    assert setup.submits == []
    assert setup.searches[0]["patient_id"] is None  # never send local IDs to Prosper


def test_reschedule_cancel_and_release_local_slot(setup):
    session = TwilioCallSession(call_id="CA-move", started_at=NOW)
    patient = register(session)
    search(session, patient)
    appointment_id = book(session, patient)["appointment_id"]
    search(session, patient)
    moved = run(
        session,
        "record_reschedule",
        appointment_id=appointment_id,
        provider_id="PR03",
        location_id="sur",
        slot=SLOTS[3]["start_time"],
        policy_id="privado",
        confirmed=True,
    )
    assert moved["appointment_id"] == appointment_id
    # Moving back to a former time is a real change, not a replay of an old result.
    search(session, patient)
    back = run(
        session,
        "record_reschedule",
        appointment_id=appointment_id,
        provider_id="PR03",
        location_id="sur",
        slot=SLOTS[0]["start_time"],
        policy_id="privado",
        confirmed=True,
    )
    assert back["appointment"]["start_time"] == SLOTS[0]["start_time"]
    cancelled = run(session, "record_cancellation", appointment_id=appointment_id, confirmed=True)
    assert cancelled["appointment"]["status"] == "cancelled"
    assert run(session, "list_appointments", patient_id=patient)["appointments"] == []
    assert search(session, patient)["slots_found"] == 4


def test_existing_prosper_patient_uses_local_calendar_overlay(setup):
    session = TwilioCallSession(call_id="CA-remote", started_at=NOW)
    assert identify(session, REMOTE_PATIENT["national_id"])["verified_patient_ids"] == ["P001"]
    search(session, "P001")
    booked = book(session, "P001")
    assert booked["persisted"]
    assert setup.searches[0]["patient_id"] == "P001"
    second = TwilioCallSession(call_id="CA-remote-2", started_at=NOW)
    identify(second, REMOTE_PATIENT["national_id"])
    assert (
        run(second, "list_appointments", patient_id="P001")["appointments"][0]["appointment_id"]
        == booked["appointment_id"]
    )
    assert setup.submits == []


def test_duplicate_registration_and_identity_guard(setup):
    first = TwilioCallSession(call_id="CA-one", started_at=NOW, from_number=PHONE)
    patient = register(first)
    second = TwilioCallSession(call_id="CA-two", started_at=NOW, from_number=PHONE)
    assert "error" in run(second, "record_registration", **NEW_PATIENT, confirmed=True)
    # The name alone, or an identifier the chart doesn't hold, never verifies.
    run(second, "find_patient", name="Ana García López")
    run(second, "find_patient", name="Ana García López", date_of_birth="")
    search(second, patient)
    assert "error" in book(second, patient)
    assert "error" in book(second, patient, confirmed=False)
    assert first.store.appointments() == []
    identify_by_phone(second)
    assert book(second, patient)["persisted"]
    # A namesake on another line is a different person.
    other = TwilioCallSession(call_id="CA-three", started_at=NOW, from_number="+34699000111")
    assert register(other) != patient
    # Full profiles (seeded, not phone-registered) still refuse a repeated DNI/NIE.
    LocalStore().save("seed", {**PROFILE, "action": "REGISTER"})
    with pytest.raises(ValueError):
        LocalStore().save("seed-again", {**PROFILE, "action": "REGISTER"})


def test_siblings_on_one_phone_and_withheld_caller_id(setup):
    family = TwilioCallSession(call_id="CA-family", started_at=NOW, from_number=PHONE)
    ana = register(family)
    mariana = register(family, given_name="Mariana")
    later = TwilioCallSession(call_id="CA-family-2", started_at=NOW)
    # "Ana" is inside "Mariana" and both charts hold this phone: the spoken full name decides.
    assert identify_by_phone(later)["verified_patient_ids"] == [ana]
    found = run(later, "find_patient", name="Mariana García López", phone="612345678")
    assert found["verified_patient_ids"] == sorted([ana, mariana])
    # Twilio's withheld-number placeholder is never stored as the patient's phone, and a
    # caller ID with no digits never matches charts that hold no phone.
    hidden = TwilioCallSession(call_id="CA-hidden", started_at=NOW, from_number="+266696687")
    assert LocalStore().patient(register(hidden, given_name="Luz"))["phone"] is None
    for withheld in ("+266696687", "anonymous"):
        stranger = asyncio.run(
            TwilioCallSession.start(call_id=f"CA-{withheld}", from_number=withheld, started_at=NOW)
        )
        assert stranger.caller_matches == []


def test_rechecks_remote_availability_before_write(setup):
    session = TwilioCallSession(call_id="CA-stale", started_at=NOW)
    patient = register(session)
    search(session, patient)
    setup.slots = []
    assert "error" in book(session, patient)
    assert session.store.appointments() == []


def test_local_age_and_referral_rules(setup, monkeypatch):
    session = TwilioCallSession(call_id="CA-child", started_at=NOW)
    child = {**PROFILE, "date_of_birth": "2020-01-01", "action": "REGISTER"}
    patient = LocalStore().save("seed", child)["patient_id"]
    found = run(
        session, "find_patient", name="Ana García López", national_id=PROFILE["national_id"]
    )
    assert found["verified_patient_ids"] == [patient]
    result = search(session, patient)
    assert result["slots_found"] == 0
    assert result["blocked"][0]["restriction"] == "not_eligible_age"
    # No date of birth on file yet: the age check waits for reception.
    assert search(session, register(session, given_name="Pedro"))["slots_found"] == 4
    clinic._catalogue["specialties"][0].update(min_age_months=0, referral_required=True)
    result = search(session, patient)
    assert result["slots_found"] == 0
    assert result["blocked"][0]["restriction"] == "referral_required"


def test_db_serializes_two_callers_competing_for_overlapping_slots(setup):
    store = LocalStore()
    profile = {**PROFILE, "action": "REGISTER"}
    patient = store.save("create", profile)["patient"]

    def attempt(index):
        action = {
            "action": "BOOK",
            "patient_id": patient["patient_id"],
            "provider_id": "PR03",
            "location_id": "sur",
            "slot": SLOTS[index]["start_time"],
            "policy_id": "privado",
        }
        try:
            return LocalStore().save(f"race-{index}", action, patient=patient, slot=SLOTS[index])
        except ValueError as error:
            return {"error": str(error)}

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(attempt, [0, 1]))
    assert sum("appointment_id" in r for r in results) == 1
    assert len(LocalStore().appointments()) == 1


def test_local_cancellation_masks_prosper_appointment(setup):
    original = {**SLOTS[0], "appointment_id": "A001", "patient_id": "P001"}
    setup.diary = [original]
    session = TwilioCallSession(call_id="CA-cancel", started_at=NOW)
    identify(session, REMOTE_PATIENT["national_id"])
    run(session, "list_appointments", patient_id="P001")
    result = run(session, "record_cancellation", appointment_id="A001", confirmed=True)
    assert result["persisted"]
    assert run(session, "list_appointments", patient_id="P001")["appointments"] == []
    assert setup.diary == [original]
    assert setup.submits == []


def test_scored_tools_keep_original_contract_and_clear_does_not_undo_saved(setup):
    assert CallSession(call_id="scored").tool_specs(TOOLS) is TOOLS
    session = TwilioCallSession(call_id="local", started_at=NOW)
    local = session.tool_specs(TOOLS)
    assert (
        "confirmed"
        in next(t for t in local if t["name"] == "record_booking")["parameters"]["required"]
    )
    assert (
        "confirmed"
        not in next(t for t in TOOLS if t["name"] == "record_booking")["parameters"]["required"]
    )
    registration = next(t for t in local if t["name"] == "record_registration")["parameters"]
    assert registration["required"] == ["given_name", "first_surname", "confirmed"]
    assert set(registration["properties"]) == {*NEW_PATIENT, "patient_id", "confirmed"}
    scored_registration = next(t for t in TOOLS if t["name"] == "record_registration")
    assert scored_registration["parameters"]["required"] == REGISTER_FIELDS
    scored = run(CallSession(call_id="scored-registration"), "record_registration", **NEW_PATIENT)
    assert "Still missing" in scored["error"]
    patient = register(session)
    search(session, patient)
    book(session, patient)
    assert "error" in run(session, "clear_recorded_actions")
    run(session, "record_no_action", reason="out_of_scope")
    assert len(session.store.appointments()) == 1


def test_two_registrations_and_explicit_correction(setup):
    session = TwilioCallSession("CAfamilies", started_at=NOW, from_number=PHONE)
    first = register(session)
    assert register(session) == first  # A retry of the same name reuses the profile.
    second = register(session, given_name="Pedro")
    assert first != second
    corrected = register(session, patient_id=first, second_surname="Lopes")
    assert corrected == first
    single = register(session, given_name="John", first_surname="Smith", second_surname="")
    assert len(LocalStore().patients()) == 3
    assert LocalStore().patient(second)["given_name"] == "Pedro"
    assert LocalStore().patient(first)["second_surname"] == "Lopes"
    assert LocalStore().patient(single)["second_surname"] == ""


def test_console_exposes_saved_calendar_only_locally(setup):
    from app.dashboard import app as dashboard
    from app.server import app as voice
    from fastapi.testclient import TestClient

    session = TwilioCallSession("CAcalendar", started_at=NOW)
    patient = register(session)
    search(session, patient)
    appointment = book(session, patient)["appointment_id"]
    response = TestClient(dashboard).get("/api/clinic/calendar")
    assert response.status_code == 200
    body = response.json()
    record = body["records"][0]
    assert record["appointmentId"] == appointment
    assert record["persisted"] is True
    assert record["source"] == "local"
    assert record["day"] == "2026-09-21"
    assert record["patient"] == "Ana García López"
    assert record["site"] == "Arenal Sur"
    assert record["callLogged"] is True
    assert body["sources"] == {"local": 1, "prosper": {"ok": True, "count": 0, "detail": None}}
    assert TestClient(voice).get("/api/clinic/calendar").status_code == 404


HARNESS_FEED = [
    {
        "call_id": "harness-book",
        "received_at": "2026-09-20T03:23:20.697498Z",
        "record": {
            "actions": [
                {
                    "action": "BOOK",
                    "patient_id": "P001",
                    "provider_id": "PR03",
                    "location_id": "sur",
                    "appointment_type_id": "first_visit",
                    "slot": "2026-09-22T09:00:00+02:00",
                    "policy_id": "privado",
                }
            ]
        },
    },
    {
        "call_id": "harness-move",
        "received_at": "2026-09-20T03:12:46.895273Z",
        "record": {
            "actions": [
                {
                    "action": "RESCHEDULE",
                    "appointment_id": "A001498",
                    "provider_id": "PR03",
                    "location_id": "sur",
                    "slot": "2026-10-13T13:15:00+02:00",
                    "policy_id": "mapfre",
                }
            ]
        },
    },
    {
        "call_id": "harness-cancel",
        "received_at": "2026-09-20T03:09:57.138786Z",
        "record": {
            "actions": [
                {"action": "CANCEL", "appointment_id": "A001335"},
                {"action": "NO_ACTION", "reason": "not_applicable"},
            ]
        },
    },
]
MOVE_LOG = [
    {
        "t": 1.0,
        "kind": "tool",
        "name": "find_patient",
        "args": {},
        "result": {
            "matches": [{"patient_id": "P00023", "name": "Sonia Vázquez Alonso"}],
            "count": 1,
        },
    },
    {
        "t": 2.0,
        "kind": "tool",
        "name": "list_appointments",
        "args": {},
        "result": {
            "appointments": [
                {
                    "appointment_id": "A001498",
                    "patient_id": "P00023",
                    "start_time": "2026-10-13T11:45:00+02:00",
                    "provider_id": "PR07",
                    "location_id": "norte",
                }
            ]
        },
    },
]


def test_console_calendar_merges_prosper_submissions(setup, tmp_path):
    from app.dashboard import app as dashboard
    from fastapi.testclient import TestClient

    setup.submissions_feed = deepcopy(HARNESS_FEED)
    # The persona directory: one practice case names the remote patient's DNI.
    clinic_api.PUBLIC_CASES.write_text(
        json.dumps(
            {
                "cases": [
                    {"persona": {"data": {"patient_national_id": REMOTE_PATIENT["national_id"]}}}
                ]
            }
        )
    )
    # Only the reschedule call was served from this host, so only its log is here.
    config.CALLS_DIR.mkdir(parents=True)
    (config.CALLS_DIR / "harness-move.jsonl").write_text(
        "".join(json.dumps(event) + "\n" for event in MOVE_LOG)
    )
    session = TwilioCallSession("CAcalendar", started_at=NOW)
    patient = register(session)
    search(session, patient)
    book(session, patient)

    body = TestClient(dashboard).get("/api/clinic/calendar").json()
    assert body["sources"] == {"local": 1, "prosper": {"ok": True, "count": 3, "detail": None}}
    assert [r["source"] for r in body["records"]] == ["local", "prosper", "prosper", "prosper"]
    by_call = {r["callId"]: r for r in body["records"]}
    booked = by_call["harness-book"]
    assert booked["kind"] == "BOOK" and booked["day"] == "2026-09-22"
    assert booked["patient"] == "Ana García López"  # via the persona-seeded directory
    assert (booked["provider"], booked["site"]) == ("Doctor Sáez", "Arenal Sur")
    assert booked["persisted"] is False and booked["callLogged"] is False
    moved = by_call["harness-move"]
    assert moved["kind"] == "RESCHEDULE" and moved["day"] == "2026-10-13"
    assert moved["patient"] == "Sonia Vázquez Alonso"  # from this host's call log
    assert moved["previousSlot"] == "2026-10-13T11:45:00+02:00"
    assert moved["callLogged"] is True
    cancelled = by_call["harness-cancel"]
    assert cancelled["kind"] == "CANCEL" and cancelled["day"] is None
    assert cancelled["patient"] == "Appointment A001335"
    assert cancelled["appointmentId"] == "A001335"


def test_console_calendar_survives_prosper_outage(setup, monkeypatch):
    from app.dashboard import app as dashboard
    from fastapi.testclient import TestClient

    async def down(limit=200):
        raise prosper.ProsperError(503, "maintenance")

    monkeypatch.setattr(setup, "submissions", down)
    session = TwilioCallSession("CAcalendar", started_at=NOW)
    patient = register(session)
    search(session, patient)
    book(session, patient)

    response = TestClient(dashboard).get("/api/clinic/calendar")
    assert response.status_code == 200
    body = response.json()
    assert [r["source"] for r in body["records"]] == ["local"]
    assert body["sources"]["prosper"]["ok"] is False
    assert "503" in body["sources"]["prosper"]["detail"]


@pytest.mark.parametrize("cancel", [False, True])
@pytest.mark.parametrize("existing_patient", [False, True])
def test_persisted_booking_emails_only_if_still_active(
    setup, monkeypatch, cancel, existing_patient
):
    from unittest.mock import AsyncMock

    from app import appointment_email

    monkeypatch.setattr(config, "APPOINTMENT_EMAILS_ENABLED", True)
    monkeypatch.setattr(config, "RESEND_API_KEY", "test-key")
    monkeypatch.setattr(config, "RESEND_FROM_EMAIL", "clinic@example.test")
    monkeypatch.setattr(config, "EVAL_MODE", False)
    sender = AsyncMock(return_value="test-email-id")
    monkeypatch.setattr(appointment_email, "send_message", sender)
    session = TwilioCallSession("CApersisted-email", started_at=NOW)
    if existing_patient:
        patient = LocalStore().save("seed", {**PROFILE, "action": "REGISTER"})["patient_id"]
        found = identify(session)
        assert found["verified_patient_ids"] == [patient]
    else:
        patient = register(session)
    search(session, patient)
    booked = book(session, patient)
    appointment = booked["appointment_id"]
    if existing_patient:
        assert booked["appointment_email"] == {"patient_id": patient, "status": "on_file"}
        assert session.appointment_emails == {}  # No model-supplied recipient or confirmation.
        address = PROFILE["email"]
    else:
        # A name-only registration has no email: it is asked for only to send the confirmation.
        assert booked["appointment_email"] == {"patient_id": patient, "status": "needs_address"}
        address = "ana.nueva@example.test"
        captured = run(session, "set_appointment_email", patient_id=patient, email=address)
        assert captured["email_to_read_back"] == address
        confirmed = run(session, "confirm_appointment_email", patient_id=patient, email=address)
        assert confirmed["status"] == "confirmed"
    if cancel:
        run(session, "record_cancellation", appointment_id=appointment, confirmed=True)
    asyncio.run(session.finish())
    assert sender.await_count == (0 if cancel else 1)
    if not cancel:
        sent = sender.call_args.args[0]
        assert sent["to"] == [address]
        assert ("registration at reception on arrival" in sent["text"]) is not existing_patient
    assert len(LocalStore().appointments()) == (0 if cancel else 1)


def test_local_prompt_separates_persisted_writes_from_scored_registration(setup, monkeypatch):
    monkeypatch.setattr(clinic, "_catalogue", None)
    scored = CallSession(call_id="scored-prompt").instructions()
    local = TwilioCallSession(call_id="local-prompt").instructions()
    assert "Do not book them anything." in scored
    assert "Do not book them anything." not in local
    assert "do not wait for confirmation" not in local
    assert "the new patient CAN book" in local
    assert "confirmed=true" in local
    assert "four registration groups" in scored
    assert "four registration groups" not in local
    assert "register as a new patient at reception" in local
    assert "needs_address" in local
