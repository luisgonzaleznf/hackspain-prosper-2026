"""Dead-air re-prompt (app/voice/deadair.py): ask "are you still there?" on a silent line instead
of letting the caller hang up ~35 s after our last audible audio (run 15f7762b, 9 agent_silence)."""

import asyncio
import importlib
import json
import time
import wave

import app.voice.codex.service as service_module
import app.voice.deadair as deadair_module
import pytest
from app.voice.codex.service import CodexLiveService
from app.voice.deadair import (
    REPEAT,
    REPROMPTS,
    STILL_HERE,
    DeadAirWatch,
    clip_path,
    is_goodbye,
    language_of,
    observe,
)


def spoke_at(t: float) -> DeadAirWatch:
    w = DeadAirWatch(quiet_secs=8.0, every_secs=10.0, max_in_row=3)  # the mechanism, at 8 s
    w.agent_audible(t)
    return w


def test_nothing_before_the_agent_has_spoken():
    assert not DeadAirWatch().due(100.0)


def test_eight_quiet_seconds_after_the_agent_spoke_trigger_one_reprompt():
    w = spoke_at(0.0)
    assert not w.due(7.9)
    assert w.due(8.0)
    assert w.prompted(8.0) == "Are you still there?"


def test_reprompts_are_at_least_ten_seconds_apart_and_stop_after_three():
    w = spoke_at(0.0)
    times = []
    for t in range(8, 80):
        if w.due(float(t)):
            w.prompted(float(t))
            times.append(t)
    assert times == [8, 18, 28]  # quiet 8 s, then every 10 s, then it stops


def test_late_caller_fragments_cannot_keep_it_nudging_past_five_per_call():
    # 08efe9f8 (test call): each late fragment reset the in-a-row count, 10 nudges.
    w = spoke_at(0.0)
    said = []
    for t in range(8, 300):
        if w.due(float(t)):
            said.append(w.prompted(float(t)))
            observe(w, {"source": "oai", "type": "input_transcript.added"}, float(t) + 2)
    assert len(said) == 5 and w.total == 5


def test_the_question_alternates_with_a_line_that_asks_nothing():
    w = spoke_at(0.0)
    said = [w.prompted(float(t)) for t in (8, 18, 28)]
    assert said == [
        "Are you still there?",
        "I'm still here, take your time.",
        "Are you still there?",
    ]
    assert not any("?" in line for line in STILL_HERE.values())
    assert set(STILL_HERE) == set(REPROMPTS)


def frames(w: DeadAirWatch, start: float, secs: float, rms) -> None:
    for i in range(int(secs * 50)):
        w.caller_level(start + i * 0.02, rms(i))


def user_turn(w: DeadAirWatch, at: float) -> None:
    observe(w, {"source": "oai", "type": "turn.created", "turn": {"role": "user"}}, at)


def test_a_stuck_caller_turn_is_released_once_after_the_quiet_window():
    w = DeadAirWatch(stuck_turn_secs=4.0)
    user_turn(w, 10.0)
    frames(w, 10.0, 2.0, lambda i: 3000.0)  # the caller's words arrive until 12.0
    assert not w.turn_stuck(15.9)
    assert w.turn_stuck(16.0)
    w.turn_released()
    assert not w.turn_stuck(30.0)  # once per turn
    user_turn(w, 40.0)
    assert w.turn_stuck(44.0)  # the next turn can be released again


def test_the_turn_release_is_off_by_default_and_waits_for_the_brain():
    w = DeadAirWatch()
    user_turn(w, 0.0)
    assert not w.turn_stuck(60.0)  # STUCK_TURN_SECS defaults to 0: off
    w = DeadAirWatch(stuck_turn_secs=4.0)
    user_turn(w, 0.0)
    observe(w, {"source": "codex", "method": "turn/started"}, 1.0)
    assert not w.turn_stuck(8.0)


def test_caller_speech_on_the_line_holds_the_nudge_before_any_transcript():
    # 41 of 176 test-caller replies land 10-15 s after our turn, and transcripts lag 1-2 s.
    w = spoke_at(0.0)
    frames(w, 0.0, 7.5, lambda i: 0.0)  # digital silence
    frames(w, 7.5, 1.0, lambda i: 3000.0)  # the caller starts talking
    assert not w.due(8.5)
    assert not w.due(12.4)
    assert w.due(12.5)  # 4 s after their voice stopped, with no answer from the model


def test_a_steady_noise_bed_is_not_speech():
    # Problem 12 mixes a noise bed under every call: it must not hold the nudge forever.
    w = spoke_at(0.0)
    frames(w, 0.0, 20.0, lambda i: 800.0 + (i * 37 % 200) - 100)  # 700-900 RMS
    assert w.due(20.0)
    frames(w, 20.0, 0.5, lambda i: 4000.0)  # speech over the noise
    assert not w.due(21.0)


def test_a_caller_turn_the_model_sits_on_gets_a_request_to_repeat():
    # ad8cd801: DNI spoken ~110 s, caller turn open 117.8-136.5 s, then "Are you still there?"
    # replaced the answer and the DNI was never used.
    w = spoke_at(112.3)
    w.lang = "es"
    observe(w, {"source": "oai", "type": "turn.created", "turn": {"role": "user"}}, 117.8)
    assert w.due(125.8)
    assert w.line == REPEAT["es"]
    observe(w, {"source": "oai", "type": "turn.done", "turn": {"role": "user"}}, 126.0)
    assert w.line == REPROMPTS["es"]
    observe(w, {"source": "oai", "type": "turn.created", "turn": {"role": "user"}}, 127.0)
    observe(w, {"source": "oai", "type": "turn.created", "turn": {"role": "assistant"}}, 128.0)
    assert not w.caller_turn_open  # the model is answering it


def test_the_caller_speaking_resets_the_quiet_window_and_the_count():
    w = spoke_at(0.0)
    w.prompted(8.0)
    w.prompted(18.0)
    observe(w, {"source": "oai", "type": "input_transcript.added"}, 20.0)
    assert w.in_row == 0
    assert not w.due(27.9)
    assert w.due(28.0)


def test_line_noise_is_not_speech_only_the_models_transcripts_count():
    # A noise bed produces loud caller audio but no caller transcript events: it must not
    # keep the line "busy" forever (problem 12 mixes noise under every call).
    w = spoke_at(0.0)
    observe(w, {"source": "oai", "type": "session.usage.updated"}, 5.0)
    assert w.due(8.0)


def test_never_over_a_lookup_or_a_brain_turn():
    w = spoke_at(0.0)
    observe(w, {"source": "codex", "method": "turn/started"}, 1.0)
    assert not w.due(15.0)
    observe(w, {"source": "codex", "method": "turn/completed"}, 15.0)
    assert not w.due(15.0)  # the voice first gets time to say the answer
    assert w.due(18.0)


def test_no_reprompt_the_instant_the_brain_finishes_the_voice_needs_time_to_answer():
    # e8aef8af: filler 41.9 s, turn/completed 51.3 s, the slot offer spoken after it. A re-prompt
    # at completion would pre-empt the offer and the caller's "yes" could book a slot unheard.
    w = spoke_at(3.5)
    observe(w, {"source": "codex", "method": "turn/started"}, 0.5)
    observe(w, {"source": "codex", "method": "turn/completed"}, 13.0)
    assert not w.due(13.0)
    assert not w.due(15.9)
    assert w.due(16.0)


def test_a_short_turn_leaves_the_quiet_window_alone():
    w = spoke_at(0.0)
    observe(w, {"source": "codex", "method": "turn/started"}, 1.0)
    observe(w, {"source": "codex", "method": "turn/completed"}, 2.0)
    assert w.due(8.0)  # the grace only matters once the quiet window has already run out


def test_a_lookup_hung_for_20_seconds_no_longer_holds_it_back():
    w = spoke_at(0.0)
    w.begin_busy(1.0)
    assert not w.due(20.9)
    assert w.due(21.0)


def test_the_agents_own_turns_do_not_count_as_the_caller():
    w = spoke_at(0.0)
    observe(w, {"source": "oai", "type": "turn.created", "turn": {"role": "assistant"}}, 6.0)
    assert w.due(8.0)


def test_the_reprompt_is_in_the_callers_language():
    w = spoke_at(0.0)
    observe(
        w,
        {
            "source": "codex",
            "method": "thread/realtime/transcript/done",
            "params": {"role": "user", "text": "Necessito una hora per traumatologia, sisplau"},
        },
        1.0,
    )
    assert w.prompted(9.0) == REPROMPTS["ca"]
    assert language_of("Hola, quería pedir cita, por favor") == "es"
    assert language_of("Hi, I'd like to book an appointment") == "en"


def said(role: str, text: str) -> dict:
    return {
        "source": "codex",
        "method": "thread/realtime/transcript/done",
        "params": {"role": role, "text": text},
    }


def test_id_dictation_does_not_flip_a_spanish_call_to_english():
    # Logged: "en" after 7 of 12 Spanish utterances, right after identity dictation.
    w = spoke_at(0.0)
    observe(w, said("user", "Hola, quería pedir cita, por favor"), 1.0)
    observe(w, said("user", "Claro, mi DNI es cuatro, ocho, dos, uno"), 3.0)
    observe(w, said("user", "Sí, la letra es Y"), 5.0)
    assert w.line == REPROMPTS["es"]


def test_a_role_less_voice_turn_is_not_the_caller():
    w = spoke_at(0.0)
    w.prompted(8.0)
    observe(w, {"source": "oai", "type": "turn.done", "turn": {}}, 9.0)
    assert w.in_row == 1  # the cap of 3 still holds on a dead line


def test_a_lost_turn_completed_does_not_disable_the_guard_for_later_lookups():
    w = spoke_at(0.0)
    observe(w, {"source": "codex", "method": "turn/started"}, 1.0)  # never completed
    observe(w, {"source": "codex", "method": "turn/started"}, 100.0)  # the next brain turn
    w.begin_busy(101.0)  # a booking write inside it
    assert not w.due(109.0)


def test_no_reprompt_once_an_outcome_is_recorded_and_the_agent_said_goodbye():
    w = spoke_at(0.0)
    w.recorded = True
    observe(w, said("assistant", "Booked for Monday at nine. Goodbye!"), 1.0)
    assert not w.due(30.0)
    observe(w, said("user", "Wait, one more thing"), 31.0)  # the caller keeps talking
    w.agent_audible(32.0)
    assert w.due(40.0)


def test_the_caller_saying_goodbye_back_keeps_the_call_finished():
    w = spoke_at(0.0)
    w.recorded = True
    observe(w, said("assistant", "De nada, que tenga buena tarde."), 1.0)
    observe(w, {"source": "oai", "type": "input_transcript.added"}, 2.0)
    observe(w, said("user", "Gracias, adiós."), 3.0)
    assert not w.due(30.0)


def test_take_care_of_that_is_not_a_goodbye():
    # Logged: "Sure, let me take care of that." (f66b8d06, 223ceae8) mid-call.
    assert not is_goodbye("Sure, let me take care of that for you.")
    assert is_goodbye("You're welcome. Take care!")


def test_a_goodbye_without_a_recorded_outcome_still_reprompts():
    w = spoke_at(0.0)
    observe(w, said("assistant", "Que tenga un buen día, adiós."), 1.0)
    assert w.due(9.0)  # nothing staged yet: the call is not finished


class StubPeer:
    """appendSpeech stand-in. `speaks`: the voice model then starts a turn (evals: 9 of 12);
    otherwise the text is only appended to its context and nothing is heard."""

    def __init__(self, svc: CodexLiveService, fail: bool = False, speaks: bool = True):
        self.svc, self.fail, self.speaks, self.said = svc, fail, speaks, []

    def audio_stats(self) -> dict:
        return {"sent_to_openai_loud_ms": 1200}

    def send_event(self, event: dict) -> None:
        self.sent_events = [*getattr(self, "sent_events", []), event]

    async def say(self, text: str) -> None:
        if self.fail:
            raise TimeoutError("appendSpeech timed out")
        self.said.append(text)
        if self.speaks:
            self.svc._on_event(
                {"source": "oai", "type": "turn.created", "turn": {"role": "assistant"}}
            )


@pytest.fixture
def svc(monkeypatch):
    monkeypatch.setattr(service_module, "CONFIRM_SECS", 0.2)
    events: list = []
    s = CodexLiveService(prompt="x")
    s.events = events  # type: ignore[attr-defined]  # only what the watch logs is asserted
    s.pushed = []  # type: ignore[attr-defined]

    def log(e: str, d: str) -> None:
        if e.startswith("voice."):
            events.append((e, json.loads(d)))

    s._on_brain_event = log

    async def push_frame(frame, direction=None):
        s.pushed.append(frame)  # type: ignore[attr-defined]

    monkeypatch.setattr(s, "push_frame", push_frame)
    s._watch = DeadAirWatch(quiet_secs=0.0, every_secs=100.0)
    s._watch.agent_audible(0.0)
    return s


def run_watch(svc: CodexLiveService, peer: StubPeer, secs: float) -> None:
    async def go() -> None:
        svc._peer = peer  # type: ignore[assignment]
        task = asyncio.create_task(svc._watch_line())
        await asyncio.sleep(secs)
        svc._peer = None
        task.cancel()

    asyncio.run(go())


def test_a_nudge_the_model_speaks_counts_once_and_plays_no_clip(svc):
    peer = StubPeer(svc)
    run_watch(svc, peer, 1.5)
    assert peer.said == ["Are you still there?"]
    assert svc._watch.in_row == 1 and svc.pushed == []
    assert [(e, d["spoken"]) for e, d in svc.events] == [("voice.reprompt", "model")]


def test_a_nudge_the_model_ignores_is_played_from_the_recording(svc):
    # evals' 8 s dropout call: 3 nudges appended to the model's context, none spoken.
    run_watch(svc, StubPeer(svc, speaks=False), 1.5)
    assert len(svc.pushed) == 1 and svc.pushed[0].sample_rate == svc._out_rate
    assert len(svc.pushed[0].audio) > svc._out_rate  # ~1 s of 16-bit audio: the whole line
    assert svc._watch.in_row == 1
    assert [(e, d["spoken"]) for e, d in svc.events] == [("voice.reprompt", "clip")]


def test_a_failed_append_still_plays_the_recording(svc):
    run_watch(svc, StubPeer(svc, fail=True), 1.5)
    assert len(svc.pushed) == 1 and svc._watch.in_row == 1
    assert svc.events[0][1]["spoken"] == "clip"


def test_a_nudge_nobody_heard_is_logged_as_such_and_not_counted(svc, monkeypatch):
    monkeypatch.setattr(service_module, "clip_path", lambda line: None)
    run_watch(svc, StubPeer(svc, speaks=False), 1.5)
    assert svc._watch.in_row == 0 and svc.pushed == []
    assert [(e, d["spoken"]) for e, d in svc.events] == [("voice.reprompt", "none")]
    assert svc._watch.last_prompt is not None  # retried after a full interval, not every second


def test_a_frozen_voice_session_is_logged_and_so_is_its_return(svc):
    peer = StubPeer(svc)
    svc._watch.agent_audible(1e12)  # keep the nudge out of it
    svc._voice_event_at = time.monotonic() - 9
    run_watch(svc, peer, 1.3)
    assert [e for e, _ in svc.events] == ["voice.stalled"]
    stalled = svc.events[0][1]
    assert stalled["silent_s"] >= 8 and stalled["caller_loud_ms"] == 1200
    svc._peer = peer  # type: ignore[assignment]
    svc._on_event({"source": "oai", "type": "session.usage.updated"})
    assert [e for e, _ in svc.events] == ["voice.stalled", "voice.resumed"]


def test_transport_closed_starts_bounded_recovery(svc, monkeypatch):
    started = []

    async def recover():
        started.append(True)

    monkeypatch.setattr(svc, "_recover_peer", recover)
    monkeypatch.setattr(svc, "create_task", lambda coroutine, name: asyncio.create_task(coroutine))

    async def go():
        svc._on_event(
            {
                "source": "codex",
                "method": "thread/realtime/closed",
                "params": {"reason": "transport_closed"},
            }
        )
        assert svc._recovery_task is not None
        await svc._recovery_task

    asyncio.run(go())
    assert started == [True]


def test_requested_close_does_not_recover(svc):
    svc._on_event(
        {
            "source": "codex",
            "method": "thread/realtime/closed",
            "params": {"reason": "requested"},
        }
    )
    assert svc._recovery_task is None


def test_recovery_never_uses_recorded_fallback_voice(svc):
    svc._recovering = True
    result = asyncio.run(svc._nudge("Are you still there?"))
    assert result == "none"
    assert svc.pushed == []


def test_recovery_replaces_peer_and_asks_for_repeat(svc, monkeypatch):
    class RecoverPeer:
        def __init__(self):
            self.closed = False
            self.started = False
            self.said = []

        async def close(self):
            self.closed = True

        async def start(self):
            self.started = True

        async def say(self, text):
            self.said.append(text)

    old, new = RecoverPeer(), RecoverPeer()
    svc._peer = old
    monkeypatch.setattr(svc, "_make_peer", lambda: new)
    asyncio.run(svc._recover_peer())
    assert old.closed
    assert new.started
    assert new.said == [service_module.RECOVERY_PROMPT]
    assert svc._peer is new
    assert svc._recoveries == 1


def test_the_service_releases_a_stuck_turn_with_response_create(svc):
    peer = StubPeer(svc)
    svc._watch = DeadAirWatch(stuck_turn_secs=0.5)
    svc._watch.agent_audible(1e12)  # keep the nudge out of it
    svc._watch.caller_turn_since = time.monotonic() - 5
    run_watch(svc, peer, 1.3)
    assert peer.sent_events == [{"type": "response.create"}]
    assert [e for e, _ in svc.events] == ["voice.turn_release"]
    assert svc.events[0][1]["open_s"] >= 5


def test_every_line_has_its_recording():
    for line in [*REPROMPTS.values(), *STILL_HERE.values(), *REPEAT.values()]:
        path = clip_path(line)
        assert path is not None and path.exists(), line
        with wave.open(str(path)) as w:
            assert (w.getframerate(), w.getnchannels(), w.getsampwidth()) == (8000, 1, 2)
            assert 0.3 < w.getnframes() / 8000 < 4


def test_a_successful_record_marks_the_outcome_and_clearing_unmarks_it():
    async def handler(name, args):
        return {"error": "Unknown patient_id"} if args.get("bad") else {"ok": True}

    svc = CodexLiveService(prompt="x", on_tool_call=handler)
    asyncio.run(svc._tool_call("record_booking", {"bad": True}))
    assert not svc._watch.recorded
    asyncio.run(svc._tool_call("record_booking", {}))
    assert svc._watch.recorded
    asyncio.run(svc._tool_call("clear_recorded_actions", {}))
    assert not svc._watch.recorded


@pytest.mark.parametrize(
    ("result", "expected"),
    [
        ({"everything_recorded": [{"action": "CANCEL", "appointment_id": "A1"}]}, True),
        ({"everything_recorded": []}, False),
        ({"error": "Invalid selector"}, True),
    ],
)
def test_selective_clear_preserves_watchdog_outcome_when_actions_remain(result, expected):
    async def handler(name, args):
        return result

    svc = CodexLiveService(prompt="x", on_tool_call=handler)
    svc._watch.recorded = True
    asyncio.run(svc._tool_call("clear_recorded_actions", {"patient_id": "P1"}))
    assert svc._watch.recorded is expected


def test_the_service_marks_tool_calls_as_busy():
    seen = []

    async def handler(name, args):
        seen.append(svc._watch._tools)
        return {"ok": True}

    svc = CodexLiveService(prompt="x", on_tool_call=handler)
    assert asyncio.run(svc._tool_call("search_availability", {})) == {"ok": True}
    assert seen == [1] and svc._watch._tools == 0


def test_watchdog_defaults_wait_12_seconds_past_problem_13s_8_second_pause():
    assert (deadair_module.QUIET_SECS, deadair_module.EVERY_SECS, deadair_module.MAX_IN_ROW) == (
        12.0,
        10.0,
        3,
    )
    assert deadair_module.MAX_PER_CALL == DeadAirWatch().max_per_call == 5
    w = DeadAirWatch()
    assert (w.quiet_secs, w.every_secs, w.max_in_row) == (12.0, 10.0, 3)
    w.agent_audible(0.0)
    assert not w.due(8.0) and not w.due(11.9) and w.due(12.0)


def test_watchdog_thresholds_are_env_overridable(monkeypatch):
    monkeypatch.setenv("WATCHDOG_SILENCE_S", "6")
    monkeypatch.setenv("WATCHDOG_REPEAT_S", "4")
    monkeypatch.setenv("WATCHDOG_MAX", "5")
    try:
        reloaded = importlib.reload(deadair_module)
        assert (reloaded.QUIET_SECS, reloaded.EVERY_SECS, reloaded.MAX_IN_ROW) == (6.0, 4.0, 5)
        w = reloaded.DeadAirWatch()
        assert (w.quiet_secs, w.every_secs, w.max_in_row) == (6.0, 4.0, 5)
    finally:
        # Every other test in this module imports the un-reloaded module-level names, so put
        # the defaults back rather than leaving the reload's overridden values live.
        monkeypatch.undo()
        importlib.reload(deadair_module)
