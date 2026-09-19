"""The wire recorder: a synthetic call with known answers (greeting time, response latency, a
barge-in, an agent stutter, a caller-side stall, dead air) must come back out of the summary, and a
recording bug must never cost the call its audio."""

import asyncio
import audioop
import base64
import json
import math
import wave

import pytest
from app import config
from app.recorder import RATE, WireRecorder
from app.session import CallSession

SILENT = audioop.lin2ulaw(bytes(2 * 160), 2)


def tone(seconds: float, level: float = 0.3) -> bytes:
    n = round(RATE * seconds)
    pcm = b"".join(
        int(level * 32767 * math.sin(2 * math.pi * 440 * i / RATE)).to_bytes(
            2, "little", signed=True
        )
        for i in range(n)
    )
    return audioop.lin2ulaw(pcm, 2)


def media(ulaw: bytes, stamp_ms: int | None = None) -> str:
    body = {"payload": base64.b64encode(ulaw).decode()}
    if stamp_ms is not None:
        body["timestamp"] = str(stamp_ms)
    return json.dumps({"event": "media", "streamSid": "MZ1", "media": body})


@pytest.fixture(autouse=True)
def calls_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "CALLS_DIR", tmp_path)


def synthetic_call() -> WireRecorder:
    """10 s. Caller speaks 1.0-2.0 s and barges in 3.4-3.8 s; the first 0.3 s of frames queue
    until 0.3 s (the session connecting) and 5.0-5.5 s arrive late in one burst.
    Agent greets 0.52-1.0 s and answers 3.0-4.0 s with a 0.2 s stutter at 3.48 s, then says nothing."""
    rec = WireRecorder(t0=0.0)
    for i in range(500):
        t = i * 0.02
        speaking = 1.0 <= t < 2.0 or 3.4 <= t < 3.8
        arrival = 0.3 if t < 0.3 else 5.5 if 5.0 <= t < 5.5 else t
        rec.inbound.append((arrival, t, tone(0.02) if speaking else SILENT))
    for start, chunks in ((0.52, 12), (3.0, 12), (3.68, 8)):  # 40 ms chunks
        for k in range(chunks):
            rec.outbound.append((start + k * 0.04, tone(0.04)))
    return rec


def test_summary_recovers_the_known_timeline(tmp_path):
    s = synthetic_call()._save("c1", tmp_path)
    assert s["first_agent_audio_s"] == 0.52
    assert s["duration_s"] == 10.0
    assert s["turns"]["responses"] == 1
    assert s["turns"]["latency_p50_s"] == pytest.approx(1.0, abs=0.05)
    assert s["turns"]["barge_ins"] == 1
    assert s["turns"]["yield_max_s"] == pytest.approx(0.6, abs=0.05)
    assert s["agent"]["underruns"] == 1
    assert s["agent"]["underrun_max_ms"] == pytest.approx(200, abs=5)
    assert s["agent"]["longest_silence_s"] == pytest.approx(6.0, abs=0.05)
    assert s["agent"]["longest_silence_at_s"] == pytest.approx(4.0, abs=0.05)
    assert (s["dead_air_s"], s["dead_air_at_s"]) == (6.0, 4.0)
    assert s["caller"]["stalls"] == 1
    assert s["caller"]["stall_max_ms"] == pytest.approx(520, abs=5)
    assert s["caller"]["connect_backlog_ms"] == pytest.approx(300, abs=5)
    assert s["caller"]["noise_dbfs"] is None  # digital silence between words
    assert s["flags"] == [
        "dead_air:6.0s@4.0s(to hang-up)",
        "agent_underruns:1x,max200ms",
        "caller_stalls:1x,max520ms",
    ]
    with wave.open(s["wav"]) as w:
        assert (w.getnchannels(), w.getframerate()) == (2, RATE)
        assert w.getnframes() == 10 * RATE
    timing = json.loads((tmp_path / "c1.timing.json").read_text())
    assert len(timing["inbound_ms"]) == 500


def test_noisy_line_is_flagged(tmp_path):
    rec = WireRecorder(t0=0.0)
    noise, speech = tone(0.02, level=0.05), tone(0.02, level=0.2)
    for i in range(250):
        t = i * 0.02
        rec.inbound.append((t, t, speech if 1.0 <= t < 3.0 else noise))
    # Speech power 16x the noise's: SNR 10*log10(16 - 1), with the bed's power taken out.
    silent_agent = rec._save("c2", tmp_path)
    assert silent_agent["caller"]["snr_db"] == pytest.approx(11.8, abs=0.5)
    assert "no_agent_audio" in silent_agent["flags"]
    rec.outbound = [(3.5 + k * 0.04, tone(0.04)) for k in range(25)]  # the bed, heard as it talks
    s = rec._save("c2", tmp_path)
    assert s["caller"]["snr_db"] == pytest.approx(11.8, abs=0.5)
    assert any(f.startswith("noisy_caller:") for f in s["flags"])


class FakeSocket:
    def __init__(self, incoming: list[dict]):
        self.incoming, self.sent = incoming, []

    async def receive(self) -> dict:
        return self.incoming.pop(0)

    async def send_text(self, data: str) -> None:
        self.sent.append(data)


def test_taps_record_both_legs_and_never_block_the_call():
    session = CallSession(call_id="c3")
    socket = FakeSocket([{"type": "websocket.receive", "text": media(SILENT, 0)}])
    rec = WireRecorder()
    rec.tap(socket, session)

    async def call():
        await socket.receive()
        await socket.send_text(media(tone(0.04)))
        await socket.send_text('{"event": "media", not json')  # a bad frame still goes out
        await socket.send_text(json.dumps({"event": "clear", "streamSid": "MZ1"}))

    asyncio.run(call())
    assert len(rec.inbound) == 1 and len(rec.outbound) == 1 and rec.clears == 1
    assert len(socket.sent) == 3
    rows = [json.loads(line) for line in (config.CALLS_DIR / "c3.jsonl").read_text().splitlines()]
    assert [r["kind"] for r in rows] == ["first_agent_audio"]
