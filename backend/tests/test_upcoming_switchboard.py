import asyncio
import json

import pytest
from app import config
from app.session import CallSession


@pytest.mark.parametrize("count", [5, 10, 20])
def test_burst_sessions_do_not_share_actions_lookups_or_outcomes(monkeypatch, tmp_path, count):
    monkeypatch.setattr(config, "CALLS_DIR", tmp_path)
    sessions = [CallSession(call_id=f"burst-{i}") for i in range(count)]
    for i, session in enumerate(sessions):
        session.remember_patients([{"patient_id": f"P{i}"}])
        session.remember_appointments([{"appointment_id": f"A{i}"}])
        session.record_search(i, [])
        session.stage({"action": "CANCEL", "appointment_id": f"A{i}"})

    async def finish_all():
        await asyncio.gather(*(session.finish() for session in sessions))

    asyncio.run(finish_all())
    for i, session in enumerate(sessions):
        assert list(session.patients) == [f"P{i}"]
        assert list(session.appointments) == [f"A{i}"]
        assert session.searches[0]["slots_found"] == i
        events = [
            json.loads(line) for line in (tmp_path / f"burst-{i}.jsonl").read_text().splitlines()
        ]
        ended = [e for e in events if e["kind"] == "call_ended"]
        assert len(ended) == 1
        assert ended[0]["actions"] == [{"action": "CANCEL", "appointment_id": f"A{i}"}]
