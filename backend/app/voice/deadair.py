"""Dead-air re-prompt: when the line has gone quiet after the agent spoke, ask whether the caller
is still there instead of letting the carrier hang up on the silence.

Test callers hung up about 30-45 s after our last audible audio (run 15f7762b: 9 calls cut
as agent_silence 34.5-36.4 s after it). Pure logic, fed signals and a clock: `DeadAirWatch` says
when to re-prompt, `observe` turns the voice's events into those signals.

Caller speech is what the voice model itself heard (its caller-transcript events), not raw
loudness: a bad line carries a noise bed under the whole call, and noise must not count as speech.
"""

from __future__ import annotations

import os
import re
import unicodedata
from pathlib import Path


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.environ[name])
    except (KeyError, ValueError):
        return default


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.environ[name])
    except (KeyError, ValueError):
        return default


# A/B-testable via env, read once at import: WATCHDOG_SILENCE_S, WATCHDOG_REPEAT_S, WATCHDOG_MAX.
# 12 s, not 8: callers pause for 8 s, and ~40% of the test callers' ordinary replies arrived
# 8-15 s after our turn. 12/22/32 s still beats the ~35 s cut.
QUIET_SECS = _env_float("WATCHDOG_SILENCE_S", 12.0)  # nothing audible either way for this long...
EVERY_SECS = _env_float("WATCHDOG_REPEAT_S", 10.0)  # ...and at least this long since last prompt
MAX_IN_ROW = _env_int("WATCHDOG_MAX", 3)  # stop after this many unanswered re-prompts
# Late caller fragments reset the in-a-row count (test call 08efe9f8: 10 nudges in one call,
# on top of delayed replies), so the whole call has a ceiling too.
MAX_PER_CALL = _env_int("WATCHDOG_MAX_PER_CALL", 5)
# Opt-in (0 = off) until one live check: the voice model normally closes a caller turn ~1.8 s after
# the caller's audio stops arriving (p90 2.7 s), but in one test run 10 turns sat open 8-14.5 s
# and each closed only when a nudge was appended, which then replaced the answer. After this long
# with the turn open and no caller speech arriving, ask for a response instead
# (`response.create` on the data channel: in the v3 client-event enum, unverified on the
# subscription).
STUCK_TURN_SECS = _env_float("STUCK_TURN_SECS", 0.0)
BUSY_MAX_SECS = 20.0  # a lookup or brain turn open longer than this no longer holds it back
# Caller speech on the line itself, ahead of any transcript (they lag 1-2 s, and 41 of 176
# test-caller replies arrived 10-15 s after our turn): never nudge within this long of it. Speech is
# audio well above the line's own noise floor, so a bad line's noise bed does not count.
CALLER_QUIET_SECS = 4.0
SPEECH_OVER_FLOOR = 3.0  # ~+10 dB over the floor
MIN_SPEECH_RMS = 300.0
FLOOR_RISE = 0.002  # per frame: a steady noise bed lifts the floor within ~10 s of 20 ms frames
# When the brain's turn ends the voice still has to start saying its answer: never re-prompt
# over it (a "yes, I'm here" could be read as accepting a slot the caller never heard).
ANSWER_GRACE_SECS = 3.0

REPROMPTS = {"en": "Are you still there?", "es": "¿Sigue ahí?", "ca": "Encara hi sou?"}
# Every other nudge is not a question: a caller whose reply is merely late is not interrogated,
# and a stray "yes" cannot be read as consent to whatever the agent said last.
STILL_HERE = {
    "en": "I'm still here, take your time.",
    "es": "Sigo aquí, tómese su tiempo.",
    "ca": "Continuo aquí, prengui's el temps que necessiti.",
}

# The voice model holding a caller turn open without answering it (ad8cd801: the caller's DNI
# came in at ~110 s, the turn stayed open 117.8-136.5 s, and "Are you still there?" replaced the
# answer): ask for it again, so fresh audio reaches the model and the brain.
REPEAT = {
    "en": "Sorry, I didn't catch that. Could you say it again?",
    "es": "Perdone, no le he entendido bien. ¿Me lo puede repetir?",
    "ca": "Perdoni, no l'he entès bé. M'ho pot repetir?",
}

# The same lines pre-rendered (macOS `say`, 8 kHz mono): played straight into the call when the
# voice model ignores the request to speak (appendSpeech is best-effort: in evals' dropout call
# all 3 nudges were appended to its context and none was spoken).
CLIPS_DIR = Path(__file__).parent / "clips"


def clip_path(line: str) -> Path | None:
    for kind, lines in (("ask", REPROMPTS), ("still", STILL_HERE), ("repeat", REPEAT)):
        for lang, text in lines.items():
            if text == line:
                return CLIPS_DIR / f"{kind}_{lang}.wav"
    return None


# Words that give away a Spanish or Catalan caller; anything else gets English.
_HINTS = {
    "ca": {"sisplau", "gràcies", "vull", "necessito", "què", "és", "amb", "d'acord", "doncs"},
    "es": {"por", "favor", "gracias", "quiero", "necesito", "qué", "vale", "hola", "usted"},
}


# The agent closing the call. With an outcome recorded, the call is over: never keep it talking.
_BYE = re.compile(
    r"\b(goodbye|bye|take care(?! of)|have a (good|nice|great|lovely) (day|afternoon|evening|weekend)"
    r"|adios|hasta (luego|pronto)|que (tenga|pase) (usted )?(un )?buena? (dia|tarde|fin de semana)"
    r"|adeu|fins (aviat|despres|ara)|que vagi be|passi-ho be|que tingui (un )?bon dia)\b"
)


def _fold(text: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFKD", text.lower()) if not unicodedata.combining(c)
    )


def is_goodbye(text: str) -> bool:
    return bool(_BYE.search(_fold(text)))


def language_of(text: str) -> str:
    words = set(re.findall(r"[\wà-ÿ']+", text.lower()))
    scores = {lang: len(words & hints) for lang, hints in _HINTS.items()}
    lang = max(scores, key=lambda k: scores[k])
    return lang if scores[lang] else "en"


class DeadAirWatch:
    def __init__(
        self,
        quiet_secs: float = QUIET_SECS,
        every_secs: float = EVERY_SECS,
        max_in_row: int = MAX_IN_ROW,
        max_per_call: int = MAX_PER_CALL,
        stuck_turn_secs: float = STUCK_TURN_SECS,
    ) -> None:
        self.quiet_secs, self.every_secs, self.max_in_row = quiet_secs, every_secs, max_in_row
        self.max_per_call = max_per_call
        self.stuck_turn_secs = stuck_turn_secs
        self.total = 0  # nudges spoken in this call
        self.agent_spoke = False  # nothing to re-prompt before the agent has said anything
        self.last_heard = 0.0  # last audible audio either way
        self.last_prompt: float | None = None
        self.in_row = 0
        self.lang = "en"
        self._tools = 0  # tool calls in flight (they always end, even when the handler raises)
        self._tools_since = 0.0
        # The brain turn is a flag, not a count: a lost turn/completed must not leave the guard
        # stuck on (or off) for the rest of the call. A new turn/started replaces the open one.
        self._turn_since: float | None = None
        self.recorded = False  # an outcome is staged (a record_* tool succeeded)
        self.said_bye = False  # the agent's last words closed the call
        self.caller_turn_since: float | None = None  # a caller turn the voice model has open
        self._released_turn: float | None = None  # the open caller turn already released
        # The line's noise floor (inbound RMS). Starts at 0, not at the first frame: a call can
        # open mid-word; a noise bed lifts it within a few seconds.
        self._floor = 0.0
        self._caller_sound_at = float("-inf")  # last inbound frame that sounded like speech

    def agent_audible(self, now: float) -> None:
        self.agent_spoke = True
        self.last_heard = now

    def caller_heard(self, now: float, text: str = "") -> None:
        self.last_heard = now
        self.in_row = 0
        if text.strip() and not is_goodbye(text):
            self.said_bye = False  # the caller wants something more: the call goes on
        # Keep the last non-English detection: ID dictation ("cuatro, ocho...") has no hint words
        # and must not flip a Spanish call's re-prompt to English.
        if text.strip() and (found := language_of(text)) != "en":
            self.lang = found

    @property
    def caller_turn_open(self) -> bool:
        return self.caller_turn_since is not None

    def turn_stuck(self, now: float) -> bool:
        """The voice model sits on a finished caller turn: time to ask it for a response."""
        since = self.caller_turn_since
        if not self.stuck_turn_secs or since is None or self._released_turn == since:
            return False
        if self._held(now):
            return False  # the brain is working on it
        quiet = now - self._caller_sound_at
        return now - since >= self.stuck_turn_secs and quiet >= self.stuck_turn_secs

    def turn_released(self) -> None:
        self._released_turn = self.caller_turn_since  # once per caller turn

    def caller_level(self, now: float, rms: float) -> None:
        """One inbound audio frame's RMS. Falls to quiet frames at once, rises slowly."""
        if rms < self._floor:
            self._floor = rms
        else:
            self._floor += (rms - self._floor) * FLOOR_RISE
        if rms > max(self._floor * SPEECH_OVER_FLOOR, MIN_SPEECH_RMS):
            self._caller_sound_at = now

    def agent_said(self, text: str) -> None:
        self.said_bye = is_goodbye(text)

    def begin_busy(self, now: float) -> None:
        """A tool call starts: a lookup or a booking write."""
        if not self._tools:
            self._tools_since = now
        self._tools += 1

    def end_busy(self, now: float) -> None:
        self._tools = max(0, self._tools - 1)
        self._settled(now)

    def begin_turn(self, now: float) -> None:
        self._turn_since = now

    def end_turn(self, now: float) -> None:
        self._turn_since = None
        self._settled(now)

    def _settled(self, now: float) -> None:
        # Nothing in flight any more: the voice still has to start saying the answer.
        if not self._tools and self._turn_since is None:
            self.last_heard = max(self.last_heard, now - self.quiet_secs + ANSWER_GRACE_SECS)

    def _held(self, now: float) -> bool:
        tools = self._tools and now - self._tools_since < BUSY_MAX_SECS
        turn = self._turn_since is not None and now - self._turn_since < BUSY_MAX_SECS
        return bool(tools or turn)

    def due(self, now: float) -> bool:
        if not self.agent_spoke or self.in_row >= self.max_in_row:
            return False
        if self.total >= self.max_per_call:
            return False
        if self.recorded and self.said_bye:
            return False  # the call is finished: the caller hanging up is the right ending
        if self._held(now):
            return False  # never over a lookup or a booking write
        if now - self._caller_sound_at < CALLER_QUIET_SECS:
            return False  # the caller is (or just was) talking
        if now - self.last_heard < self.quiet_secs:
            return False
        return self.last_prompt is None or now - self.last_prompt >= self.every_secs

    @property
    def line(self) -> str:
        """What to say, in the caller's language: the question, then a neutral line, alternating;
        or, while the voice model sits on an unanswered caller turn, a request to repeat it."""
        if self.caller_turn_open:
            return REPEAT[self.lang]
        return (REPROMPTS if self.total % 2 == 0 else STILL_HERE)[self.lang]

    def prompted(self, now: float) -> str:
        """Record a re-prompt that was spoken; returns its line."""
        said = self.line
        self.in_row += 1
        self.total += 1
        self.last_prompt = now
        self.last_heard = now
        return said

    def say_failed(self, now: float) -> None:
        """The re-prompt was not spoken: it does not count, but wait a full interval to retry."""
        self.last_prompt = now


def observe(watch: DeadAirWatch, ev: dict, now: float) -> None:
    """Feed one voice/brain event (CodexLivePeer's on_event shape) into the watch."""
    kind = ev.get("type") or ev.get("method")
    params = ev.get("params") or {}
    if kind in ("input_transcript.added", "turn.created", "turn.done"):
        role = (ev.get("turn") or {}).get("role", "")
        if kind == "input_transcript.added" or role == "user":
            watch.caller_heard(now)
        if kind == "turn.created" and role in ("user", "assistant"):
            watch.caller_turn_since = now if role == "user" else None
        elif kind == "turn.done" and role == "user":
            watch.caller_turn_since = None
    elif kind == "thread/realtime/transcript/done":
        if params.get("role") == "user":
            watch.caller_heard(now, params.get("text") or "")
        elif params.get("role") == "assistant":
            watch.agent_said(params.get("text") or "")
    elif kind == "turn/started":
        watch.begin_turn(now)
    elif kind == "turn/completed":
        watch.end_turn(now)
