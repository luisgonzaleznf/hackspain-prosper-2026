"""Record both legs of a call straight off the wire, and summarise how the call sounded.

The taps sit on the call's WebSocket, below any voice layer, so what is kept is exactly what
the carrier sent us (the caller) and what we sent back (the agent), each with the monotonic time
it crossed. During the call the taps only append to lists and log one `first_agent_audio` event.
After the outcome is logged, `save()` runs off the event loop and writes, for every call
(gitignored):

- logs/audio/<call_id>.wav          stereo 8 kHz: left the caller, right the agent, one timeline
- logs/audio/<call_id>.timing.json  per-frame arrival/send times, for later transport analysis

and returns the summary the server logs to the call's JSONL as `audio.timeline`.
"""

from __future__ import annotations

import asyncio
import audioop  # stdlib until 3.13; pipecat uses it too
import base64
import json
import math
import statistics
import time
import wave
from contextlib import suppress
from itertools import pairwise
from pathlib import Path
from typing import Any

RATE = 8000
FRAME = 160  # 20 ms of 8 kHz audio: the unit every metric below is measured in
AUDIBLE_RMS = 200  # ~-44 dBFS, as in evals/audio.py
MAX_S = 300  # stop recording after 5 min
STALL_S = (
    0.2  # caller frames arriving this far apart: codex/peer.py drops audio past 200 ms backlog
)
HOLE_S = 0.08  # an agent chunk this late after the last one ends is a gap the caller hears
PAUSE_S = 1.0  # a longer gap after speech is a pause between turns, not a stutter
MERGE_S = 0.4  # speech bursts closer than this are one turn
MIN_TURN_S = 0.15  # shorter bursts are clicks, not speech
BARGE_S = 0.1  # less overlap than this is turn-taking at the seam, not an interruption

# Flag thresholds: the lines worth reading first in a batch of calls.
SLOW_GREETING_S = 5.0
DEAD_AIR_S = 6.0  # neither side audible; carriers' silence windows vary (evals guess 10 s)
SLOW_RESPONSE_S = 5.0
SLOW_YIELD_S = 2.0
NOISY_SNR_DB = 15.0
CLIPPED_PCT = 0.1


class WireRecorder:
    def __init__(self, t0: float | None = None) -> None:
        self.t0 = time.monotonic() if t0 is None else t0
        self.inbound: list[
            tuple[float, float | None, bytes]
        ] = []  # (arrival s, media.timestamp s, µ-law)
        self.outbound: list[tuple[float, bytes]] = []  # (send s, µ-law)
        self.clears = 0
        self._greeted = False

    def tap(self, websocket: Any, session: Any) -> None:
        """Wrap the socket's receive/send_text. Recording can fail; the call never does."""
        receive, send_text = websocket.receive, websocket.send_text

        async def receive_and_record() -> dict:
            message = await receive()
            text = message.get("text")
            if text and '"media"' in text:
                with suppress(Exception):
                    self._inbound(json.loads(text))
            return message

        async def send_and_record(data: str) -> None:
            with suppress(Exception):
                self._outbound(data, session)
            await send_text(data)

        websocket.receive = receive_and_record
        websocket.send_text = send_and_record

    def _inbound(self, message: dict) -> None:
        now = time.monotonic() - self.t0
        if message.get("event") != "media" or now > MAX_S:
            return
        media = message["media"]
        stamp = media.get("timestamp")  # ms since the stream started, a string on the wire
        self.inbound.append(
            (now, int(stamp) / 1000 if stamp else None, base64.b64decode(media["payload"]))
        )

    def _outbound(self, data: str, session: Any) -> None:
        now = time.monotonic() - self.t0
        if '"clear"' in data:
            self.clears += 1
        if '"media"' not in data or now > MAX_S:
            return
        ulaw = base64.b64decode(json.loads(data)["media"]["payload"])
        self.outbound.append((now, ulaw))
        if not self._greeted and _rms(ulaw) > AUDIBLE_RMS:
            self._greeted = True
            session.log("first_agent_audio", ms=round(now * 1000))

    async def save(self, call_id: str, directory: Path) -> dict:
        return await asyncio.to_thread(self._save, call_id, directory)

    def _save(self, call_id: str, directory: Path) -> dict:
        caller, stalls, backlog = self._caller_track()
        agent, underruns = self._agent_track()
        n = max(len(caller), len(agent))
        caller += bytes(n - len(caller))
        agent += bytes(n - len(agent))
        summary = summarise(
            bytes(caller),
            bytes(agent),
            caller_ulaw=b"".join(u for _, _, u in self.inbound),
            agent_ulaw=b"".join(u for _, u in self.outbound),
            stalls=stalls,
            connect_backlog_s=backlog,
            underruns=underruns,
            clears=self.clears,
        )
        directory.mkdir(parents=True, exist_ok=True)
        wav = directory / f"{call_id}.wav"
        with wave.open(str(wav), "wb") as out:
            out.setnchannels(2)
            out.setsampwidth(2)
            out.setframerate(RATE)
            out.writeframes(
                audioop.add(
                    audioop.tostereo(bytes(caller), 2, 1, 0),
                    audioop.tostereo(bytes(agent), 2, 0, 1),
                    2,
                )
            )
        (directory / f"{call_id}.timing.json").write_text(
            json.dumps(
                {
                    "inbound_ms": [
                        [round(t * 1000, 1), None if s is None else round(s * 1000)]
                        for t, s, _ in self.inbound
                    ],
                    "outbound_ms": [[round(t * 1000, 1), len(u)] for t, u in self.outbound],
                    "clears": self.clears,
                }
            )
        )
        summary["wav"] = str(wav)
        return summary

    def _caller_track(self) -> tuple[bytearray, list[float], float]:
        """Place each caller frame by its media.timestamp on our clock. The anchor is the least
        delayed frame: the first ones queue while CallSession.start() does its lookups."""
        if not self.inbound:
            return bytearray(), [], 0.0
        stamps = [
            s if s is not None else i * FRAME / RATE for i, (_, s, _) in enumerate(self.inbound)
        ]
        offset = min(t - s for (t, _, _), s in zip(self.inbound, stamps, strict=True))
        placed = [(s + offset, u) for s, (_, _, u) in zip(stamps, self.inbound, strict=True)]
        arrivals = [t for t, _, _ in self.inbound]
        stalls = [b - a for a, b in pairwise(arrivals) if b - a > STALL_S]
        return _lay(placed), stalls, arrivals[0] - placed[0][0]

    def _agent_track(self) -> tuple[bytearray, list[float]]:
        """Place agent audio the way the far end plays it: back to back while chunks arrive on
        time, re-anchored at the send time after a gap. Placing every chunk at its own send time
        would turn millisecond pacing jitter into crackle that was never on the wire."""
        placed: list[tuple[float, bytes]] = []
        underruns: list[float] = []
        end, prev_loud = -math.inf, False
        for sent, ulaw in self.outbound:
            gap = sent - end
            if gap > HOLE_S:
                if prev_loud and gap < PAUSE_S:
                    underruns.append(gap)
                start = sent
            else:
                start = end
            placed.append((start, ulaw))
            end = start + len(ulaw) / RATE
            prev_loud = _rms(ulaw) > AUDIBLE_RMS
        return _lay(placed), underruns


def _rms(ulaw: bytes) -> int:
    return audioop.rms(audioop.ulaw2lin(ulaw, 2), 2)


def _lay(placed: list[tuple[float, bytes]]) -> bytearray:
    """Decode µ-law chunks into one PCM16 track at their positions (seconds)."""
    if not placed:
        return bytearray()
    size = max(round(at * RATE) + len(u) for at, u in placed)
    track = bytearray(2 * min(size, MAX_S * RATE))
    for at, ulaw in placed:
        i = 2 * max(0, round(at * RATE))
        pcm = audioop.ulaw2lin(ulaw, 2)[: max(0, len(track) - i)]
        track[i : i + len(pcm)] = pcm
    return track


def _frame_rms(pcm: bytes) -> list[int]:
    step = 2 * FRAME
    return [audioop.rms(pcm[i : i + step], 2) for i in range(0, len(pcm) - step + 1, step)]


def _dbfs(rms: float) -> float | None:
    return round(20 * math.log10(rms / 32768), 1) if rms > 0 else None


def _turns(loud: list[bool]) -> list[tuple[float, float]]:
    """Frames over the threshold -> (start s, end s) speech turns, short gaps merged."""
    turns: list[list[float]] = []
    for i, on in enumerate(loud):
        if not on:
            continue
        t = i * FRAME / RATE
        if turns and t - turns[-1][1] <= MERGE_S:
            turns[-1][1] = t + FRAME / RATE
        else:
            turns.append([t, t + FRAME / RATE])
    return [(a, b) for a, b in turns if b - a >= MIN_TURN_S]


def _longest_run(flags: list[bool]) -> tuple[int, int]:
    """(length, start index) of the longest run of True."""
    best = (0, 0)
    run = 0
    for i, f in enumerate(flags):
        run = run + 1 if f else 0
        if run > best[0]:
            best = (run, i - run + 1)
    return best


def _clipped_pct(ulaw: bytes) -> float:
    # µ-law 0x80 / 0x00 are the loudest codes (±32124): a sample there hit the ceiling.
    return round(100 * (ulaw.count(b"\x80") + ulaw.count(b"\x00")) / len(ulaw), 3) if ulaw else 0.0


def summarise(
    caller: bytes,
    agent: bytes,
    *,
    caller_ulaw: bytes = b"",
    agent_ulaw: bytes = b"",
    stalls: list[float] = (),
    connect_backlog_s: float = 0.0,
    underruns: list[float] = (),
    clears: int = 0,
) -> dict:
    """Metrics for one call from its two time-aligned PCM16 tracks (8 kHz, equal length)."""
    sec = FRAME / RATE
    caller_rms, agent_rms = _frame_rms(caller), _frame_rms(agent)
    frames = len(agent_rms)

    agent_loud = [r > AUDIBLE_RMS for r in agent_rms]
    first = agent_loud.index(True) * sec if any(agent_loud) else None
    silent, silent_at = _longest_run([not x for x in agent_loud])
    agent_turns = _turns(agent_loud)

    # Caller: the noise floor is what the line carries while the caller listens, i.e. while the
    # agent talks. A TV or street bed sits far above its own quietest moments, so the quietest
    # tenth of the call (the fallback when the agent never spoke) reads it several dB too low.
    listening = sorted(r for r, on in zip(caller_rms, agent_loud, strict=True) if on)
    if not listening:  # up to the caller's last frame, not over the zeros padding their track
        last = max((i for i, r in enumerate(caller_rms) if r), default=-1)
        listening = sorted(caller_rms[: last + 1])[: (last + 1) // 5]
    floor = listening[len(listening) // 2] if listening else 0
    caller_loud = [r > max(AUDIBLE_RMS, 2 * floor) for r in caller_rms]
    caller_turns = _turns(caller_loud)
    speech = [r for r, on in zip(caller_rms, caller_loud, strict=True) if on]
    level_rms = statistics.median(speech) if speech else 0
    level, noise = _dbfs(level_rms), _dbfs(floor)
    # Speech frames carry the noise too: take its power out before comparing.
    snr = (
        round(10 * math.log10((level_rms**2 - floor**2) / floor**2), 1)
        if floor and level_rms > floor
        else None
    )
    # Dead air: neither side audible, which is how evals/caller.py models the silence cut.
    # ("No audible audio from the agent" alone is longest_silence_s.)
    dead, dead_at = _longest_run(
        [not (a or c) for a, c in zip(agent_loud, caller_loud, strict=False)]
    )

    # Response latency: from the end of the caller's words to the start of the agent's next turn.
    latencies, prev_end = [], -math.inf
    for a0, a1 in agent_turns:
        ends = [c1 for _, c1 in caller_turns if prev_end < c1 <= a0]
        if ends:
            latencies.append(a0 - max(ends))
        prev_end = a1
    # Barge-in: the caller starts while the agent is talking; yield is how long the agent goes on.
    yields = [a1 - c0 for c0, _ in caller_turns for a0, a1 in agent_turns if a0 < c0 < a1 - BARGE_S]

    agent_level = [r for r, on in zip(agent_rms, agent_loud, strict=True) if on]
    summary = {
        "duration_s": round(frames * sec, 1),
        "first_agent_audio_s": None if first is None else round(first, 2),
        "dead_air_s": round(dead * sec, 1),
        "dead_air_at_s": round(dead_at * sec, 1),
        "agent": {
            "talk_s": round(sum(agent_loud) * sec, 1),
            "longest_silence_s": round(silent * sec, 1),
            "longest_silence_at_s": round(silent_at * sec, 1),
            "level_dbfs": _dbfs(statistics.median(agent_level)) if agent_level else None,
            "clipped_pct": _clipped_pct(agent_ulaw),
            "underruns": len(underruns),
            "underrun_max_ms": round(max(underruns, default=0) * 1000),
            "clears": clears,
        },
        "caller": {
            "talk_s": round(sum(caller_loud) * sec, 1),
            "level_dbfs": level,
            "noise_dbfs": noise,  # None: digital silence between words
            "snr_db": snr,
            "clipped_pct": _clipped_pct(caller_ulaw),
            "stalls": len(stalls),
            "stall_max_ms": round(max(stalls, default=0) * 1000),
            "connect_backlog_ms": round(connect_backlog_s * 1000),
        },
        "turns": {
            "responses": len(latencies),
            "latency_p50_s": round(statistics.median(latencies), 2) if latencies else None,
            "latency_max_s": round(max(latencies), 2) if latencies else None,
            "barge_ins": len(yields),
            "yield_max_s": round(max(yields), 2) if yields else None,
        },
    }
    summary["flags"] = _flags(summary)
    return summary


def _flags(s: dict) -> list[str]:
    agent, caller, turns = s["agent"], s["caller"], s["turns"]
    flags = []
    if s["first_agent_audio_s"] is None:
        flags.append("no_agent_audio")
    elif s["first_agent_audio_s"] > SLOW_GREETING_S:
        flags.append(f"slow_greeting:{s['first_agent_audio_s']}s")
    if s["dead_air_s"] >= DEAD_AIR_S:
        to_end = s["dead_air_at_s"] + s["dead_air_s"] >= s["duration_s"] - 0.1
        flags.append(
            f"dead_air:{s['dead_air_s']}s@{s['dead_air_at_s']}s"
            + ("(to hang-up)" if to_end else "")
        )
    if (turns["latency_max_s"] or 0) > SLOW_RESPONSE_S:
        flags.append(f"slow_response:{turns['latency_max_s']}s")
    if (turns["yield_max_s"] or 0) > SLOW_YIELD_S:
        flags.append(f"slow_yield:{turns['yield_max_s']}s")
    if agent["underruns"]:
        flags.append(f"agent_underruns:{agent['underruns']}x,max{agent['underrun_max_ms']}ms")
    if caller["stalls"]:
        flags.append(f"caller_stalls:{caller['stalls']}x,max{caller['stall_max_ms']}ms")
    if caller["snr_db"] is not None and caller["snr_db"] < NOISY_SNR_DB:
        flags.append(f"noisy_caller:{caller['snr_db']}dB")
    for leg in ("agent", "caller"):
        if s[leg]["clipped_pct"] > CLIPPED_PCT:
            flags.append(f"{leg}_clipping:{s[leg]['clipped_pct']}%")
    return flags
