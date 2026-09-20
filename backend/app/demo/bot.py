"""Pipecat SmallWebRTC entry point for the role-play demo."""

from typing import Any

from pipecat.runner.run import app as runner_app
from pipecat.runner.types import RunnerArguments
from pipecat.runner.utils import create_transport
from pipecat.transports.base_transport import TransportParams

from app import config
from app.demo.app import register_demo_routes
from app.demo.models import DemoStartRequest
from app.demo.recording import DemoRecorder
from app.demo.scenarios import get_scenario
from app.demo.state import (
    build_action_evidence,
    claim_session,
    create_session,
    end_session,
    log_event,
    update_outcome,
)
from app.session import CallSession
from app.voice import codex

register_demo_routes(runner_app)


class DemoCallSession(CallSession):
    """A normal call session whose observable events also feed the demo UI."""

    def log(self, kind: str, **data: Any) -> None:
        super().log(kind, **data)
        log_event(self.call_id, kind, **data)
        if kind in {"action_staged", "actions_cleared"}:
            update_outcome(self.call_id, self.actions, build_action_evidence(self))


async def bot(runner_args: RunnerArguments) -> None:
    """Run one browser role-play without submitting its staged outcome."""
    request = DemoStartRequest.model_validate(runner_args.body)
    scenario = get_scenario(request.scenario_id)
    if scenario is None:
        raise ValueError(f"Unknown demo scenario: {request.scenario_id}")

    session_id = runner_args.session_id
    if not session_id:
        raise ValueError("Pipecat runner did not provide a session_id")

    create_session(session_id, scenario.id)
    if not claim_session(session_id):
        return
    session: DemoCallSession | None = None
    recorder = DemoRecorder()
    try:
        session = await DemoCallSession.start(
            call_id=session_id,
            stream_sid=session_id,
            from_number=scenario.phone or None,
            demo_mode=True,
        )
        transport = await create_transport(
            runner_args,
            {"webrtc": lambda: TransportParams(audio_in_enabled=True, audio_out_enabled=True)},
        )
        recorder.tap(transport)
        await codex.run_call(transport, session)
    except Exception as exc:
        if session:
            session.log("voice_error", error=repr(exc))
        else:
            log_event(session_id, "voice_error", error=repr(exc))
        raise
    finally:
        if session is None:
            end_session(session_id)
        else:
            try:
                session.log("recording.saved", **await recorder.save(session_id, config.AUDIO_DIR))
            except Exception as exc:
                session.log("recording.error", error=repr(exc))
            await session.finish_demo()
            end_session(session_id, session.actions, build_action_evidence(session))


if __name__ == "__main__":
    from pipecat.runner.run import main

    main()
