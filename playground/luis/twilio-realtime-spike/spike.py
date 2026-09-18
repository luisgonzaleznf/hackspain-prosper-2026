"""Day-0 spike: Twilio Media Streams -> OpenAI Realtime, raw frames both ways.

Not the real agent. No tools, no VAD, no barge-in, no resampling. If audio
comes back out the other end, the spike did its job.

Run: OPENAI_API_KEY=... uv run python spike.py
"""

import asyncio
import base64
import json
import os

from websockets.asyncio.client import connect
from websockets.asyncio.server import serve

TWILIO_PORT = 8080
REALTIME_URL = "wss://api.openai.com/v1/realtime?model=gpt-4o-realtime-preview"
SESSION_CONFIG = {
    "type": "session.update",
    "session": {
        "type": "realtime",
        "instructions": "You are a clinic receptionist. Be brief.",
        "voice": "alloy",
        # TODO: does this accept µ-law? Probably need a resample here AND back.
        "input_audio_format": "pcm16",
        "output_audio_format": "pcm16",
        "turn_detection": {"type": "server_vad"},  # TODO: tune for a phone line
    },
}

GREETING = (
    "Hello, thanks for calling the clinic. How can I help you today?"
)


def twilio_event(raw: bytes) -> dict | None:
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


def audio_to_b64(pcm: bytes) -> str:
    return base64.b64encode(pcm).decode()


def b64_to_audio(b64: str) -> bytes:
    return base64.b64decode(b64)


async def bridge(twilio_ws) -> None:
    headers = {
        "Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}",
        "OpenAI-Beta": "realtime=v1",
    }
    start = None
    async with connect(REALTIME_URL, additional_headers=headers) as rt:
        await rt.send(json.dumps(SESSION_CONFIG))
        await rt.send(
            json.dumps(
                {
                    "type": "response.create",
                    "response": {"instructions": f"Say exactly: {GREETING}"},
                }
            )
        )

        async def twilio_to_realtime() -> None:
            nonlocal start
            async for raw in twilio_ws:
                event = twilio_event(raw)
                if event is None:
                    continue
                match event.get("event"):
                    case "start":
                        start = event["start"]  # callSid, custom params...
                    case "media":
                        # TODO: µ-law 8kHz -> pcm16. Fake it as raw for now.
                        await rt.send(
                            json.dumps(
                                {
                                    "type": "input_audio_buffer.append",
                                    "audio": event["media"]["payload"],
                                }
                            )
                        )
                    case "stop":
                        return

        async def realtime_to_twilio() -> None:
            async for raw in rt:
                event = json.loads(raw)
                match event.get("type"):
                    case "response.audio":
                        # TODO: pcm16 -> µ-law 8kHz. Fake it as raw for now.
                        await twilio_ws.send(
                            json.dumps(
                                {
                                    "event": "media",
                                    "streamSid": start["streamSid"] if start else "",
                                    "media": {"payload": audio_to_b64(b64_to_audio(event["data"]))},
                                }
                            )
                        )
                    # TODO: function calls. That's the interesting part.

        await asyncio.gather(
            twilio_to_realtime(),
            realtime_to_twilio(),
        )


async def main() -> None:
    async with serve(bridge, "localhost", TWILIO_PORT):
        await asyncio.Future()  # run forever


if __name__ == "__main__":
    asyncio.run(main())
