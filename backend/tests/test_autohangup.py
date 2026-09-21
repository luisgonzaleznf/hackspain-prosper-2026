"""Auto hang-up (app/voice/autohangup.py): the agent's goodbye ends the call.

The watcher must fire only after the agent's own transcript closed the call,
hold while a clinic tool is in flight, and stand down when the caller speaks.
Demo calls only: scored calls never auto-close (the platform owns hang-up).
"""

import asyncio

from app.session import CallSession
from app.voice import autohangup


def demo_session(call_id: str) -> CallSession:
    session = CallSession(call_id=call_id, demo_mode=True)
    session.actions.append({"action": "BOOK", "patient_id": "P1"})
    return session


def test_goodbye_after_outcome_arms_and_fires():
    async def run():
        session = demo_session("autohangup-1")
        autohangup.agent_closed_call(session, "It is booked for Tuesday. Have a good day!")
        assert session.agent_finished
        fired = asyncio.Event()

        async def end_call():
            fired.set()

        task = asyncio.create_task(autohangup.watch(session, end_call))
        try:
            await asyncio.wait_for(fired.wait(), timeout=5)
        finally:
            task.cancel()
        assert session.agent_finished

    asyncio.run(run())


def test_goodbye_without_outcome_does_not_arm():
    session = CallSession(call_id="autohangup-2", demo_mode=True)
    autohangup.agent_closed_call(session, "Have a good day!")
    assert not session.agent_finished


def test_scored_call_never_arms_even_with_outcome_and_goodbye():
    session = CallSession(call_id="autohangup-scored", demo_mode=False)
    session.actions.append({"action": "BOOK", "patient_id": "P1"})
    autohangup.agent_closed_call(session, "Booked for Tuesday. Have a good day!")
    assert not session.agent_finished, "a scored call must not auto-close"


def test_caller_speech_cancels_the_fired_hangup():
    async def run():
        session = demo_session("autohangup-3")
        autohangup.agent_closed_call(session, "Then I cannot help with that. Goodbye!")
        autohangup.caller_reopened_call(session, "Actually, wait, one more thing")
        assert not session.agent_finished

    asyncio.run(run())


def test_caller_farewell_does_not_cancel_the_hangup():
    """The agent says "Adiós", the caller replies "gracias, adiós": the call ends."""
    session = demo_session("autohangup-4b")
    autohangup.agent_closed_call(session, "Adiós!")
    autohangup.caller_reopened_call(session, "gracias, adiós")
    assert session.agent_finished


def test_caller_audio_cancels_the_hangup():
    """Audio above the speech floor cancels even without a committed transcript."""
    async def run():
        session = demo_session("autohangup-4c")
        autohangup.agent_closed_call(session, "Booked. Take care!")
        autohangup.caller_made_sound(session)
        assert not session.agent_finished

    asyncio.run(run())


def test_in_flight_tool_holds_the_hangup_until_it_lands():
    async def run():
        session = demo_session("autohangup-4")
        autohangup.agent_closed_call(session, "Booked. Take care!")
        fired = asyncio.Event()

        async def end_call():
            fired.set()

        task = asyncio.create_task(autohangup.watch(session, end_call))
        await asyncio.sleep(0.6)  # longer than the watcher's poll, shorter than the grace
        assert not fired.is_set(), "hang-up fired while the booking write was in flight"
        session.in_flight_tools = 0
        try:
            await asyncio.wait_for(fired.wait(), timeout=5)
        finally:
            task.cancel()

    asyncio.run(run())
