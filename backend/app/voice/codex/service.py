"""Pipecat processor: GPT-Live on the Codex subscription as the whole voice stack.

Sits where STT -> LLM -> TTS would: consumes the caller's InputAudioRawFrames, pushes
the agent's voice downstream as OutputAudioRawFrames. GPT-Live does its own turn-taking
and barge-in, and we relay its audio in real time, so there is no backlog to flush.
"""

from __future__ import annotations

import array
import asyncio
import json
import math
import time
import wave

from loguru import logger
from pipecat.audio.utils import create_file_resampler
from pipecat.frames.frames import (
    CancelFrame,
    EndFrame,
    Frame,
    InputAudioRawFrame,
    OutputAudioRawFrame,
)
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor, FrameProcessorSetup

from app.voice.codex.peer import CodexLivePeer
from app.voice.deadair import MIN_SPEECH_RMS, DeadAirWatch, clip_path, observe

SILENCE_PEAK = 300  # int16 peak below which a 20ms chunk counts as silence
HANGOVER_MS = 600  # keep relaying through pauses shorter than this
# A nudge counts as spoken by the model only if it starts talking this soon after the request
# (evals: 9 of 12 spoken within ~0.6 s); otherwise the pre-rendered clip plays instead. Test run
# fe845bd3: 94 of 96 started within 2 s but one took 4.2 s, and the clip would have doubled it.
CONFIRM_SECS = 5.0
# No event of any kind from the voice session for this long: log it (evals saw two concurrent
# sessions freeze at the same instant, one mid-word). Diagnostic only; the nudge still runs.
STALL_SECS = 8.0
MAX_RECOVERIES = 2
RECOVERY_PROMPT = "I lost the last few words. Please repeat your last sentence."

_clips: dict[tuple[str, int], bytes] = {}


async def _clip_pcm(line: str, rate: int) -> bytes | None:
    """The pre-rendered clip of `line` as PCM16 at `rate`, or None if there is none."""
    path = clip_path(line)
    if path is None or not path.exists():
        return None
    if (line, rate) not in _clips:
        with wave.open(str(path)) as w:
            pcm, src_rate = w.readframes(w.getnframes()), w.getframerate()
        _clips[(line, rate)] = await create_file_resampler().resample(pcm, src_rate, rate)
    return _clips[(line, rate)]


# Data-channel ("oai") events that arrive every ~200 ms of speech: the transcripts already
# carry their content, so logging them would only bury the rare events that explain a stall.
_CHATTY = {"turn.delta", "input_transcript.added", "output_transcript.added"}


def _worth_logging(ev: dict) -> bool:
    """Everything the voice and the brain report, minus per-fragment noise.

    The voice's own events (turn.created/turn.done with a role, session.*, errors, anything
    new) are what show whether a caller turn was ever committed when a call goes silent.
    """
    source = ev.get("source")
    if source == "codex":
        return ev.get("method") != "thread/realtime/transcript/done"
    if source in ("oai", "brain"):
        kind = str(ev.get("type", ""))
        return kind not in _CHATTY and kind != "delegation.context.appended"
    return False


class CodexLiveService(FrameProcessor):
    def __init__(
        self,
        *,
        prompt: str,
        greeting: str | None = None,
        voice: str = "cove",
        on_transcript=None,
        tools: list[dict] | None = None,
        brain_instructions: str | None = None,
        on_tool_call=None,
        on_brain_event=None,
        on_caller_speech=None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self._prompt = prompt
        self._greeting = greeting
        self._voice = voice
        self._on_transcript = on_transcript  # (role, text) -> None
        self._on_caller_speech = on_caller_speech  # () -> None: caller audio above the floor
        self._tools = tools
        self._brain_instructions = brain_instructions
        self._on_tool_call = self._tool_call if on_tool_call else None
        self._tool_handler = on_tool_call  # async (name, args) -> dict
        self._on_brain_event = on_brain_event  # (event, detail) -> None: turns, handoffs, errors
        self._peer: CodexLivePeer | None = None
        self._out_rate = 24000
        self._quiet_ms = HANGOVER_MS  # start "not speaking"
        self._watch = DeadAirWatch()
        self._watch_task: asyncio.Task | None = None
        self._agent_started_at = 0.0  # last assistant turn.created or loud agent audio
        self._voice_event_at = time.monotonic()  # last event from the voice session itself
        self._caller_loud_ms_at_event = 0
        self._stalled = False
        self._recoveries = 0
        self._recovering = False
        self._recovery_task: asyncio.Task | None = None
        self._in_rate = 8000
        self.usage: dict = {}

    async def setup(self, setup: FrameProcessorSetup):  # type: ignore[override]  # pipecat's own signature
        await super().setup(setup)
        self._out_rate = setup.audio_out_sample_rate
        self._in_rate = setup.audio_in_sample_rate
        self._peer = self._make_peer()
        await self._peer.start()
        logger.info(f"codex-live connected (thread {self._peer.thread_id})")
        self._voice_event_at = time.monotonic()
        if self._greeting:
            await self._peer.say(self._greeting)
        self._watch_task = self.create_task(self._watch_line(), "dead-air")

    def _make_peer(self) -> CodexLivePeer:
        return CodexLivePeer(
            prompt=self._prompt,
            voice=self._voice,
            in_rate=self._in_rate,
            out_rate=self._out_rate,
            on_audio=self._on_agent_audio,
            on_event=self._on_event,
            tools=self._tools,
            brain_instructions=self._brain_instructions,
            on_tool_call=self._on_tool_call,
        )

    async def _recover_peer(self) -> None:
        if self._recovering or self._recoveries >= MAX_RECOVERIES:
            return
        self._recovering = True
        self._recoveries += 1
        attempt = self._recoveries
        if self._on_brain_event:
            self._on_brain_event("voice.recovering", json.dumps({"attempt": attempt}))
        old, self._peer = self._peer, None
        if old:
            await old.close()
        try:
            peer = self._make_peer()
            self._peer = peer
            await peer.start()
            self._voice_event_at = time.monotonic()
            self._stalled = False
            await peer.say(RECOVERY_PROMPT)
            self._watch.last_heard = self._voice_event_at
            if self._on_brain_event:
                self._on_brain_event("voice.recovered", json.dumps({"attempt": attempt}))
        except Exception as error:
            logger.exception("codex-live recovery failed")
            self._peer = None
            if self._on_brain_event:
                self._on_brain_event(
                    "voice.recovery_failed",
                    json.dumps({"attempt": attempt, "error": repr(error)}),
                )
        finally:
            self._recovering = False

    async def _tool_call(self, name: str, args: dict) -> dict:
        assert self._tool_handler is not None
        self._watch.begin_busy(time.monotonic())  # a lookup or a write: never re-prompt over it
        try:
            result = await self._tool_handler(name, args)
        finally:
            self._watch.end_busy(time.monotonic())
        if name.startswith("record_") and "error" not in result:
            self._watch.recorded = True
        elif name == "clear_recorded_actions" and "error" not in result:
            self._watch.recorded = bool(result.get("everything_recorded"))
        return result

    async def _watch_line(self) -> None:
        """Re-prompt a silent line (app/voice/deadair.py) instead of letting the carrier hang up."""
        while True:
            await asyncio.sleep(1)
            now = time.monotonic()
            if self._peer and not self._stalled and now - self._voice_event_at >= STALL_SECS:
                self._stalled = True
                self._log_stall("voice.stalled", now)
            if self._peer and self._watch.turn_stuck(now):
                self._release_turn(now)
            if not self._peer or not self._watch.due(now):
                continue
            line = self._watch.line
            spoken = await self._nudge(line)
            if spoken == "none":
                self._watch.say_failed(now)  # not counted; retry after a full interval
            else:
                self._watch.prompted(time.monotonic())
            if self._on_brain_event:
                w = self._watch
                detail = {"n": w.in_row, "total": w.total, "lang": w.lang, "text": line}
                detail["spoken"] = spoken
                detail["caller_turn_open"] = w.caller_turn_open
                self._on_brain_event("voice.reprompt", json.dumps(detail, ensure_ascii=False))

    async def _nudge(self, line: str) -> str:
        """Say `line`: "model" if the voice model spoke, "clip" if the recording played, or "none"."""
        asked = time.monotonic()
        try:
            assert self._peer is not None
            await self._peer.say(line)
            deadline = time.monotonic() + CONFIRM_SECS
            while self._agent_started_at <= asked and time.monotonic() < deadline:
                await asyncio.sleep(0.1)
            if self._agent_started_at > asked:
                return "model"
        except Exception as e:
            logger.warning(f"dead-air re-prompt failed: {e!r}")
            if not self._peer or self._recovering:
                return "none"
        pcm = await _clip_pcm(line, self._out_rate)
        if not pcm:
            return "none"
        await self.push_frame(
            OutputAudioRawFrame(audio=pcm, sample_rate=self._out_rate, num_channels=1)
        )
        return "clip"

    def _release_turn(self, now: float) -> None:
        """Ask the voice model to answer the caller turn it is sitting on, without injecting words
        (an appended nudge closes the turn too, but its words replace the answer)."""
        assert self._peer is not None
        w = self._watch
        w.turn_released()
        self._peer.send_event({"type": "response.create"})
        if self._on_brain_event and w.caller_turn_since is not None:
            detail = {
                "open_s": round(now - w.caller_turn_since, 1),
                "quiet_s": round(min(now - w._caller_sound_at, 999.0), 1),
            }
            self._on_brain_event("voice.turn_release", json.dumps(detail))

    def _log_stall(self, event: str, now: float) -> None:
        """voice.stalled / voice.resumed. caller_loud_ms: the caller's speech we sent to OpenAI
        meanwhile; if it is well above zero, the session went deaf rather than the line quiet."""
        if not self._on_brain_event or not self._peer:
            return
        loud = self._peer.audio_stats()["sent_to_openai_loud_ms"] - self._caller_loud_ms_at_event
        detail = {
            "silent_s": round(now - self._voice_event_at, 1),
            "caller_loud_ms": loud,
            "caller_turn_open": self._watch.caller_turn_open,
        }
        self._on_brain_event(event, json.dumps(detail))

    async def cleanup(self):
        await super().cleanup()
        await self._close_peer()

    async def _close_peer(self) -> None:
        if self._watch_task:
            await self.cancel_task(self._watch_task)
            self._watch_task = None
        if self._recovery_task:
            await self.cancel_task(self._recovery_task)
            self._recovery_task = None
        if not self._peer:
            return
        if self._on_brain_event:
            self._on_brain_event("audio.stats", json.dumps(self._peer.audio_stats()))
        await self._peer.close()
        self._peer = None

    async def _on_agent_audio(self, pcm: bytes) -> None:
        # The WebRTC track never stops (silence between turns); only relay speech plus
        # a short hangover so the transport's bot-speaking events mean something.
        chunk_ms = len(pcm) * 1000 // (2 * self._out_rate)
        loud = max((abs(x) for x in array.array("h", pcm)), default=0) > SILENCE_PEAK
        self._quiet_ms = 0 if loud else self._quiet_ms + chunk_ms
        if loud:
            self._agent_started_at = time.monotonic()
            self._watch.agent_audible(self._agent_started_at)
        if self._quiet_ms < HANGOVER_MS:
            await self.push_frame(
                OutputAudioRawFrame(audio=pcm, sample_rate=self._out_rate, num_channels=1)
            )

    def _on_event(self, ev: dict) -> None:
        now = time.monotonic()
        observe(self._watch, ev, now)
        if ev.get("source") == "oai" or str(ev.get("method", "")).startswith("thread/realtime"):
            if self._stalled:
                self._stalled = False
                self._log_stall("voice.resumed", now)
            self._voice_event_at = now
            if self._peer:
                self._caller_loud_ms_at_event = self._peer.audio_stats()["sent_to_openai_loud_ms"]
        if ev.get("type") == "turn.created" and (ev.get("turn") or {}).get("role") == "assistant":
            self._agent_started_at = time.monotonic()
        if (
            ev.get("method") == "thread/realtime/closed"
            and (ev.get("params") or {}).get("reason") == "transport_closed"
            and not self._recovering
            and self._recoveries < MAX_RECOVERIES
        ):
            self._recovery_task = self.create_task(self._recover_peer(), "voice-recovery")
        if ev.get("method") == "thread/realtime/transcript/done":
            p = ev.get("params") or {}
            role, text = p.get("role", "?"), (p.get("text") or "").strip()
            logger.info(f"[{role}] {text}")
            if self._on_transcript:
                self._on_transcript(role, text)
        elif ev.get("type") == "session.usage.updated":
            self.usage = ev.get("usage") or {}
        elif ev.get("method") in ("thread/realtime/error", "error"):
            logger.error(f"codex-live: {ev.get('params')}")
        if self._on_brain_event and _worth_logging(ev):
            name = ev.get("method") or ev.get("type")
            detail = ev.get("params") if ev.get("source") == "codex" else ev
            self._on_brain_event(name, json.dumps(detail, ensure_ascii=False)[:600])

    async def process_frame(self, frame: Frame, direction: FrameDirection):
        await super().process_frame(frame, direction)
        if isinstance(frame, InputAudioRawFrame):
            if self._peer:
                self._peer.push_audio(frame.audio)
            pcm = array.array("h", frame.audio)
            if pcm:
                rms = math.sqrt(sum(x * x for x in pcm) / len(pcm))
                self._watch.caller_level(time.monotonic(), rms)
                if rms >= MIN_SPEECH_RMS and self._on_caller_speech:
                    self._on_caller_speech()
            return  # consumed: the caller's audio goes to GPT-Live, not downstream
        if isinstance(frame, (EndFrame, CancelFrame)):
            await self._close_peer()
        await self.push_frame(frame, direction)
