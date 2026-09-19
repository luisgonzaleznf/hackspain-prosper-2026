import asyncio

import pytest
from app import config, prosper
from app.session import CallSession


@pytest.mark.parametrize("count", [5, 10, 20])
def test_burst_sessions_do_not_share_actions_lookups_or_submissions(monkeypatch, tmp_path, count):
    monkeypatch.setattr(config, "CALLS_DIR", tmp_path)
    submitted = []

    class Recorder:
        async def submit(self, payload):
            await asyncio.sleep(0)
            submitted.append(payload)
            return 200, {}

    monkeypatch.setattr(prosper, "client", Recorder)
    sessions = [CallSession(call_id=f"burst-{i}") for i in range(count)]
    for i, session in enumerate(sessions):
        session.remember_patients([{"patient_id": f"P{i}"}])
        session.remember_appointments([{"appointment_id": f"A{i}"}])
        session.record_search(i, [])
        session.stage({"action": "CANCEL", "appointment_id": f"A{i}"})

    async def finish_all():
        await asyncio.gather(*(session.finish() for session in sessions))

    asyncio.run(finish_all())
    assert len(submitted) == count
    for i, session in enumerate(sessions):
        assert list(session.patients) == [f"P{i}"]
        assert list(session.appointments) == [f"A{i}"]
        assert session.searches[0]["slots_found"] == i
        assert {"action": "CANCEL", "appointment_id": f"A{i}", "call_id": f"burst-{i}"} in submitted
