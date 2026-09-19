import asyncio

import pytest
from app import config
from app.prompt import RULES
from app.session import CallSession
from app.tools import call_tool


@pytest.mark.parametrize(
    ("selector", "remaining"),
    [
        ({"patient_id": "P1"}, ["RESCHEDULE", "BOOK"]),
        ({"appointment_id": "A1"}, ["BOOK", "BOOK"]),
        ({}, []),
    ],
)
def test_withdraw_one_intent_preserves_others(tmp_path, monkeypatch, selector, remaining):
    monkeypatch.setattr(config, "CALLS_DIR", tmp_path)
    session = CallSession(call_id="correction")
    session.stage({"action": "BOOK", "patient_id": "P1"})
    session.stage({"action": "RESCHEDULE", "appointment_id": "A1"})
    session.stage({"action": "BOOK", "patient_id": "P2"})
    result = asyncio.run(call_tool(session, "clear_recorded_actions", selector))
    assert [a["action"] for a in result["everything_recorded"]] == remaining
    if selector:
        assert session.actions[-1]["patient_id"] == "P2"


@pytest.mark.parametrize(
    "selector", [{"patient_id": ""}, {"patient_id": "P1", "appointment_id": "A1"}]
)
def test_invalid_selector_does_not_clear_everything(tmp_path, monkeypatch, selector):
    monkeypatch.setattr(config, "CALLS_DIR", tmp_path)
    session = CallSession(call_id="invalid")
    session.stage({"action": "BOOK", "patient_id": "P1"})
    assert "error" in asyncio.run(call_tool(session, "clear_recorded_actions", selector))
    assert len(session.actions) == 1


def test_explicit_correction_is_not_ignored_as_a_slip():
    assert "find_patient again with it if the chart is not yet confirmed" in RULES
    assert "The slip rule is for an extra identifier the caller does not correct" in RULES
    assert "so do not clear first" in RULES
    assert "drop that patient's booking with nothing to replace it" in RULES
    assert "A pause is not consent or cancellation" in RULES
