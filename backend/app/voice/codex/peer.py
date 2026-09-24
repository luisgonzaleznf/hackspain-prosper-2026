"""One GPT-Live call on the Codex subscription, with OUR server as the WebRTC peer.

    peer = CodexLivePeer(prompt=..., in_rate=8000, out_rate=8000, on_audio=..., on_event=...)
    await peer.start()          # spawns codex app-server, negotiates WebRTC
    peer.push_audio(pcm16)      # caller audio, mono PCM16 at in_rate
    ...                         # on_audio(pcm16 at out_rate) with the agent's voice
    await peer.close()

on_event receives both the GPT-Live data-channel events ("oai-events") and the
app-server notifications, each as a dict with a "source" key added.
"""

from __future__ import annotations

import array
import asyncio
import contextlib
import fractions
import json
import re
import time
from collections.abc import Awaitable, Callable
from typing import Any

import av
from aiortc import MediaStreamTrack, RTCConfiguration, RTCPeerConnection, RTCSessionDescription
from aiortc.mediastreams import MediaStreamError

from app.voice.codex.rpc import (
    LIVE_START_TIMEOUT,
    CodexAppServer,
    CodexRpcError,
    start_live,
)

FRAME_MS = 20
LOUD_PEAK = 600  # int16 peak above which 20ms of audio counts as speech, for the counters


def _peak(pcm16: bytes) -> int:
    samples = array.array("h", pcm16[: len(pcm16) // 2 * 2])
    return max(map(abs, samples), default=0)


# A brain turn that ends on a promise ("one moment while I check...") leaves the line silent:
# nothing restarts the brain until the caller speaks, and callers hang up on silence. When that
# happens we start the next turn ourselves (at most MAX_CONTINUES times in a row).
PROMISE = re.compile(
    r"\b(one moment|just a moment|a moment|bear with me|let me (check|look|see|find|search|pull)"
    r"|i'?ll (check|look|find|search|pull)|i am checking|i'm checking|checking (that|now|the|your)"
    r"|looking (that|it|into|for)|un momento|déjeme|voy a (buscar|mirar|comprobar|consultar)"
    r"|lo (miro|compruebo|busco)|ara ho (miro|comprovo)|un moment)\b",
    re.IGNORECASE,
)
CONTINUE = (
    "You ended your last reply with a promise to check, but the caller is waiting in silence. "
    "Do it now: make the tool calls, then reply with the result or the one question to ask."
)
MAX_CONTINUES = 2


def is_promise(text: str) -> bool:
    """A reply that only promises work: says it will check, and asks the caller nothing."""
    text = text.strip()
    return bool(text) and not text.endswith("?") and bool(PROMISE.search(text))


MAX_BACKLOG_MS = 200


class _PcmSourceTrack(MediaStreamTrack):
    """Audio track fed from a byte buffer; emits silence when the buffer is empty."""

    kind = "audio"

    def __init__(self, rate: int) -> None:
        super().__init__()
        self.rate = rate
        self.samples = rate * FRAME_MS // 1000
        self.buf = bytearray()
        self._t0: float | None = None
        self._pts = 0
        # Counters for the call log: did the caller's voice actually reach OpenAI?
        self.pushed_ms = self.pushed_loud_ms = self.sent_ms = self.sent_loud_ms = 0
        # Caller audio trimmed from the backlog: all of it, and the part trimmed after the first
        # frame went out (a mid-call stall, not the audio queued while the session connected).
        self.dropped_ms = self.dropped_midcall_ms = 0

    def feed(self, pcm16: bytes) -> None:
        self.buf.extend(pcm16)
        ms = len(pcm16) * 1000 // (2 * self.rate)
        self.pushed_ms += ms
        if _peak(pcm16) > LOUD_PEAK:
            self.pushed_loud_ms += ms

    async def recv(self) -> av.AudioFrame:
        connecting = self._t0 is None
        if connecting:
            self._t0 = time.monotonic()
        else:
            wait = self._t0 + self._pts / self.rate - time.monotonic()
            if wait > 0:
                await asyncio.sleep(wait)
        n = self.samples * 2
        # Relay in real time: audio queued while the session connected would delay every
        # later turn by the same amount, so keep at most MAX_BACKLOG_MS buffered.
        excess = len(self.buf) - self.rate * 2 * MAX_BACKLOG_MS // 1000
        if excess > 0:
            del self.buf[:excess]
            ms = excess * 1000 // (2 * self.rate)
            self.dropped_ms += ms
            if not connecting:
                self.dropped_midcall_ms += ms
        chunk = bytes(self.buf[:n])
        del self.buf[:n]
        if len(chunk) < n:
            chunk += bytes(n - len(chunk))
        frame = av.AudioFrame(format="s16", layout="mono", samples=self.samples)
        frame.planes[0].update(chunk)
        frame.sample_rate = self.rate
        frame.pts = self._pts
        frame.time_base = fractions.Fraction(1, self.rate)
        self._pts += self.samples
        self.sent_ms += FRAME_MS
        if _peak(chunk) > LOUD_PEAK:
            self.sent_loud_ms += FRAME_MS
        return frame


class CodexLivePeer:
    def __init__(
        self,
        *,
        prompt: str,
        voice: str = "cove",
        in_rate: int = 8000,
        out_rate: int = 8000,
        on_audio: Callable[[bytes], Any] | None = None,  # may be async
        on_event: Callable[[dict], Any] | None = None,
        tools: list[dict] | None = None,
        brain_instructions: str | None = None,
        on_tool_call: Callable[[str, dict], Awaitable[dict]] | None = None,
    ) -> None:
        """With `tools`, GPT-Live delegates to the Codex thread agent (instructed by
        `brain_instructions`), whose tool calls land in `on_tool_call(name, args)`."""
        self.prompt = prompt
        self.tools = tools
        self.brain_instructions = brain_instructions
        self.on_tool_call = on_tool_call
        self.voice = voice
        self.out_rate = out_rate
        self.on_audio = on_audio
        self.on_event = on_event
        self.thread_id: str | None = None
        self._src = _PcmSourceTrack(in_rate)
        # No STUN: OpenAI's side is public, host candidates suffice, and aiortc's
        # default STUN lookup adds ~5s of ICE gathering to every call.
        self._pc = RTCPeerConnection(RTCConfiguration(iceServers=[]))
        self._dc = self._pc.createDataChannel("oai-events")
        self._srv = self._new_server()
        self._answer: asyncio.Future[str] | None = None
        self.agent_audio_ms = 0
        self._turn_text = ""  # the brain's last message in its current turn
        self._continues = 0
        self._tasks: set[asyncio.Task] = set()
        self._drain_task: asyncio.Task | None = None

    def _new_server(self) -> CodexAppServer:
        return CodexAppServer(on_notification=self._on_notification, on_request=self._on_request)

    # -- events ---------------------------------------------------------------

    def _emit(self, source: str, msg: dict) -> None:
        if self.on_event:
            self.on_event({"source": source, **msg})

    def _on_notification(self, msg: dict) -> None:
        method = msg.get("method", "")
        params = msg.get("params") or {}
        if method == "thread/realtime/sdp" and self._answer and not self._answer.done():
            self._answer.set_result(params.get("sdp", ""))
        elif method == "thread/realtime/error" and self._answer and not self._answer.done():
            self._answer.set_exception(CodexRpcError(str(params.get("message"))))
        if method == "turn/started":
            self._turn_text = ""
        elif (
            method == "item/completed" and (params.get("item") or {}).get("type") == "agentMessage"
        ):
            self._turn_text = params["item"].get("text") or ""
        elif method == "turn/completed" and self.tools is not None:
            task = asyncio.create_task(self._continue_if_promise(self._turn_text))
            self._tasks.add(task)
            task.add_done_callback(self._tasks.discard)
        if not method.endswith("/delta"):  # deltas (audio, partial text) are high-volume noise
            self._emit("codex", msg)

    async def _continue_if_promise(self, text: str) -> None:
        if not is_promise(text):
            self._continues = 0
            return
        if self._continues >= MAX_CONTINUES or not self.thread_id:
            return
        self._continues += 1
        self._emit("brain", {"type": "brain.continue", "after": text, "attempt": self._continues})
        with contextlib.suppress(Exception):  # the call goes on either way
            await self._srv.request(
                "turn/start",
                {"threadId": self.thread_id, "input": [{"type": "text", "text": CONTINUE}]},
                timeout=10,
            )

    async def _on_request(self, method: str, params: dict) -> dict:
        if method != "item/tool/call" or self.on_tool_call is None:
            raise CodexRpcError(f"unsupported request {method}")
        name, args = params.get("tool", ""), params.get("arguments") or {}
        if isinstance(args, str):
            args = json.loads(args or "{}")
        self._emit("tool", {"type": "tool.call", "name": name, "arguments": args})
        result = await self.on_tool_call(name, args)
        self._emit("tool", {"type": "tool.result", "name": name, "result": result})
        return {
            "contentItems": [{"type": "inputText", "text": json.dumps(result, ensure_ascii=False)}],
            "success": not (isinstance(result, dict) and "error" in result),
        }

    async def _drain(self, track: MediaStreamTrack) -> None:
        resampler = av.AudioResampler(format="s16", layout="mono", rate=self.out_rate)
        while True:
            try:
                frame = await track.recv()
            except MediaStreamError:
                return
            if not isinstance(frame, av.AudioFrame):
                continue
            for f in resampler.resample(frame):
                self.agent_audio_ms += f.samples * 1000 // self.out_rate
                if self.on_audio:
                    res = self.on_audio(f.to_ndarray().tobytes())
                    if asyncio.iscoroutine(res):
                        await res

    # -- lifecycle --------------------------------------------------------------

    async def start(self) -> None:
        @self._dc.on("message")
        def _dc_message(data: str | bytes) -> None:
            with contextlib.suppress(json.JSONDecodeError, TypeError):
                self._emit("oai", json.loads(data))

        @self._pc.on("track")
        def _on_track(track: MediaStreamTrack) -> None:
            if track.kind == "audio":
                self._drain_task = asyncio.create_task(self._drain(track))

        self._pc.addTrack(self._src)
        await self._pc.setLocalDescription(await self._pc.createOffer())
        for attempt in range(2):
            self._answer = asyncio.get_running_loop().create_future()
            try:
                await asyncio.wait_for(self._srv.start(), LIVE_START_TIMEOUT)
                self.thread_id = await start_live(
                    self._srv,
                    prompt=self.prompt,
                    sdp_offer=self._pc.localDescription.sdp,
                    voice=self.voice,
                    brain_instructions=self.brain_instructions,
                    tools=self.tools,
                    timeout=LIVE_START_TIMEOUT,
                )
                sdp = await asyncio.wait_for(self._answer, LIVE_START_TIMEOUT)
                await self._pc.setRemoteDescription(RTCSessionDescription(sdp=sdp, type="answer"))
                return
            except TimeoutError:
                if attempt == 0:
                    self._emit(
                        "brain",
                        {"type": "voice.start_retry", "attempt": 1, "reason": "timeout"},
                    )
                await self._srv.close()
                self.thread_id = None
                if attempt == 1:
                    raise
                self._srv = self._new_server()

    async def say(self, text: str) -> None:
        """Make the agent speak `text` (e.g. the greeting when the call connects)."""
        await self._srv.request(
            "thread/realtime/appendSpeech", {"threadId": self.thread_id, "text": text}, timeout=10
        )

    def push_audio(self, pcm16: bytes) -> None:
        self._src.feed(pcm16)

    def audio_stats(self) -> dict:
        """Caller audio: pushed to us, sent on to OpenAI, dropped as backlog (ms)."""
        src = self._src
        return {
            "caller_pushed_ms": src.pushed_ms,
            "caller_pushed_loud_ms": src.pushed_loud_ms,
            "sent_to_openai_ms": src.sent_ms,
            "sent_to_openai_loud_ms": src.sent_loud_ms,
            "dropped_backlog_ms": src.dropped_ms,
            "dropped_midcall_ms": src.dropped_midcall_ms,
            "agent_audio_ms": self.agent_audio_ms,
        }

    def send_event(self, event: dict) -> None:
        """Send a GPT-Live client event over the data channel (e.g. delegation results)."""
        if self._dc.readyState == "open":
            self._dc.send(json.dumps(event))

    async def close(self) -> None:
        if self.thread_id:
            with contextlib.suppress(Exception):  # hanging up: best effort
                await self._srv.request(
                    "thread/realtime/stop", {"threadId": self.thread_id}, timeout=10
                )
        await self._pc.close()
        if self._drain_task:
            self._drain_task.cancel()
        await self._srv.close()
