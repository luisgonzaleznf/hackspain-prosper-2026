"""Agent-initiated hang-up: end the call once the agent has said goodbye.

The voice model usually waits for the caller to hang up after closing the call
("…Have a good day"), which on a real PSTN line can leave dead air for tens of
seconds. When the agent's own transcript closes the call — a goodbye after an
outcome is staged, or a terminal report (NO_ACTION / ESCALATE) — the watcher
ends the transport session so the carrier hangs up.

Caller signals during the grace are weighed, not reflexive:

- Raw audio above the speech floor delays the hang-up (transcripts lag audio by
  1-2 s per deadair.py), but does not clear the arm: the farewell transcript
  that confirms "gracias, adiós" must still let the call end.
- A non-goodbye transcript clears the arm: the caller wants something more.
- A farewell transcript inside the grace lets the hang-up stand even though
  raw audio arrived first.

A tool still running (the booking write behind the goodbye) holds the hang-up
until it lands. Scored calls never auto-close: the platform owns hang-up there,
and a mid-call farewell ("…have a good day" after booking three of ten) must
not end the call while the caller's next request is still to come.
"""

from __future__ import annotations

import asyncio
import time

from loguru import logger

from app.session import CallSession

# Goodbye heard -> session ends after this delay, so the closing words finish
# playing and a caller's "wait, one more thing" still lands.
GRACE_SECS = 3.0
POLL_SECS = 0.25


def agent_closed_call(session: CallSession, text: str) -> None:
    """Feed one agent transcript line to the watcher: does it end the call?"""
    from app.voice.deadair import is_goodbye

    if not session.demo_mode or not session.actions or not is_goodbye(text):
        return
    session.agent_finished = True
    session.log("autohangup.armed", trigger="goodbye", text=text)


def caller_reopened_call(session: CallSession, text: str | None = None) -> None:
    """One committed caller transcript line during the grace.

    A farewell keeps the arm (the agent said goodbye and the caller's reply is
    a goodbye too); any other speech clears it. Mirrors deadair.py, which
    resets said_bye only on non-goodbye caller speech.
    """
    if not session.agent_finished:
        return
    if text is not None:
        from app.voice.deadair import is_goodbye

        if is_goodbye(text):
            return
    session.agent_finished = False
    session.log("autohangup.cancelled", reason="caller_spoke")


def caller_made_sound(session: CallSession) -> None:
    """Raw caller audio above the speech floor: push the hang-up back.

    Transcript events lag the caller's audio by 1-2 s (deadair.py), so audio
    alone must delay the ending — but not cancel it. The farewell transcript
    that lands a moment later still lets the call end; a real request clears
    the arm through caller_reopened_call.
    """
    if session.agent_finished:
        session.caller_sound_at = time.monotonic()


async def watch(session: CallSession, end_call) -> None:
    """End the transport session once the agent has closed the call.

    `end_call` is the voice layer's own teardown (cancel the pipeline runner);
    it must not raise. The grace restarts on raw caller audio and is abandoned
    outright if a committed transcript shows the caller wants something more;
    a farewell transcript inside the grace lets the hang-up stand. A clinic
    tool still in flight holds everything until it lands.
    """
    while True:
        await asyncio.sleep(POLL_SECS)
        if not session.agent_finished or session.in_flight_tools > 0:
            continue
        deadline = time.monotonic() + GRACE_SECS
        while time.monotonic() < deadline:
            await asyncio.sleep(POLL_SECS)
            if not session.agent_finished or session.in_flight_tools > 0:
                break  # disarmed or busy: the outer loop re-arms if it comes back
            sound_at = getattr(session, "caller_sound_at", None)
            if sound_at is not None and sound_at + GRACE_SECS > deadline:
                deadline = sound_at + GRACE_SECS  # fresh audio: fire 3 s after it, not before
        else:
            session.log("autohangup.fired", action=session.actions[-1].get("action"))
            logger.info(f"call {session.call_id}: agent closed the call, hanging up")
            try:
                await end_call()
            except Exception as e:  # the socket close path logs its own errors
                session.log("autohangup.error", error=repr(e))
            return
