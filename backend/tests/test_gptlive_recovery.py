"""VOICE=gptlive recovery: a socket that drops mid-call rebuilds the session and apologises.

Same model and same failure as VOICE=codex's `transport_closed` recovery (app/voice/codex/
service.py), so the caller hears the same line instead of the call ending under them.
"""

import asyncio
from types import SimpleNamespace

from app.voice.codex.service import MAX_RECOVERIES, RECOVERY_PROMPT
from app.voice.gptlive import MeteredLive


class FakeCall:
    """Just the part of CallSession this path touches."""

    def __init__(self):
        self.logged: list[tuple[str, dict]] = []

    def log(self, kind: str, **data) -> None:
        self.logged.append((kind, data))

    def kinds(self) -> list[str]:
        return [kind for kind, _ in self.logged]


def live(monkeypatch) -> tuple[MeteredLive, FakeCall, dict]:
    """A service that never opens a socket: the reset and the fatal error are recorded instead."""
    call = FakeCall()
    svc = MeteredLive(
        call=call,
        api_key="test-key",
        settings=MeteredLive.Settings(model="gpt-live-1", system_instruction="x", voice="marin"),
    )
    seen: dict = {"resets": 0, "fatal": [], "spoken": []}

    async def reset_conversation():
        seen["resets"] += 1

    async def push_error(self, **kwargs):  # the base class's: what would end the call
        seen["fatal"].append(kwargs.get("error_msg", ""))

    async def send_context_append(delegation_id, text, *, spoken):
        seen["spoken"].append((text, spoken))

    monkeypatch.setattr(svc, "reset_conversation", reset_conversation)
    monkeypatch.setattr(svc, "_send_context_append", send_context_append)
    monkeypatch.setattr(MeteredLive.__mro__[1], "push_error", push_error)
    # No pipecat task manager in a unit test: run the recovery coroutine directly.
    monkeypatch.setattr(svc, "create_task", lambda coro, name=None: asyncio.ensure_future(coro))
    return svc, call, seen


SESSION_STARTED = SimpleNamespace(session=SimpleNamespace(id="sess_1"))


async def drop_socket(svc: MeteredLive) -> None:
    """What pipecat does when the websocket closes under a running session."""
    await svc.push_error(
        error_msg="Connection closed: 1006", exception=None, force_treat_as_permanent=True
    )
    await asyncio.sleep(0)  # let the recovery task run


def test_dropped_socket_rebuilds_and_apologises(monkeypatch):
    svc, call, seen = live(monkeypatch)
    svc._session_started_on_connection = True

    async def go():
        await drop_socket(svc)
        await svc._handle_evt_session_started(SESSION_STARTED)

    asyncio.run(go())

    assert seen["resets"] == 1  # a new session, not a dead call
    assert seen["fatal"] == []  # the pipeline was never told to stop
    assert call.kinds() == ["voice.recovering", "voice.recovered"]
    assert seen["spoken"] == [(RECOVERY_PROMPT, True)]  # said aloud, once the session is back


def test_startup_failure_stays_fatal(monkeypatch):
    """No session ever started on this connection: a bad key or no credits. Retrying only fails."""
    svc, call, seen = live(monkeypatch)
    svc._session_started_on_connection = False

    asyncio.run(drop_socket(svc))

    assert seen["resets"] == 0
    assert seen["fatal"] == ["Connection closed: 1006"]
    assert call.kinds() == []


def test_recovery_has_the_same_ceiling_as_codex(monkeypatch):
    svc, call, seen = live(monkeypatch)
    svc._session_started_on_connection = True

    async def go():
        for _ in range(MAX_RECOVERIES + 1):
            await drop_socket(svc)

    asyncio.run(go())

    assert seen["resets"] == MAX_RECOVERIES
    assert seen["fatal"] == ["Connection closed: 1006"]  # the one past the ceiling ends the call
    assert call.kinds().count("voice.recovering") == MAX_RECOVERIES


def test_a_failed_rebuild_ends_the_call(monkeypatch):
    svc, call, seen = live(monkeypatch)
    svc._session_started_on_connection = True

    async def boom():
        raise RuntimeError("no socket")

    monkeypatch.setattr(svc, "reset_conversation", boom)

    async def go():
        await drop_socket(svc)
        await svc._handle_evt_session_started(SESSION_STARTED)

    asyncio.run(go())

    assert call.kinds() == ["voice.recovering", "voice.recovery_failed"]
    assert seen["fatal"] and "no socket" in seen["fatal"][0]
    assert seen["spoken"] == []  # nothing to apologise into
