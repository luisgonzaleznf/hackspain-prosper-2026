"""Agent-initiated hang-up: end the call once the agent has said goodbye.

The voice model usually waits for the caller to hang up after closing the call
("…Have a good day"), which on a real PSTN line can leave dead air for tens of
seconds. When the agent's own transcript closes the call — a goodbye after an
outcome is staged, or a terminal report (NO_ACTION / ESCALATE) — the watcher
ends the transport session so the carrier hangs up. Any caller speech cancels
it: a goodbye that is answered is not an ending. A tool still running (the
booking write behind the goodbye) holds the hang-up until it lands.

Scored calls never auto-close: the platform owns hang-up there, and a mid-call
farewell ("…have a good day" after booking three of ten) must not end the call
while the caller's next request is still to come.
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
    """Caller speech or sound after the goodbye reopens the call — unless the
    caller's own words are a farewell. The common ending is the agent saying
    "Adiós" and the caller replying "gracias, adiós": the watcher must still
    fire, which is the whole point. Mirrors deadair.py, which resets said_bye
    only on non-goodbye caller speech.
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
    """Raw caller audio above the speech floor: the same reopen rule applies.

    Transcript events lag the caller's audio by 1-2 s (deadair.py), so the
    audio path is what keeps a caller mid-sentence safe during the grace.
    """
    caller_reopened_call(session)


async def watch(session: CallSession, end_call) -> None:
    """End the transport session once the agent has closed the call.

    `end_call` is the voice layer's own teardown (cancel the pipeline runner);
    it must not raise. Held while any clinic tool is in flight, and the arm is
    re-checked through the grace so a caller who resumes mid-grace is safe.
    """
    while True:
        await asyncio.sleep(POLL_SECS)
        if not session.agent_finished or session.in_flight_tools > 0:
            continue
        deadline = time.monotonic() + GRACE_SECS
        while time.monotonic() < deadline:
            await asyncio.sleep(POLL_SECS)
            if not session.agent_finished or session.in_flight_tools > 0:
                break
        else:
            session.log("autohangup.fired", action=session.actions[-1].get("action"))
            logger.info(f"call {session.call_id}: agent closed the call, hanging up")
            try:
                await end_call()
            except Exception as e:  # the socket close path logs its own errors
                session.log("autohangup.error", error=repr(e))
            return
