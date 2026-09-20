"""Exercise browser/Twilio finalizers with real tool validation and mocked Resend HTTP."""

import asyncio
import json
from datetime import datetime

import httpx
import pytest
from app import appointment_email, clinic, config, prosper
from app.session import CallSession
from app.tools import TOOLS, call_tool, tools_for_session
from integrations.twilio import TwilioCallSession

SLOT = {
    "provider_id": "PR01",
    "provider_name": "Dra. Carmen Ortiz Vidal",
    "location_id": "centro",
    "appointment_type_id": "review",
    "start_time": "2026-09-21T11:00:00+02:00",
    "payable_with": ["mapfre"],
}
BOOK = {
    "patient_id": "P1",
    "provider_id": "PR01",
    "location_id": "centro",
    "appointment_type_id": "review",
    "slot": SLOT["start_time"],
    "policy_id": "mapfre",
}
EMAIL = {"patient_id": "P1", "email": "judge+demo@example.org"}


def run(coro):
    return asyncio.run(coro)


class TwilioEmailFinalizer(TwilioCallSession):
    # Isolate the email finalizer's staged-proposal contract. Persistent phone writes
    # require confirmation, identity and fresh availability and are exercised in
    # test_local_clinic.py, including email delivery after a persisted booking.
    execute_tool = CallSession.execute_tool
    stage = CallSession.stage
    finish_demo = CallSession.finish_demo


@pytest.fixture(params=[CallSession, TwilioEmailFinalizer], ids=["browser", "twilio-finalizer"])
def setup(tmp_path, monkeypatch, request):
    monkeypatch.setattr(config, "CALLS_DIR", tmp_path)
    monkeypatch.setattr(config, "APPOINTMENT_EMAILS_ENABLED", True)
    monkeypatch.setattr(config, "EVAL_MODE", False)
    monkeypatch.setattr(config, "RESEND_API_KEY", "test-secret-never-log")
    monkeypatch.setattr(config, "RESEND_FROM_EMAIL", "Rosario <citas@example.org>")
    monkeypatch.setattr(
        clinic,
        "_catalogue",
        {
            "clinic_name": "Clínica Arenal",
            "locations": [
                {"id": "centro", "name": "Arenal Centro", "address": "Calle del Arenal 12, Madrid"}
            ],
        },
    )
    session = request.param(
        call_id="email-test", started_at=datetime(2026, 9, 20, tzinfo=config.TZ), demo_mode=True
    )
    session.remember_patients(
        [
            {
                "patient_id": "P1",
                "given_name": "Ana",
                "first_surname": "García",
                "second_surname": "López",
                "national_id": "48064716Y",
            },
            {
                "patient_id": "P2",
                "given_name": "Luis",
                "first_surname": "López",
                "second_surname": "García",
            },
        ]
    )
    session.remember_slots([SLOT, SLOT | {"start_time": "2026-09-22T12:30:00+02:00"}])
    session.remember_appointments(
        [
            {
                "appointment_id": "A1",
                "patient_id": "P1",
                "start_time": "2026-09-21T09:00:00+02:00",
            }
        ]
    )
    operations = []
    requests = []
    behavior = {"submit_status": 200, "email_status": 200, "email_body": {"id": "re-test-id"}}

    class Clinic:
        async def submit(self, payload):
            operations.append(("submit", payload))
            return behavior["submit_status"], {"record": {"actions": [payload]}}

    def resend(request):
        # The proposal is on disk before requesting an email, on either demo transport.
        assert '"kind": "demo_outcome"' in (tmp_path / "email-test.jsonl").read_text()
        assert str(request.url) == "https://api.resend.com/emails"
        assert request.headers["Authorization"] == "Bearer test-secret-never-log"
        requests.append(request)
        operations.append(("email", json.loads(request.content)))
        if behavior.get("timeout"):
            raise httpx.ReadTimeout("do not log test-secret-never-log", request=request)
        return httpx.Response(behavior["email_status"], json=behavior["email_body"])

    client_type = httpx.AsyncClient
    monkeypatch.setattr(
        httpx,
        "AsyncClient",
        lambda **kwargs: client_type(transport=httpx.MockTransport(resend), **kwargs),
    )
    monkeypatch.setattr(prosper, "client", Clinic)
    return session, requests, operations, behavior


def book_and_confirm(session, *, patient_id="P1", email="judge+demo@example.org"):
    assert "error" not in run(
        call_tool(session, "record_booking", BOOK | {"patient_id": patient_id})
    )
    args = {"patient_id": patient_id, "email": email}
    assert run(call_tool(session, "set_appointment_email", args))["status"] == "needs_confirmation"
    assert run(call_tool(session, "confirm_appointment_email", args))["status"] == "confirmed"


def test_final_bookings_only_after_local_persistence_once(setup):
    session, requests, operations, _ = setup
    session.patients["P1"]["email"] = "chart@example.org"
    booked = run(call_tool(session, "record_booking", BOOK))
    assert booked["appointment_email"] == {"patient_id": "P1", "status": "on_file"}
    run(call_tool(session, "record_booking", BOOK | {"slot": "2026-09-22T12:30:00+02:00"}))
    book_and_confirm(session, patient_id="P2", email="relative@example.org")
    assert requests == []
    results = run(session.finish())
    assert len(results) == 2
    assert [op[0] for op in operations] == ["email", "email"]
    message = json.loads(requests[0].content)
    assert message["from"] == "Rosario <citas@example.org>"
    assert message["to"] == ["chart@example.org"]
    assert results[0]["recipient_source"] == "patient_record"
    assert results[1]["recipient_source"] == "caller_confirmed"
    assert "22/09/2026 · 12:30" in message["text"]
    assert "21/09/2026 · 11:00" not in message["text"]
    assert "Calle del Arenal 12, Madrid" in message["text"]
    assert "Dra. Carmen Ortiz Vidal" in message["text"]
    assert "48064716Y" not in message["text"]
    assert "mapfre" not in message["text"]
    assert "diary was not changed" in message["text"]
    assert run(session.finish()) == []
    assert len(requests) == 2


def test_move_uses_looked_up_patient_and_new_time(setup):
    session, requests, _, _ = setup
    session.patients["P1"]["email"] = "chart@example.org"
    session.patients["P2"]["email"] = "other-patient@example.org"
    args = {
        key: value
        for key, value in BOOK.items()
        if key not in ("patient_id", "appointment_type_id")
    }
    assert "error" not in run(
        call_tool(session, "record_reschedule", args | {"appointment_id": "A1"})
    )
    run(session.finish())
    message = json.loads(requests[0].content)
    assert "Appointment moved" in message["subject"]
    assert "21/09/2026 · 11:00" in message["text"]
    assert "21/09/2026 · 09:00" in message["text"]
    assert message["to"] == ["chart@example.org"]


@pytest.mark.parametrize("capture", [False, True])
@pytest.mark.parametrize("on_file", [None, "", "incomplete@"])
def test_missing_or_invalid_chart_email_requires_confirmed_address(setup, capture, on_file):
    session, requests, _, _ = setup
    session.patients["P1"]["email"] = on_file
    booked = run(call_tool(session, "record_booking", BOOK))
    assert booked["appointment_email"]["status"] == "needs_address"
    if capture:
        run(call_tool(session, "set_appointment_email", EMAIL))
    run(session.finish())
    assert requests == []


def test_chart_address_wins_over_model_supplied_recipient(setup):
    session, requests, _, _ = setup
    book_and_confirm(session)
    # A record refreshed after capture remains authoritative, even with stale model state.
    session.remember_patients([session.patients["P1"] | {"email": " Chart@Example.ORG "}])
    run(session.finish())
    assert json.loads(requests[0].content)["to"] == ["Chart@example.org"]


def test_email_tools_cannot_override_chart_address(setup):
    session, requests, _, _ = setup
    session.patients["P1"]["email"] = "chart@example.org"
    run(call_tool(session, "record_booking", BOOK))
    assert run(call_tool(session, "set_appointment_email", EMAIL))["status"] == "on_file"
    assert "error" in run(call_tool(session, "confirm_appointment_email", EMAIL))
    assert session.appointment_emails == {}
    run(session.finish())
    assert json.loads(requests[0].content)["to"] == ["chart@example.org"]


def test_each_patient_uses_their_own_chart_unless_they_decline(setup):
    session, requests, _, _ = setup
    for patient_id in ("P1", "P2"):
        session.patients[patient_id]["email"] = f"{patient_id}@example.org"
        run(call_tool(session, "record_booking", BOOK | {"patient_id": patient_id}))
    run(call_tool(session, "set_appointment_email", EMAIL | {"email": ""}))
    # Changing P1's slot must not forget their opt-out.
    booked = run(call_tool(session, "record_booking", BOOK | {"slot": "2026-09-22T12:30:00+02:00"}))
    assert booked["appointment_email"]["status"] == "declined"
    run(session.finish())
    assert len(requests) == 1
    assert json.loads(requests[0].content)["to"] == ["P2@example.org"]


def test_lookup_without_a_booking_never_sends_email(setup):
    session, requests, _, _ = setup
    session.patients["P1"]["email"] = "chart@example.org"
    run(session.finish())
    assert requests == []


def test_requires_separate_capture_before_confirmation(setup):
    session, _, _, _ = setup
    assert "error" in run(call_tool(session, "set_appointment_email", EMAIL))
    run(call_tool(session, "record_booking", BOOK))
    assert "error" in run(call_tool(session, "confirm_appointment_email", EMAIL))
    result = run(
        call_tool(
            session, "set_appointment_email", EMAIL | {"email": " Judge.Name +demo @Example.ORG "}
        )
    )
    assert result["email_to_read_back"] == "Judge.Name+demo@example.org"
    assert "error" in run(call_tool(session, "confirm_appointment_email", EMAIL))


@pytest.mark.parametrize("correction", ["corrected@example.org", "incomplete@", ""])
def test_any_correction_or_withdrawal_invalidates_previous_confirmation(setup, correction):
    session, requests, _, _ = setup
    book_and_confirm(session)
    run(call_tool(session, "set_appointment_email", EMAIL | {"email": correction}))
    run(session.finish())
    assert requests == []


@pytest.mark.parametrize("address", ["corrected@example.org", "incomplete@"])
def test_mismatching_confirmation_also_invalidates_old_address(setup, address):
    session, requests, _, _ = setup
    book_and_confirm(session)
    assert "error" in run(
        call_tool(session, "confirm_appointment_email", EMAIL | {"email": address})
    )
    run(session.finish())
    assert requests == []


def test_corrected_address_needs_fresh_confirmation(setup):
    session, requests, _, _ = setup
    book_and_confirm(session)
    corrected = EMAIL | {"email": "corrected@example.org"}
    run(call_tool(session, "set_appointment_email", corrected))
    assert "error" in run(call_tool(session, "confirm_appointment_email", EMAIL))
    run(call_tool(session, "confirm_appointment_email", corrected))
    run(session.finish())
    assert json.loads(requests[0].content)["to"] == [corrected["email"]]


@pytest.mark.parametrize(
    "address",
    [
        "a@@example.org",
        "a@localhost",
        ".a@example.org",
        "a..b@example.org",
        "a@-example.org",
        "a@example.org,b@example.org",
        "A <a@example.org>",
        "a\n@example.org",
        "a\r@example.org",
        "a@exam_ple.org",
    ],
)
def test_rejects_malformed_or_multiple_addresses(address):
    with pytest.raises(ValueError):
        appointment_email.normalize_address(address)


@pytest.mark.parametrize("action", ["clear", "cancel", "no_action", "escalate"])
def test_superseded_or_withdrawn_appointment_never_gets_email(setup, action):
    session, requests, _, _ = setup
    if action == "cancel":
        run(
            call_tool(
                session,
                "record_reschedule",
                {
                    "appointment_id": "A1",
                    "provider_id": "PR01",
                    "location_id": "centro",
                    "slot": SLOT["start_time"],
                    "policy_id": "mapfre",
                },
            )
        )
        run(call_tool(session, "set_appointment_email", EMAIL))
        run(call_tool(session, "confirm_appointment_email", EMAIL))
        run(call_tool(session, "record_cancellation", {"appointment_id": "A1"}))
    else:
        book_and_confirm(session)
        if action == "clear":
            run(call_tool(session, "clear_recorded_actions", {"patient_id": "P1"}))
        else:
            name = "record_escalation" if action == "escalate" else "record_no_action"
            run(call_tool(session, name, {"reason": "out_of_scope"}))
    session.patients["P1"]["email"] = "chart@example.org"
    run(session.finish())
    assert requests == []


def test_selective_clear_preserves_other_patients_email(setup):
    session, requests, _, _ = setup
    book_and_confirm(session)
    book_and_confirm(session, patient_id="P2", email="relative@example.org")
    run(call_tool(session, "clear_recorded_actions", {"patient_id": "P1"}))
    run(session.finish())
    assert len(requests) == 1
    assert json.loads(requests[0].content)["to"] == ["relative@example.org"]


@pytest.mark.parametrize("status", [0, 200, 409, 404, 410, 422, 500])
def test_scored_calls_never_offer_or_send_email_even_with_stale_consent(setup, status, monkeypatch):
    session, requests, _, behavior = setup
    book_and_confirm(session)
    scored = CallSession(
        call_id="scored",
        actions=session.actions,
        appointment_emails=session.appointment_emails,
        patients={"P1": session.patients["P1"] | {"email": "chart@example.org"}},
    )
    assert tools_for_session(scored) is TOOLS
    monkeypatch.setattr(clinic, "_catalogue", None)
    assert "APPOINTMENT EMAIL" not in scored.instructions()
    assert "error" in run(call_tool(scored, "set_appointment_email", EMAIL))
    assert "error" in run(call_tool(scored, "confirm_appointment_email", EMAIL))
    behavior["submit_status"] = status
    assert run(scored.finish())[0]["status"] == status
    assert run(appointment_email.send_for_actions(scored, scored.actions)) == []
    assert requests == []


def test_repeated_demo_send_uses_idempotency(setup):
    session, requests, _, _ = setup
    book_and_confirm(session)
    run(session.finish())
    key = requests[0].headers["Idempotency-Key"]
    assert key.startswith("appointment/")
    assert len(key) <= 256
    run(appointment_email.send_for_actions(session, session.actions))
    assert len(requests) == 1
    # Replaying the same finalized message uses the same provider key and exact payload.
    session.sent_appointment_emails.clear()
    run(appointment_email.send_for_actions(session, session.actions))
    assert requests[1].headers["Idempotency-Key"] == key
    assert requests[1].content == requests[0].content


@pytest.mark.parametrize("failure", ["http", "timeout", "malformed"])
def test_email_failure_cannot_erase_appointment_or_expose_secrets(setup, failure):
    session, requests, _, behavior = setup
    book_and_confirm(session)
    if failure == "http":
        behavior["email_status"] = 403
    elif failure == "timeout":
        behavior["timeout"] = True
    else:
        behavior["email_body"] = {}
    assert run(session.finish())[0]["status"] == "failed"
    assert session.actions == [{"action": "BOOK", **BOOK}]
    assert len(requests) == 1
    log = (config.CALLS_DIR / "email-test.jsonl").read_text()
    assert "appointment_email.failed" in log
    assert "call_ended" in log
    assert config.RESEND_API_KEY not in log


def test_demo_finalizes_locally_and_sends_without_submitting_to_prosper(setup):
    session, requests, operations, _ = setup
    book_and_confirm(session)
    assert run(session.finish_demo())[0]["email_id"] == "re-test-id"
    assert [op[0] for op in operations] == ["email"]
    message = json.loads(requests[0].content)
    assert "Demo" in message["subject"]
    assert "diary was not changed" in message["text"]
    assert run(session.finish_demo()) == []
    assert run(session.finish()) == []
    assert len(requests) == 1
    assert "error" in run(call_tool(session, "set_appointment_email", EMAIL))


@pytest.mark.parametrize(
    "setting,value",
    [
        ("APPOINTMENT_EMAILS_ENABLED", False),
        ("EVAL_MODE", True),
        ("RESEND_API_KEY", ""),
        ("RESEND_FROM_EMAIL", ""),
    ],
)
def test_disabled_or_unconfigured_sends_nothing_and_does_not_offer_email(
    setup, monkeypatch, setting, value
):
    session, requests, _, _ = setup
    book_and_confirm(session)
    monkeypatch.setattr(config, setting, value)
    monkeypatch.setattr(clinic, "_catalogue", None)
    assert "APPOINTMENT EMAIL" not in session.instructions()
    assert tools_for_session(session) is TOOLS
    assert "error" in run(call_tool(session, "set_appointment_email", EMAIL))
    run(session.finish())
    assert requests == []


def test_email_escapes_lookup_text_and_uses_madrid_time(setup):
    session, requests, _, _ = setup
    session.patients["P1"]["given_name"] = "<script>alert(1)</script>"
    # The offered UTC timestamp must be rendered as the same Madrid appointment.
    utc_slot = SLOT | {"start_time": "2026-09-21T09:00:00+00:00"}
    session.remember_slots([utc_slot])
    book_and_confirm(session)
    run(session.finish_demo())
    message = json.loads(requests[0].content)
    assert "<script>" not in message["html"]
    assert "&lt;script&gt;" in message["html"]
    assert "21/09/2026 · 11:00" in message["text"]
