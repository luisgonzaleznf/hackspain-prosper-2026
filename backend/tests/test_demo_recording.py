import asyncio
import json
import wave
from types import SimpleNamespace

import numpy as np
from app.demo import recording, state
from app.demo.app import register_demo_routes
from app.demo.recording import DemoRecorder
from fastapi import FastAPI
from fastapi.testclient import TestClient


def test_recording_preserves_both_legs_on_one_timeline(tmp_path, monkeypatch):
    clock = [100.0]
    monkeypatch.setattr(recording.time, "monotonic", lambda: clock[0])
    recorder = DemoRecorder()
    clock[0] = 100.02
    recorder.record(0, SimpleNamespace(
        audio=np.full(480, 1200, dtype="<i2").tobytes(), num_channels=1, sample_rate=24000,
    ))
    clock[0] = 100.5
    recorder.record(1, SimpleNamespace(
        audio=np.full(480, -1800, dtype="<i2").tobytes(), num_channels=1, sample_rate=24000,
    ))
    summary = asyncio.run(recorder.save("test", tmp_path))
    with wave.open(str(tmp_path / "test.wav")) as wav:
        assert (wav.getnchannels(), wav.getframerate()) == (2, 24000)
        samples = np.frombuffer(wav.readframes(wav.getnframes()), dtype="<i2").reshape(-1, 2)
    assert np.all(samples[:480, 0] == 1200)
    assert np.all(samples[12000:12480, 1] == -1800)
    assert np.all(samples[:12000, 1] == 0)
    assert summary["duration_s"] == 0.52
    assert len(json.loads((tmp_path / "test.timing.json").read_text())) == 2


def test_failed_and_empty_calls_are_retained_once(tmp_path, monkeypatch):
    monkeypatch.setattr(state, "_LEDGER_PATH", tmp_path / "ledger.jsonl")
    registry = state.DemoSessionRegistry()
    registry.create("failed", "booking")
    registry.log("failed", "voice_error", error="connection lost")
    assert registry.end("failed").status == "error"
    registry.end("failed")
    registry.create("empty", "booking")
    registry.end("empty")
    entries = registry.ledger()
    assert [(entry.session_id, entry.status) for entry in entries] == [
        ("empty", "complete"), ("failed", "error"),
    ]


def test_local_review_serves_full_tool_trace_and_recording(tmp_path, monkeypatch):
    from app import config

    monkeypatch.setattr(config, "CALLS_DIR", tmp_path)
    monkeypatch.setattr(config, "AUDIO_DIR", tmp_path)
    call_id = "11111111-1111-4111-8111-111111111111"
    tool = {"kind": "tool", "name": "record_booking", "args": {"slot": "test"},
            "result": {"error": "Slot not looked up"}}
    (tmp_path / f"{call_id}.jsonl").write_text(json.dumps(tool) + "\n")
    (tmp_path / f"{call_id}.wav").write_bytes(b"test audio")
    app = FastAPI()
    register_demo_routes(app)
    client = TestClient(app)
    trace = client.get(f"/api/demo/sessions/{call_id}/trace")
    assert trace.status_code == 200
    assert json.loads(trace.text) == tool
    assert client.get(f"/api/demo/sessions/{call_id}/audio").content == b"test audio"
    assert client.get("/api/demo/sessions/invalid_id/trace").status_code == 400
    assert client.get("/demo/review.html").status_code == 200
