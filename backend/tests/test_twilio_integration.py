import asyncio
import json
from unittest.mock import AsyncMock
from xml.etree.ElementTree import fromstring

import pytest
from app import clinic, config
from app.server import app
from app.session import CallSession
from app.tools import register_pipecat_tools, tools_for_session
from fastapi.testclient import TestClient
from integrations import twilio
from integrations.twilio import PHONE_NUMBER, TwilioCallSession

ACCOUNT_SID = "AC" + "0" * 32


@pytest.fixture(autouse=True)
def twilio_account(monkeypatch):
    monkeypatch.setattr(twilio, "ACCOUNT_SID", ACCOUNT_SID)


def test_webhook_passes_caller_id_to_secure_bidirectional_stream():
    client = TestClient(app, base_url="https://clinic.example")
    response = client.post(
        "/integrations/twilio/voice",
        data={
            "AccountSid": ACCOUNT_SID,
            "To": PHONE_NUMBER,
            "From": "+34600123456",
            "CallSid": "CA123",
        },
    )
    assert response.status_code == 200
    xml = fromstring(response.text)
    stream = xml.find("Connect/Stream")
    assert stream is not None
    assert stream.attrib["url"] == "wss://clinic.example/integrations/twilio/ws"
    assert {p.attrib["name"]: p.attrib["value"] for p in stream} == {
        "from_number": "+34600123456",
        "to_number": PHONE_NUMBER,
    }
    assert xml.find("Hangup") is not None


def test_webhook_rejects_missing_call_metadata():
    client = TestClient(app)
    assert client.post("/integrations/twilio/voice", data={}).status_code == 400
    assert (
        client.post(
            "/integrations/twilio/voice", data={"AccountSid": ACCOUNT_SID, "To": PHONE_NUMBER}
        ).status_code
        == 400
    )


def test_phone_demo_records_outcome_without_submitting_to_scorer(monkeypatch, tmp_path):
    monkeypatch.setattr(config, "CALLS_DIR", tmp_path)
    session = TwilioCallSession(call_id="CA123")
    session.actions = [{"action": "NO_ACTION", "reason": "out_of_scope"}]
    submit = AsyncMock()
    monkeypatch.setattr(session, "_submit_once_retrying", submit)
    assert asyncio.run(session.finish()) == []
    assert asyncio.run(session.finish()) == []
    submit.assert_not_called()
    events = [json.loads(line) for line in (tmp_path / "CA123.jsonl").read_text().splitlines()]
    assert [event["kind"] for event in events] == ["demo_outcome", "call_ended"]
    assert all(event["submitted"] is False for event in events)
    assert all(event["source"] == "twilio" for event in events)
    assert events[-1]["actions"] == session.actions


def test_twilio_start_enables_human_tools_for_gptlive_only_when_configured(monkeypatch, tmp_path):
    monkeypatch.setattr(config, "CALLS_DIR", tmp_path)
    monkeypatch.setattr(clinic, "catalogue", AsyncMock(return_value={}))
    monkeypatch.setattr(config, "APPOINTMENT_EMAILS_ENABLED", True)
    monkeypatch.setattr(config, "RESEND_API_KEY", "test-secret")
    monkeypatch.setattr(config, "RESEND_FROM_EMAIL", "Rosario <citas@example.org>")
    monkeypatch.setattr(config, "EVAL_MODE", False)

    session = asyncio.run(TwilioCallSession.start(call_id="CA123"))
    assert session.demo_mode is True
    assert "APPOINTMENT EMAIL" in session.instructions()
    assert "HUMAN DEMO CUSTOMER ACCOUNTS" in session.instructions()
    registered = {}

    class LLM:
        def register_function(self, name, handler):
            registered[name] = handler

    register_pipecat_tools(LLM(), session)
    assert set(registered) == {tool["name"] for tool in session.tool_specs(tools_for_session(session))}
    assert {"set_appointment_email", "confirm_customer_account"} <= registered.keys()
    scored = asyncio.run(CallSession.start(call_id="scored"))
    assert scored.demo_mode is False
    assert "set_appointment_email" not in {tool["name"] for tool in tools_for_session(scored)}
    monkeypatch.setattr(config, "EVAL_MODE", True)
    assert "set_appointment_email" not in {tool["name"] for tool in session.tool_specs(tools_for_session(session))}
