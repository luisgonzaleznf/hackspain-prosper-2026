import asyncio

from app import config, prosper
from app.prompt import RULES
from app.session import CallSession
from app.tools import call_tool


def test_relative_move_survives_caller_correction_and_both_submit(monkeypatch, tmp_path):
    monkeypatch.setattr(config, "CALLS_DIR", tmp_path)
    sent = []

    class Recorder:
        async def submit(self, payload):
            sent.append(payload)
            return 200, {}

    monkeypatch.setattr(prosper, "client", Recorder)
    session = CallSession(call_id="two-intents")
    relative = {"action": "RESCHEDULE", "appointment_id": "A1", "policy_id": "mapfre"}
    session.stage(relative)
    session.stage({"action": "BOOK", "patient_id": "P2", "slot": "Tuesday", "policy_id": "asisa"})
    asyncio.run(call_tool(session, "clear_recorded_actions", {"patient_id": "P2"}))
    assert session.actions == [relative]
    corrected = {"action": "BOOK", "patient_id": "P2", "slot": "Thursday", "policy_id": "asisa"}
    session.stage(corrected)
    asyncio.run(session.finish())
    assert sent == [a | {"call_id": "two-intents"} for a in [relative, corrected]]
    assert "Search separately for each patient" in RULES
    assert "Never use record_no_action for a digression or unfinished second request" in RULES
