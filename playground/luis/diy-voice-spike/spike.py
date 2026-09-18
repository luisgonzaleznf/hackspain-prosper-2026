"""DIY voice spike: Twilio µ-law -> whisper-1 -> claude-3-5-sonnet -> tts-1 -> µ-law.

The direction we picked (see notes/voice-stack.md). Sequential and blocking on
purpose for this first pass: whole utterance in, whole reply out. Streaming,
interruption handling and VAD tuning are TODOs for the real build.
"""

import asyncio
import base64
import io
import json
import os
import wave

import audioop
from anthropic import Anthropic
from openai import OpenAI
from websockets.asyncio.server import serve

STT_MODEL = "whisper-1"
LLM_MODEL = "claude-3-5-sonnet-20241022"
TTS_MODEL = "tts-1"

SAMPLE_RATE = 8000
FRAME_BYTES = 160
SILENCE_FRAME = b"\xff"
SILENCE_FRAMES_TO_FLUSH = 30  # ~600 ms of trailing silence ends the turn

SYSTEM_PROMPT = "You are a clinic receptionist. Be brief and ask one question at a time."

openai = OpenAI()
anthropic = Anthropic()


def pcm_to_wav(pcm: bytes) -> io.BytesIO:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SAMPLE_RATE)
        w.writeframes(pcm)
    buf.seek(0)
    return buf


def transcribe(pcm: bytes) -> str:
    result = openai.audio.transcriptions.create(model=STT_MODEL, file=pcm_to_wav(pcm))
    return result.text


def reply(user_text: str) -> str:
    # TODO: tool loop for lookups once we know which clinic endpoints matter
    message = anthropic.messages.create(
        model=LLM_MODEL,
        max_tokens=300,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_text}],
    )
    return "".join(block.text for block in message.content if block.type == "text")


def speak(text: str) -> bytes:
    speech = openai.audio.speech.create(model=TTS_MODEL, voice="alloy", input=text)
    pcm24, _ = audioop.ratecv(speech.content, 2, 1, 24000, SAMPLE_RATE, None)
    return audioop.lin2ulaw(pcm24, 2)


def stream_tts_audio(ulaw: bytes, stream_sid: str, twilio_ws) -> None:
    for i in range(0, len(ulaw), FRAME_BYTES):
        frame = ulaw[i : i + FRAME_BYTES]
        twilio_ws.send(
            json.dumps(
                {
                    "event": "media",
                    "sequenceNumber": "1",
                    "streamSid": stream_sid,
                    "media": {"track": "outbound", "chunk": base64.b64encode(frame).decode(), "timestamp": str(i * 20)},
                }
            )
        )


async def handle_turn(ulaw: bytes, stream_sid: str, twilio_ws) -> None:
    if len(ulaw) < FRAME_BYTES * 10:
        return
    # TODO: this whole chain should be streaming; blocking is fine for the spike
    pcm = audioop.ulaw2lin(ulaw, 2)
    text = transcribe(pcm)
    print("caller:", text)
    if not text.strip():
        return
    answer = reply(text)
    print("agent:", answer)
    stream_tts_audio(speak(answer), stream_sid, twilio_ws)


async def bridge(twilio_ws) -> None:
    stream_sid = ""
    buffer = b""
    quiet = 0
    async for raw in twilio_ws:
        event = json.loads(raw)
        match event.get("event"):
            case "start":
                stream_sid = event["start"]["streamSid"]
            case "media":
                chunk = base64.b64decode(event["media"]["payload"])
                buffer += chunk
                if chunk == SILENCE_FRAME * FRAME_BYTES:
                    quiet += 1
                    # TODO: real VAD; this naive threshold misfires on noisy lines
                    if quiet >= SILENCE_FRAMES_TO_FLUSH:
                        await handle_turn(buffer, stream_sid, twilio_ws)
                        buffer = b""
                        quiet = 0
                else:
                    quiet = 0
            case "stop":
                if buffer:
                    await handle_turn(buffer, stream_sid, twilio_ws)
                return


async def main() -> None:
    async with serve(bridge, "localhost", 8081):
        await asyncio.Future()  # run forever


if __name__ == "__main__":
    asyncio.run(main())
