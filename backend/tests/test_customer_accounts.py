import asyncio
import json
import sqlite3

import httpx
import pytest
from app import clinic, config
from app.demo.state import build_action_evidence
from app.session import CallSession
from app.tools import TOOLS, call_tool, tools_for_session
from integrations import local_clinic
from integrations.twilio import TwilioCallSession

DETAILS = {"name": "Alex Test", "email": "alex+demo@example.org"}


def run(coro):
    return asyncio.run(coro)


@pytest.fixture(params=[CallSession, TwilioCallSession], ids=["browser", "twilio"])
def setup(tmp_path, monkeypatch, request):
    monkeypatch.setattr(config, "CALLS_DIR", tmp_path / "calls")
    monkeypatch.setattr(config, "CUSTOMER_DB_PATH", tmp_path / "private" / "customers.sqlite3")
    monkeypatch.setattr(config, "APPOINTMENT_EMAILS_ENABLED", True)
    monkeypatch.setattr(config, "RESEND_API_KEY", "test-secret")
    monkeypatch.setattr(config, "RESEND_FROM_EMAIL", "Rosario <onboarding@resend.dev>")
    monkeypatch.setattr(clinic, "_catalogue", None)
    requests = []
    behavior = {"status": 200}

    def resend(request):
        # The customer must already be committed before Resend is contacted.
        with sqlite3.connect(config.CUSTOMER_DB_PATH) as db:
            assert db.execute("SELECT count(*) FROM customers").fetchone()[0] == 1
        assert request.headers["Idempotency-Key"].startswith("customer/")
        requests.append(request)
        return httpx.Response(behavior["status"], json={"id": "welcome-email-id"})

    client_type = httpx.AsyncClient
    monkeypatch.setattr(
        httpx,
        "AsyncClient",
        lambda **kwargs: client_type(transport=httpx.MockTransport(resend), **kwargs),
    )

    def no_clinic(*_, **__):
        pytest.fail("Customer enrollment must not read the clinic")

    monkeypatch.setattr(local_clinic, "client", no_clinic)
    return request.param(call_id="customer-test", demo_mode=True), requests, behavior


def confirm_account(session, details=None):
    details = details or DETAILS
    captured = run(call_tool(session, "prepare_customer_account", details))
    assert captured["status"] == "needs_confirmation"
    confirmed = run(
        call_tool(session, "confirm_customer_account", {"email": captured["email_to_read_back"]})
    )
    assert confirmed["status"] == "confirmed"


def test_real_database_write_then_welcome_email_once(setup):
    session, requests, _ = setup
    confirm_account(session)
    assert not config.CUSTOMER_DB_PATH.exists()
    assert not requests
    result = run(session.finish())[0]
    assert result["status"] == "created"
    assert result["email_status"] == "accepted"
    with sqlite3.connect(config.CUSTOMER_DB_PATH) as db:
        row = db.execute("SELECT id, name, email FROM customers").fetchone()
    assert row == (result["account_id"], DETAILS["name"], DETAILS["email"])
    payload = json.loads(requests[0].content)
    assert payload["to"] == [DETAILS["email"]]
    assert result["account_id"] in payload["text"]
    assert "No medical appointment" in payload["text"]
    evidence = build_action_evidence(session)[0]
    assert evidence.label == "Customer account saved"
    assert ("Email", "Accepted by Resend") in evidence.fields
    assert run(session.finish_demo()) == []
    assert len(requests) == 1


def test_existing_customer_survives_new_session_without_duplicate_or_overwrite(setup):
    session, requests, _ = setup
    confirm_account(session)
    original = run(session.finish_demo())[0]
    next_session = CallSession(call_id="next-customer-call", demo_mode=True)
    confirm_account(
        next_session, {"name": "Different supplied name", "email": DETAILS["email"].upper()}
    )
    repeated = run(next_session.finish_demo())[0]
    assert repeated["status"] == "existing"
    assert repeated["account_id"] == original["account_id"]
    with sqlite3.connect(config.CUSTOMER_DB_PATH) as db:
        assert db.execute("SELECT name FROM customers").fetchall() == [(DETAILS["name"],)]
    assert len(requests) == 2


@pytest.mark.parametrize(
    "change", ["unconfirmed", "corrected", "invalid", "withdrawn", "wrong_confirmation"]
)
def test_no_account_or_email_without_current_consent(setup, change):
    session, requests, _ = setup
    if change == "unconfirmed":
        run(call_tool(session, "prepare_customer_account", DETAILS))
    else:
        confirm_account(session)
        if change == "wrong_confirmation":
            run(call_tool(session, "confirm_customer_account", {"email": "other@example.org"}))
        else:
            email = {"corrected": "other@example.org", "invalid": "broken@", "withdrawn": ""}[
                change
            ]
            run(call_tool(session, "prepare_customer_account", DETAILS | {"email": email}))
    assert run(session.finish_demo()) == []
    assert not config.CUSTOMER_DB_PATH.exists()
    assert not requests


def test_corrected_email_is_saved_only_after_new_confirmation(setup):
    session, requests, _ = setup
    confirm_account(session)
    confirm_account(session, DETAILS | {"email": "corrected@example.org"})
    run(session.finish_demo())
    assert json.loads(requests[0].content)["to"] == ["corrected@example.org"]
    with sqlite3.connect(config.CUSTOMER_DB_PATH) as db:
        assert db.execute("SELECT email FROM customers").fetchall() == [("corrected@example.org",)]


def test_database_failure_prevents_email(setup, monkeypatch, tmp_path):
    session, requests, _ = setup
    monkeypatch.setattr(config, "CUSTOMER_DB_PATH", tmp_path)  # directory, not a database file
    confirm_account(session)
    result = run(session.finish_demo())[0]
    assert result["status"] == "failed"
    assert result["email_status"] == "not_sent"
    assert not requests
    assert build_action_evidence(session)[0].label == "Customer account could not be saved"


def test_email_rejection_preserves_customer_and_reports_failure(setup):
    session, _, behavior = setup
    behavior["status"] = 403
    confirm_account(session)
    result = run(session.finish_demo())[0]
    assert result["status"] == "created"
    assert result["email_status"] == "failed"
    assert result["http_status"] == 403
    with sqlite3.connect(config.CUSTOMER_DB_PATH) as db:
        assert db.execute("SELECT count(*) FROM customers").fetchone()[0] == 1
    assert ("Email", "Not sent; check the trace") in build_action_evidence(session)[0].fields
    assert "test-secret" not in (config.CALLS_DIR / "customer-test.jsonl").read_text()


def test_non_demo_sessions_cannot_create_demo_customers(setup):
    _, requests, _ = setup
    plain = CallSession(call_id="plain")
    assert tools_for_session(plain) is TOOLS
    assert "HUMAN DEMO CUSTOMER ACCOUNTS" not in plain.instructions()
    assert "error" in run(call_tool(plain, "prepare_customer_account", DETAILS))
    assert not config.CUSTOMER_DB_PATH.exists()
    assert not requests


def test_human_demo_has_account_tools_and_instructions(setup):
    session, _, _ = setup
    assert "prepare_customer_account" in {tool["name"] for tool in tools_for_session(session)}
    assert "HUMAN DEMO CUSTOMER ACCOUNTS" in session.instructions()


def test_disabled_feature_refuses_account_creation(setup, monkeypatch):
    session, requests, _ = setup
    monkeypatch.setattr(config, "APPOINTMENT_EMAILS_ENABLED", False)
    assert tools_for_session(session) is TOOLS
    assert "error" in run(call_tool(session, "prepare_customer_account", DETAILS))
    assert not requests
