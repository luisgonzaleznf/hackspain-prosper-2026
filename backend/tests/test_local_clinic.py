"""Phone calls end to end against a real (temporary) clinic database: register, verify, search,
book, move, cancel, and what the console calendar then shows."""

import asyncio
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

import pytest
from app import clinic, config
from app.session import CallSession
from app.tools import TOOLS, call_tool
from integrations.local_store import LocalStore
from integrations.twilio import TwilioCallSession

from clinic_fixture import booked, patient, seeded

NOW = datetime(2026, 9, 20, 10, tzinfo=config.TZ)  # a Sunday; Monday 21 Sep is searched
DAY = "2026-09-21"
PROFILE = {
    "given_name": "Ana",
    "first_surname": "García",
    "second_surname": "López",
    "national_id": "48064716Y",
    "date_of_birth": "1988-03-14",
    "phone": "612345678",
    "email": "ana@mail.es",
    "insurer": "privado",
}
# Already on file: same name as the caller who registers, another DNI and phone.
SEEDED = patient(
    "P001",
    **{k: PROFILE[k] for k in ("given_name", "first_surname", "second_surname", "date_of_birth")},
    national_id="12345678Z",
    phone="600123456",
    insurer="privado",
    has_visited_before=False,
)
BLOCKER = patient("P09999", national_id="11111111H", phone="699000111")
# Dr. Sáez sits at Sur on Mondays 09-13. The diary leaves 09:00-10:00 and 10:30-11:00 free, so a
# 30-minute first visit fits at 09:00, 09:15, 09:30 and 10:30.
DIARY = [
    booked(f"A9{i:02d}", "P09999", "PR03", "sur", f"{DAY}T{hhmm}:00+02:00")
    for i, hhmm in enumerate(
        ["10:00", "10:15", "11:00", "11:15", "11:30", "11:45", "12:00", "12:15", "12:30", "12:45"]
    )
]
FREE = ["09:00", "09:15", "09:30", "10:30"]


def slot(at: str) -> dict:
    return {
        "provider_id": "PR03",
        "provider_name": "Dr. Martín Sáez",
        "specialty_id": "general_practice",
        "location_id": "sur",
        "appointment_type_id": "first_visit",
        "start_time": f"{DAY}T{at}:00+02:00",
        "duration_minutes": 30,
        "payable_with": ["privado"],
    }


@pytest.fixture
def setup(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "CALLS_DIR", tmp_path / "calls")
    store = seeded(patients=[SEEDED, BLOCKER], appointments=DIARY)
    # The catalogue as of the call's day, fixed for the test (the wall clock moves on).
    monkeypatch.setattr(clinic, "_catalogue", clinic.build(store, NOW.date()))
    return store


def run(session, tool_name, **args):
    return asyncio.run(call_tool(session, tool_name, args))


def register(session, **overrides):
    result = run(session, "record_registration", **{**PROFILE, "confirmed": True, **overrides})
    assert "error" not in result, result
    return result["patient_id"]


def search(session, patient_id, **extra):
    result = run(
        session,
        "search_availability",
        **{
            "patient_id": patient_id,
            "provider_id": "PR03",
            "location_id": "sur",
            "date_from": DAY,
            "date_to": DAY,
            **extra,
        },
    )
    assert "error" not in result, result
    return result


def times(result):
    return [s["slot"][11:16] for s in result["earliest_slots"]]


def book(session, patient_id, at="09:00", **overrides):
    return run(
        session,
        "record_booking",
        **{
            "patient_id": patient_id,
            "provider_id": "PR03",
            "location_id": "sur",
            "appointment_type_id": "first_visit",
            "slot": f"{DAY}T{at}:00+02:00",
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


def test_register_book_and_recall_in_new_call(setup):
    first = TwilioCallSession(call_id="CA-first", started_at=NOW)
    assert "error" in run(first, "record_registration", **PROFILE)
    patient_id = register(first)
    assert times(search(first, patient_id)) == FREE
    booking = book(first, patient_id)
    assert booking["persisted"] is True
    assert book(first, patient_id)["appointment_id"] == booking["appointment_id"]
    assert len(first.store.appointments(patient_id)) == 1
    assert times(search(first, patient_id)) == ["09:30", "10:30"]
    asyncio.run(first.finish())
    second = asyncio.run(
        TwilioCallSession.start(call_id="CA-second", from_number="+34612345678", started_at=NOW)
    )
    assert second.caller_matches[0]["patient_id"] == patient_id
    assert "error" in run(second, "list_appointments", patient_id=patient_id)
    assert identify(second)["verified_patient_ids"] == [patient_id]
    diary = run(second, "list_appointments", patient_id=patient_id)["appointments"]
    assert diary[0]["appointment_id"] == booking["appointment_id"]


def test_reschedule_cancel_and_release_local_slot(setup):
    session = TwilioCallSession(call_id="CA-move", started_at=NOW)
    patient_id = register(session)
    search(session, patient_id)
    appointment_id = book(session, patient_id)["appointment_id"]
    search(session, patient_id)
    moved = run(
        session,
        "record_reschedule",
        appointment_id=appointment_id,
        provider_id="PR03",
        location_id="sur",
        slot=slot("10:30")["start_time"],
        policy_id="privado",
        confirmed=True,
    )
    assert moved["appointment_id"] == appointment_id
    # Moving back to a former time is a real change, not a replay of an old result.
    search(session, patient_id)
    back = run(
        session,
        "record_reschedule",
        appointment_id=appointment_id,
        provider_id="PR03",
        location_id="sur",
        slot=slot("09:00")["start_time"],
        policy_id="privado",
        confirmed=True,
    )
    assert back["appointment"]["start_time"] == slot("09:00")["start_time"]
    cancelled = run(session, "record_cancellation", appointment_id=appointment_id, confirmed=True)
    assert cancelled["appointment"]["status"] == "cancelled"
    assert run(session, "list_appointments", patient_id=patient_id)["appointments"] == []
    assert times(search(session, patient_id)) == FREE


def test_seeded_patient_books_and_sees_it_in_a_later_call(setup):
    session = TwilioCallSession(call_id="CA-seeded", started_at=NOW)
    assert identify(session, SEEDED["national_id"])["verified_patient_ids"] == ["P001"]
    search(session, "P001")
    booking = book(session, "P001")
    assert booking["persisted"]
    second = TwilioCallSession(call_id="CA-seeded-2", started_at=NOW)
    identify(second, SEEDED["national_id"])
    listed = run(second, "list_appointments", patient_id="P001")["appointments"]
    assert [a["appointment_id"] for a in listed] == [booking["appointment_id"]]


def test_duplicate_registration_and_identity_guard(setup):
    first = TwilioCallSession(call_id="CA-one", started_at=NOW)
    patient_id = register(first)
    second = TwilioCallSession(call_id="CA-two", started_at=NOW)
    assert "error" in run(second, "record_registration", **PROFILE, confirmed=True)
    assert "error" in run(
        second,
        "record_registration",
        **{**PROFILE, "national_id": SEEDED["national_id"]},
        confirmed=True,
    )
    run(second, "find_patient", national_id=PROFILE["national_id"])
    search(second, patient_id)
    assert "error" in book(second, patient_id)
    assert "error" in book(second, patient_id, confirmed=False)
    assert first.store.appointments(patient_id) == []
    identify(second)
    assert book(second, patient_id)["persisted"]


def test_rechecks_availability_before_write(setup):
    session = TwilioCallSession(call_id="CA-stale", started_at=NOW)
    patient_id = register(session)
    search(session, patient_id)
    # Another caller takes 09:00 between the offer and the caller's yes.
    taken = booked("A999", "P09999", "PR03", "sur", slot("09:00")["start_time"])
    seeded(store=setup, appointments=[taken])
    assert "error" in book(session, patient_id)
    assert session.store.appointments(patient_id) == []


def test_local_age_and_referral_rules(setup):
    session = TwilioCallSession(call_id="CA-child", started_at=NOW)
    patient_id = register(session, date_of_birth="2020-01-01")
    result = search(session, patient_id)
    assert result["slots_found"] == 0
    assert result["blocked"][0]["restriction"] == "not_eligible_age"
    clinic._catalogue["specialties"][0].update(min_age_months=0, referral_required=True)
    result = search(session, patient_id)
    assert result["slots_found"] == 0
    assert result["blocked"][0]["restriction"] == "referral_required"


def test_db_serializes_two_callers_competing_for_overlapping_slots(setup):
    store = LocalStore()
    profile = {**PROFILE, "action": "REGISTER"}
    registered = store.save("create", profile)["patient"]

    def attempt(at):
        action = {
            "action": "BOOK",
            "patient_id": registered["patient_id"],
            "provider_id": "PR03",
            "location_id": "sur",
            "slot": slot(at)["start_time"],
            "policy_id": "privado",
        }
        try:
            return LocalStore().save(f"race-{at}", action, patient=registered, slot=slot(at))
        except ValueError as error:
            return {"error": str(error)}

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(attempt, ["09:00", "09:15"]))
    assert sum("appointment_id" in r for r in results) == 1
    assert len(LocalStore().appointments(registered["patient_id"])) == 1


def test_cancelling_a_seeded_appointment_frees_its_slot(setup):
    mine = booked("A001", "P001", "PR03", "sur", slot("09:00")["start_time"], "first_visit")
    seeded(store=setup, appointments=[mine])
    session = TwilioCallSession(call_id="CA-cancel", started_at=NOW)
    identify(session, SEEDED["national_id"])
    listed = run(session, "list_appointments", patient_id="P001")["appointments"]
    assert [a["appointment_id"] for a in listed] == ["A001"]
    assert "09:00" not in times(search(session, "P001"))
    result = run(session, "record_cancellation", appointment_id="A001", confirmed=True)
    assert result["persisted"]
    assert run(session, "list_appointments", patient_id="P001")["appointments"] == []
    assert times(search(session, "P001")) == FREE
    row = LocalStore().appointments("P001", include_cancelled=True)[0]
    assert (row["status"], row["call_id"], row["source"]) == ("cancelled", "CA-cancel", "local")


def test_plain_tools_keep_original_contract_and_clear_does_not_undo_saved(setup):
    assert CallSession(call_id="plain").tool_specs(TOOLS) is TOOLS
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
    patient_id = register(session)
    search(session, patient_id)
    book(session, patient_id)
    assert "error" in run(session, "clear_recorded_actions")
    run(session, "record_no_action", reason="out_of_scope")
    assert len(session.store.appointments(patient_id)) == 1


def test_two_registrations_and_explicit_correction(setup):
    session = TwilioCallSession("CAfamilies", started_at=NOW)
    first = register(session)
    second = register(session, given_name="Pedro", national_id="87654321X")
    assert first != second
    corrected = register(session, patient_id=first, email="corrected@example.test")
    assert corrected == first
    assert {p["patient_id"] for p in LocalStore().patients()} >= {first, second}
    assert LocalStore().patient(second)["given_name"] == "Pedro"
    assert LocalStore().patient(first)["email"] == "corrected@example.test"
    assert LocalStore().patient(first)["insurer_authorizations"] == []


def test_console_calendar_shows_the_diary_window_and_call_bookings(setup):
    from app.dashboard import app as dashboard
    from app.server import app as voice
    from fastapi.testclient import TestClient

    seeded(
        store=setup,
        absences=[("PR05", "2026-09-20", "2026-09-22", None, None, "congress")],
        closures=[("2026-10-12", None, "Fiesta Nacional")],
    )
    session = TwilioCallSession("CAcalendar", started_at=NOW)
    patient_id = register(session)
    search(session, patient_id)
    appointment = book(session, patient_id)["appointment_id"]
    client = TestClient(dashboard)
    body = client.get("/api/clinic/calendar", params={"from": DAY, "to": DAY}).json()
    assert (body["from"], body["to"]) == (DAY, DAY)
    assert {p["id"] for p in body["providers"]} >= {"PR03", "PR05"}
    assert {"id": "sur", "name": "Arenal Sur"} in body["locations"]
    assert body["absences"] == [
        {
            "providerId": "PR05",
            "start": "2026-09-20",
            "end": "2026-09-22",
            "startTime": None,
            "endTime": None,
            "reason": "congress",
        }
    ]
    assert body["closures"] == []  # 12 Oct is outside this window
    assert len(body["records"]) == len(DIARY) + 1
    record = next(r for r in body["records"] if r["appointmentId"] == appointment)
    assert record["persisted"] is True
    assert record["source"] == "call"
    assert record["callId"] == "CAcalendar"
    assert record["day"] == DAY
    assert record["patient"] == "Ana García López"
    assert (record["provider"], record["providerId"], record["site"]) == (
        "Dr. Martín Sáez",
        "PR03",
        "Arenal Sur",
    )
    assert (record["end"], record["durationMinutes"]) == (f"{DAY}T09:30:00+02:00", 30)
    assert (record["appointmentType"], record["status"], record["kind"]) == (
        "first_visit",
        "booked",
        "BOOK",
    )
    assert record["callLogged"] is True
    diary = next(r for r in body["records"] if r["appointmentId"] == "A900")
    assert (diary["source"], diary["callId"], diary["callLogged"]) == ("diary", None, False)
    assert [r["slot"] for r in body["records"]] == sorted(r["slot"] for r in body["records"])
    later = client.get("/api/clinic/calendar", params={"from": "2026-10-12", "to": "2026-10-12"})
    assert later.json()["closures"] == [
        {"date": "2026-10-12", "locationId": None, "name": "Fiesta Nacional"}
    ]
    assert TestClient(voice).get("/api/clinic/calendar").status_code == 404


def test_console_calendar_tolerates_sparse_rows_and_bad_windows(setup):
    from app.dashboard import app as dashboard
    from fastapi.testclient import TestClient

    sparse = booked("A500", "P001", "PR03", "sur", f"{DAY}T09:00:00+02:00", "first_visit")
    for key in ("updated_at", "call_id", "provider_name"):
        sparse.pop(key)
    cancelled = {**sparse, "appointment_id": "A501", "status": "cancelled"}
    seeded(store=setup, appointments=[sparse, cancelled])
    client = TestClient(dashboard)
    body = client.get("/api/clinic/calendar", params={"from": DAY, "to": DAY}).json()
    rows = {r["appointmentId"]: r for r in body["records"]}
    assert rows["A500"]["recordedAt"] is None
    assert rows["A500"]["provider"] == "Dr. Martín Sáez"
    assert (rows["A501"]["kind"], rows["A501"]["status"]) == ("CANCEL", "cancelled")
    for window in (
        {"from": "2026-09-01", "to": "2026-12-31"},  # over 62 days
        {"from": "2026-09-22", "to": DAY},
        {"from": "tomorrow"},
    ):
        assert client.get("/api/clinic/calendar", params=window).status_code == 422
    assert client.get("/api/clinic/calendar").status_code == 200  # today-7 .. today+35


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
    sender = AsyncMock(return_value="test-email-id")
    monkeypatch.setattr(appointment_email, "send_message", sender)
    session = TwilioCallSession("CApersisted-email", started_at=NOW)
    if existing_patient:
        patient_id = register(TwilioCallSession("CAearlier-registration", started_at=NOW))
        found = identify(session)
        assert found["verified_patient_ids"] == [patient_id]
    else:
        patient_id = register(session)
    search(session, patient_id)
    booking = book(session, patient_id)
    appointment = booking["appointment_id"]
    assert booking["appointment_email"] == {"patient_id": patient_id, "status": "on_file"}
    assert session.appointment_emails == {}  # No model-supplied recipient or confirmation.
    if cancel:
        run(session, "record_cancellation", appointment_id=appointment, confirmed=True)
    asyncio.run(session.finish())
    assert sender.await_count == (0 if cancel else 1)
    if not cancel:
        assert sender.call_args.args[0]["to"] == [PROFILE["email"]]
    assert len(LocalStore().appointments(patient_id)) == (0 if cancel else 1)


def test_local_prompt_separates_persisted_writes_from_staged_registration(setup, monkeypatch):
    monkeypatch.setattr(clinic, "_catalogue", None)
    staged = CallSession(call_id="staged-prompt").instructions()
    local = TwilioCallSession(call_id="local-prompt").instructions()
    assert "Do not book them anything." in staged
    assert "Do not book them anything." not in local
    assert "do not wait for confirmation" not in local
    assert "the new patient CAN book" in local
    assert "confirmed=true" in local


def test_a_hyphenated_surname_is_verified_from_its_spoken_words(setup):
    chart = patient(
        "P002",
        given_name="Luis",
        first_surname="García-Moreno",
        second_surname="Pérez",
        national_id="22222222J",
        date_of_birth="1970-01-01",
    )
    seeded(store=setup, patients=[chart])
    session = TwilioCallSession(call_id="CA-hyphen", started_at=NOW)
    found = run(session, "find_patient", name="Luis García Moreno", date_of_birth="1970-01-01")
    assert found["verified_patient_ids"] == ["P002"]
