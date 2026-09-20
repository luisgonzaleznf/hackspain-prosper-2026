from xml.etree.ElementTree import fromstring

import pytest
from app.server import app
from fastapi.testclient import TestClient
from integrations import twilio

ACCOUNT_SID = "AC" + "0" * 32
PHONE_NUMBER = "+15717135999"


@pytest.fixture(autouse=True)
def twilio_account(monkeypatch):
    monkeypatch.setattr(twilio, "ACCOUNT_SID", ACCOUNT_SID)
    monkeypatch.setattr(twilio, "PHONE_NUMBER", PHONE_NUMBER)

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


def test_twiml_alias_uses_the_same_secure_stream():
    client = TestClient(app, base_url="https://clinic.example")
    response = client.post(
        "/twiml",
        data={"AccountSid": ACCOUNT_SID, "To": PHONE_NUMBER, "From": "+34600123456", "CallSid": "CA123"},
    )
    assert response.status_code == 200
    stream = fromstring(response.text).find("Connect/Stream")
    assert stream is not None
    assert stream.attrib["url"] == "wss://clinic.example/integrations/twilio/ws"
