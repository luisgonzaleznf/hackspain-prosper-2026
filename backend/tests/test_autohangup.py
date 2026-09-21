"""Auto hang-up (app/voice/autohangup.py): the agent's goodbye ends the call.

The watcher must fire only after the agent's own transcript closed the call,
hold while a clinic tool is in flight, and weigh caller signals during the
grace: raw audio delays it, a farewell transcript keeps it, real speech clears
it. Demo calls only: scored calls never auto-close (the platform owns hang-up).
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


def test_caller_speech_clears_the_armed_hangup():
    async def run():
        session = demo_session("autohangup-3")
        autohangup.agent_closed_call(session, "Then I cannot help with that. Goodbye!")
        autohangup.caller_reopened_call(session, "Actually, wait, one more thing")
        assert not session.agent_finished

    asyncio.run(run())


def test_caller_farewell_keeps_the_arm():
    """The agent says "Adiós", the caller replies "gracias, adiós": the call ends."""
    session = demo_session("autohangup-4b")
    autohangup.agent_closed_call(session, "Adiós!")
    autohangup.caller_reopened_call(session, "gracias, adiós")
    assert session.agent_finished


def test_caller_audio_delays_but_does_not_cancel():
    """Audio inside the grace pushes the deadline back; the arm survives."""
    async def run():
        session = demo_session("autohangup-4c")
        autohangup.agent_closed_call(session, "Booked. Take care!")
        autohangup.caller_made_sound(session)
        assert session.agent_finished, "raw audio must not disarm the hang-up"
        assert session.caller_sound_at is not None
        fired = asyncio.Event()

        async def end_call():
            fired.set()

        task = asyncio.create_task(autohangup.watch(session, end_call))
        # the watcher keeps waiting through fresh audio, then fires once quiet
        try:
            await asyncio.wait_for(fired.wait(), timeout=5)
        finally:
            task.cancel()

    asyncio.run(run())


def test_audio_then_farewell_transcript_still_ends_the_call():
    """Raw audio first (transcript lags), farewell transcript after: the call ends."""
    async def run():
        session = demo_session("autohangup-4d")
        autohangup.agent_closed_call(session, "Booked. Take care!")
        fired = asyncio.Event()

        async def end_call():
            fired.set()

        task = asyncio.create_task(autohangup.watch(session, end_call))
        await asyncio.sleep(0.5)  # inside the grace: caller sound arrives...
        autohangup.caller_made_sound(session)
        autohangup.caller_reopened_call(session, "gracias, adiós")  # ...then its transcript
        assert session.agent_finished, "farewell after audio must keep the arm"
        try:
            await asyncio.wait_for(fired.wait(), timeout=5)
        finally:
            task.cancel()

    asyncio.run(run())


def test_audio_then_real_request_clears_the_hangup():
    """Raw audio first, then a committed non-goodbye transcript: the call goes on."""
    session = demo_session("autohangup-4e")
    autohangup.agent_closed_call(session, "Booked. Take care!")
    autohangup.caller_made_sound(session)
    autohangup.caller_reopened_call(session, "Wait, can we also move Thursday's visit?")
    assert not session.agent_finished


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
