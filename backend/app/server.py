"""Prosper wire: Twilio Media Streams over a plain WebSocket at /ws (docs/prosper/pages/04-call-contract.md).

    VOICE=codex uv run python -m app.server     # ws://localhost:7860/ws ; expose with scripts/tunnel.sh

Every connection is its own call: fresh transport, fresh CallSession, fresh voice pipeline.
When the socket closes, the session POSTs what the call staged (window: 30 s after hang-up).
"""

import asyncio
import base64
import binascii
import json
from contextlib import asynccontextmanager, suppress
from datetime import datetime

import uvicorn
from fastapi import FastAPI, WebSocket
from integrations.twilio import TwilioCallSession
from integrations.twilio import router as twilio_router
from loguru import logger
from pipecat.runner.utils import parse_telephony_websocket
from pipecat.serializers.twilio import TwilioFrameSerializer
from pipecat.transports.websocket.fastapi import FastAPIWebsocketParams, FastAPIWebsocketTransport
from starlette.types import Message
from starlette.websockets import WebSocketState

from app import audio, clinic, config, voice
from app.demo.app import register_demo_routes
from app.recorder import WireRecorder
from app.session import CallSession

ACTIVE: set[str] = set()


def _eval_reference_time(params: dict) -> datetime | None:
    """The call's "now" in local evals (EVAL_MODE=1 only); None means the real clock."""
    raw = params.get("eval_reference_time") if config.EVAL_MODE else None
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw).astimezone(config.TZ)
    except ValueError:
        logger.warning(f"ignoring bad eval_reference_time {raw!r}")
        return None


def instrument_inbound_events(
    websocket: WebSocket, session: CallSession, caller_ulaw: bytearray | None
) -> None:
    """Log how the carrier ended the call and, given a buffer, capture the caller's audio.

    Pipecat drops `stop` and the close code, so without this a harness socket error and a clean
    hang-up look the same in our logs. `close_frame` is False when the connection dropped with no
    close frame (uvicorn reports 1005 and no `reason` then). With `caller_ulaw` None (the default,
    RECORD_CALLER_AUDIO off) media frames are not parsed at all.
    """
    receive = websocket.receive

    async def receive_and_log() -> Message:
        message = await receive()
        if message["type"] == "websocket.disconnect":
            session.log(
                "socket_closed",
                code=message.get("code"),
                reason=message.get("reason") or "",
                close_frame="reason" in message,
            )
        elif (text := message.get("text")) and (caller_ulaw is not None or '"stop"' in text):
            with suppress(ValueError, KeyError, binascii.Error):
                event = json.loads(text)
                if event.get("event") == "media" and caller_ulaw is not None:
                    media = event["media"]
                    if media.get("track", "inbound") == "inbound":
                        caller_ulaw.extend(base64.b64decode(media["payload"], validate=True))
                elif event.get("event") == "stop":
                    session.log("stop_received")
        return message

    websocket.receive = receive_and_log  # type: ignore[method-assign]


def save_caller_audio(session: CallSession, caller_ulaw: bytes | bytearray) -> None:
    """Save the exact inbound carrier stream as a replayable 8 kHz mono WAV."""
    if not caller_ulaw:
        return
    path = config.CALLS_DIR / f"{session.call_id}.caller.wav"
    audio.write_wav(path, audio.decode(caller_ulaw))
    session.log(
        "caller_audio_saved",
        file=path.name,
        seconds=round(len(caller_ulaw) / audio.RATE, 3),
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        await clinic.catalogue()
        logger.info("clinic catalogue loaded")
    except Exception as e:
        logger.error(f"clinic catalogue not loaded (check PLATFORM_API_KEY): {e!r}")
    yield


app = FastAPI(lifespan=lifespan)

# Role-play Studio at /demo/ (app/demo/README.md). It shares this process's CallSession,
# prompt and clinic tools, but never submits to Prosper, so it is safe to leave mounted:
# the scored call path is /ws and is untouched by it.
register_demo_routes(app)
app.include_router(twilio_router)


@app.get("/health")
async def health():
    return {
        "ok": True,
        "voice": config.VOICE,
        "active_calls": len(ACTIVE),
        "catalogue_loaded": clinic.cached() is not None,
    }


@app.websocket("/ws")
async def ws(websocket: WebSocket):
    await run_telephony_call(websocket)


@app.websocket("/integrations/twilio/ws")
async def twilio_ws(websocket: WebSocket):
    await run_telephony_call(websocket, session_type=TwilioCallSession)


async def run_telephony_call(websocket: WebSocket, session_type: type[CallSession] = CallSession):
    await websocket.accept()
    transport_type, call = await parse_telephony_websocket(websocket)
    recorder = WireRecorder()  # the call's clock starts once the handshake is in
    if transport_type != "twilio" or not call.call_id:
        logger.error(f"unexpected handshake: {transport_type} {call}")
        await websocket.close()
        return
    serializer = TwilioFrameSerializer(
        stream_sid=call.stream_id,
        call_sid=call.call_id,
        # Closing the socket returns real Twilio calls to the webhook's <Hangup>.
        # Prosper likewise owns hang-up; neither path needs Twilio API credentials.
        params=TwilioFrameSerializer.InputParams(auto_hang_up=False),
    )
    transport = FastAPIWebsocketTransport(
        websocket,
        FastAPIWebsocketParams(
            audio_in_enabled=True,
            audio_out_enabled=True,
            add_wav_header=False,
            serializer=serializer,
        ),
    )
    session = await session_type.start(
        call_id=call.call_id,
        stream_sid=call.stream_id or "",
        from_number=call.from_number,
        started_at=_eval_reference_time(call.body),
    )
    caller_ulaw = bytearray() if config.RECORD_CALLER_AUDIO else None
    instrument_inbound_events(websocket, session, caller_ulaw)
    recorder.tap(websocket, session)
    ACTIVE.add(session.call_id)
    logger.info(f"call {session.call_id} from {call.from_number} voice={config.VOICE}")
    try:
        await voice.run_call(transport, session)
    except Exception as e:
        logger.exception(f"call {session.call_id}: voice layer failed")
        session.log("voice_error", error=repr(e))
    finally:
        if websocket.client_state == WebSocketState.CONNECTED:
            session.log("closed_by_agent")  # returning closes the socket: we hung up first
        ACTIVE.discard(session.call_id)
        results = await session.finish()
        if caller_ulaw:
            await asyncio.to_thread(save_caller_audio, session, caller_ulaw)
        logger.info(f"call {session.call_id} ended; submitted {[r['status'] for r in results]}")
        # Only after the submit: the audio can wait, the 30 s window cannot.
        try:
            session.log("audio.timeline", **await recorder.save(session.call_id, config.AUDIO_DIR))
        except Exception as e:
            session.log("audio_error", error=repr(e))


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=config.PORT)
