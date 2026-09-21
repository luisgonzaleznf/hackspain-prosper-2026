"""Agent-initiated hang-up: end the call once the agent has said goodbye.

The voice model usually waits for the caller to hang up after closing the call
("…Have a good day"), which on a real PSTN line can leave dead air for tens of
seconds. When the agent's own transcript closes the call — a goodbye after an
outcome is staged, or a terminal report (NO_ACTION / ESCALATE) — the watcher
ends the transport session so the carrier hangs up. Any caller speech cancels
it: a goodbye that is answered is not an ending. A tool still running (the
booking write behind the goodbye) holds the hang-up until it lands.
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

    if session.actions and is_goodbye(text):
        session.agent_finished = True
        session.log("autohangup.armed", trigger="goodbye", text=text)


def caller_reopened_call(session: CallSession) -> None:
    """Caller speech after the goodbye reopens the call: the hang-up is off."""
    if session.agent_finished:
        session.agent_finished = False
        session.log("autohangup.cancelled", reason="caller_spoke")


async def watch(session: CallSession, end_call) -> None:
    """End the transport session once the agent has closed the call.

    `end_call` is the voice layer's own teardown (cancel the pipeline runner);
    it must not raise. Held while any clinic tool is in flight.
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
