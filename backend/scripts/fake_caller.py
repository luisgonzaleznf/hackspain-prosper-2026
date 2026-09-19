"""Fake Prosper carrier: dials our /ws speaking Twilio Media Streams, like the scorer does.

    uv run python scripts/fake_caller.py caller_8k.wav          # one call to ws://localhost:7860/ws
    uv run python scripts/fake_caller.py caller_8k.wav --n 10   # ten overlapping calls (a Run All wave)
    uv run python scripts/fake_caller.py caller_8k.wav --url wss://<tunnel-host>/ws

caller_8k.wav: 8kHz mono PCM16. Writes what the agent said to $CALLER_OUT/agent_<i>.wav.
Pass --captured for logs/calls/<call_id>.caller.wav, which already includes the original timing.
"""

import argparse
import asyncio
import base64
import json
import os
import time
import uuid
import wave
from array import array
from pathlib import Path

import websockets
from app import audio

OUT = Path(os.environ.get("CALLER_OUT", "out"))


async def call(
    i: int,
    url: str,
    caller_ulaw: bytes,
    listen_secs: float,
    from_number: str | None,
    captured: bool,
) -> dict:
    call_sid, stream_sid = str(uuid.uuid4()), "MZ" + uuid.uuid4().hex
    agent = array("h")
    t: dict[str, float] = {}
    seq = 0

    def msg(event: str, **body) -> str:
        nonlocal seq
        seq += 1
        return json.dumps(
            {"event": event, "sequenceNumber": str(seq), "streamSid": stream_sid, **body}
        )

    async with websockets.connect(url, max_size=None) as ws:

        async def receive():
            async for raw in ws:
                m = json.loads(raw)
                if m.get("event") == "media":
                    chunk = base64.b64decode(m["media"]["payload"])
                    pcm = audio.decode(chunk)
                    agent.extend(pcm)
                    if audio.pcm_rms(pcm) > audio.AUDIBLE_RMS:
                        t["last_loud"] = time.monotonic()
                        t.setdefault("greeting", time.monotonic())
                        if "user_done" in t:
                            t.setdefault("first_audio", time.monotonic())

        rx = asyncio.create_task(receive())
        await ws.send(json.dumps({"event": "connected", "protocol": "Call", "version": "1.0.0"}))
        params = {"call_id": call_sid}
        if from_number:
            params["from_number"] = from_number
        await ws.send(
            msg(
                "start",
                start={
                    "accountSid": "AC" + "0" * 32,
                    "streamSid": stream_sid,
                    "callSid": call_sid,
                    "tracks": ["inbound"],
                    "customParameters": params,
                    "mediaFormat": {"encoding": "audio/x-mulaw", "sampleRate": 8000, "channels": 1},
                },
            )
        )
        chunk_no, t0 = 0, time.monotonic()

        async def send_frames(data: bytes) -> None:
            nonlocal chunk_no
            for off in range(0, len(data), audio.FRAME_BYTES):
                chunk_no += 1
                await ws.send(
                    msg(
                        "media",
                        media={
                            "track": "inbound",
                            "chunk": str(chunk_no),
                            "timestamp": str(chunk_no * 20),
                            "payload": base64.b64encode(
                                data[off : off + audio.FRAME_BYTES]
                            ).decode(),
                        },
                    )
                )
                # pace in real time against the call clock, not per-frame sleeps
                await asyncio.sleep(max(0, t0 + chunk_no * 0.02 - time.monotonic()))

        if not captured:
            # A normal utterance waits for the greeting. Captured carrier audio already includes
            # its original silence and turn timing, so it starts at the call's first media frame.
            while time.monotonic() - t0 < 8 and not (
                "last_loud" in t and time.monotonic() - t["last_loud"] > 0.8
            ):
                await send_frames(audio.SILENCE * 5)
        await send_frames(caller_ulaw)
        t["user_done"] = time.monotonic()
        await send_frames(audio.SILENCE * int(listen_secs * 50))
        await ws.send(msg("stop", stop={"accountSid": "AC" + "0" * 32, "callSid": call_sid}))
        rx.cancel()

    audio.write_wav(OUT / f"agent_{i}.wav", agent)
    return {
        "call": i,
        "call_id": call_sid,
        "greeting_after_secs": round(t["greeting"] - t0, 2) if "greeting" in t else None,
        "agent_audio_secs": round(len(agent) / audio.RATE, 1),
        "reply_latency_secs": round(t["first_audio"] - t["user_done"], 2)
        if "first_audio" in t
        else None,
    }


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("wav")
    ap.add_argument("--url", default="ws://localhost:7860/ws")
    ap.add_argument("--n", type=int, default=1)
    ap.add_argument("--listen", type=float, default=10.0)
    ap.add_argument("--from-number", default="+34612345678")
    ap.add_argument("--captured", action="store_true")
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    with wave.open(args.wav) as w:
        assert w.getframerate() == 8000 and w.getnchannels() == 1 and w.getsampwidth() == 2
        pcm = array("h")
        pcm.frombytes(w.readframes(w.getnframes()))
    caller_ulaw = audio.encode(pcm)
    del pcm
    results = await asyncio.gather(
        *(
            call(i, args.url, caller_ulaw, args.listen, args.from_number, args.captured)
            for i in range(args.n)
        ),
        return_exceptions=True,
    )
    print(json.dumps([r if isinstance(r, dict) else repr(r) for r in results], indent=2))


if __name__ == "__main__":
    asyncio.run(main())
