"""The per-call log says how the carrier hung up: its `stop`, the close code, and whether a close
frame arrived. Message shapes are uvicorn's (websockets_sansio_impl): a close frame carries
`reason`, a dropped connection reports 1005 without one."""

import asyncio
import json
import wave

import pytest
from app import config
from app.server import instrument_inbound_events, save_caller_audio
from app.session import CallSession

STOP = json.dumps({"event": "stop", "sequenceNumber": "9", "streamSid": "MZ1", "stop": {}})
MEDIA = json.dumps({"event": "media", "streamSid": "MZ1", "media": {"payload": "//8="}})


@pytest.fixture(autouse=True)
def calls_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "CALLS_DIR", tmp_path)


class FakeSocket:
    def __init__(self, messages: list[dict]):
        self.messages = messages

    async def receive(self) -> dict:
        return self.messages.pop(0)


def events(messages: list[dict]) -> list[dict]:
    session = CallSession(call_id="c1")
    socket = FakeSocket(messages)
    instrument_inbound_events(socket, session, None)  # type: ignore[arg-type]

    async def drain():
        while socket.messages:
            await socket.receive()

    asyncio.run(drain())
    rows = [json.loads(line) for line in (config.CALLS_DIR / "c1.jsonl").read_text().splitlines()]
    return [{k: v for k, v in r.items() if k != "t"} for r in rows]


def test_captures_inbound_audio_as_replayable_wav():
    session = CallSession(call_id="capture")
    socket = FakeSocket([{"type": "websocket.receive", "text": MEDIA}])
    caller_ulaw = bytearray()
    instrument_inbound_events(socket, session, caller_ulaw)  # type: ignore[arg-type]
    asyncio.run(socket.receive())
    assert bytes(caller_ulaw) == b"\xff\xff"

    save_caller_audio(session, caller_ulaw)
    path = config.CALLS_DIR / "capture.caller.wav"
    with wave.open(str(path)) as captured:
        assert (captured.getframerate(), captured.getnchannels(), captured.getsampwidth()) == (
            8000,
            1,
            2,
        )
        assert captured.getnframes() == 2


def test_clean_hangup_logs_stop_then_close_frame():
    assert events(
        [
            {"type": "websocket.receive", "text": MEDIA},
            {"type": "websocket.receive", "text": STOP},
            {"type": "websocket.disconnect", "code": 1000, "reason": ""},
        ]
    ) == [
        {"kind": "stop_received"},
        {"kind": "socket_closed", "code": 1000, "reason": "", "close_frame": True},
    ]


def test_dropped_connection_logs_no_close_frame():
    assert events(
        [
            {"type": "websocket.receive", "text": MEDIA},
            {"type": "websocket.disconnect", "code": 1005},
        ]
    ) == [{"kind": "socket_closed", "code": 1005, "reason": "", "close_frame": False}]
