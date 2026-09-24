"""Walk the browser account scenario through disconnect and the saved receipt."""

import asyncio
import sqlite3
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from app import appointment_email, clinic, config
from app.demo import app as demo_app
from app.demo import bot, state
from app.demo import settings as store
from app.demo.app import register_demo_routes
from app.demo.scenarios import get_scenario
from app.tools import call_tool
from fastapi import FastAPI
from fastapi.testclient import TestClient
from integrations import local_clinic


@pytest.fixture
def demo(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "CALLS_DIR", tmp_path / "calls")
    monkeypatch.setattr(store, "SETTINGS_PATH", tmp_path / "voice-settings.json")
    monkeypatch.setattr(config, "CUSTOMER_DB_PATH", tmp_path / "customers.sqlite3")
    monkeypatch.setattr(config, "APPOINTMENT_EMAILS_ENABLED", True)
    monkeypatch.setattr(config, "RESEND_API_KEY", "test-secret")
    monkeypatch.setattr(config, "RESEND_FROM_EMAIL", "Rosario <citas@example.org>")
    monkeypatch.setattr(clinic, "catalogue", AsyncMock(return_value={}))
    registry = state.DemoSessionRegistry()
    monkeypatch.setattr(state, "registry", registry)
    monkeypatch.setattr(demo_app, "registry", registry)
    monkeypatch.setattr(state, "_LEDGER_PATH", tmp_path / "ledger.jsonl")
    monkeypatch.setattr(
        local_clinic, "client", Mock(side_effect=AssertionError("Unexpected clinic read"))
    )
    app = FastAPI()
    register_demo_routes(app)
    return TestClient(app)


def test_browser_account_disconnect_persists_then_sends_and_exposes_receipt(demo, monkeypatch):
    call_id = "11111111-1111-4111-8111-111111111111"
    name, email = "Alex Test", "alex@example.org"

    async def conversation(transport, session, *, settings):
        assert session.demo_mode is True
        assert session.from_number is None
        captured = await call_tool(
            session, "prepare_customer_account", {"name": name, "email": email}
        )
        assert captured["status"] == "needs_confirmation"
        confirmed = await call_tool(session, "confirm_customer_account", {"email": email})
        assert confirmed["status"] == "confirmed"

    async def send(payload, key):
        with sqlite3.connect(config.CUSTOMER_DB_PATH) as db:
            assert db.execute("SELECT name, email FROM customers").fetchone() == (name, email)
        assert payload["to"] == [email]
        assert key.startswith("customer/")
        return "welcome-test-id"

    sender = AsyncMock(side_effect=send)
    monkeypatch.setattr(appointment_email, "send_message", sender)
    monkeypatch.setattr(bot.gptlive, "run_call", conversation)
    monkeypatch.setattr(bot, "create_transport", AsyncMock(return_value=object()))
    monkeypatch.setattr(
        bot, "DemoRecorder", lambda: SimpleNamespace(tap=Mock(), save=AsyncMock(return_value={}))
    )
    request = SimpleNamespace(session_id=call_id, body={"scenario_id": "account"})
    asyncio.run(bot.bot(request))
    # A duplicate browser negotiation must not enroll or email twice.
    asyncio.run(bot.bot(request))
    sender.assert_awaited_once()

    response = demo.get(f"/api/demo/sessions/{call_id}")
    assert response.status_code == 200
    receipt = response.json()
    assert receipt["status"] == "complete"
    assert receipt["actions"] == []  # Customer enrollment is separate from clinic registration.
    assert receipt["evidence"][0]["label"] == "Customer account saved"
    assert ["Email", "Accepted by Resend"] in receipt["evidence"][0]["fields"]
    assert email not in response.text
    assert len(demo.get("/api/demo/ledger").json()) == 1


@pytest.mark.parametrize("enabled,available", [(True, True), (False, False)])
def test_account_scenario_requires_configured_human_email(demo, monkeypatch, enabled, available):
    monkeypatch.setattr(config, "APPOINTMENT_EMAILS_ENABLED", enabled)
    response = demo.get("/api/demo/scenarios")
    assert response.status_code == 200
    assert ("account" in {scenario["id"] for scenario in response.json()}) is available
    assert (get_scenario("account") is not None) is available
    assert demo.get("/demo/").status_code == 200
