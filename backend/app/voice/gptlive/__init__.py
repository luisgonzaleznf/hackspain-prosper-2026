"""VOICE=gptlive: GPT-Live-1 through the OpenAI API (OPENAI_API_KEY). See README.md.

The same two-model shape as VOICE=codex, without the ChatGPT subscription:
- the voice (GPT-Live-1, full duplex) talks to the caller and delegates;
- the brain (a Responses model, OpenAI-hosted "Responses delegation") gets each delegation and
  calls app.tools, which pipecat executes here through `register_pipecat_tools`.

A socket that drops mid-call is recovered the way VOICE=codex recovers a closed transport:
a new session seeded with the conversation so far, and the same line to the caller.

Every call logs what it costs as kind="usage": GPT-Live's billed audio seconds and each brain
response's tokens (see scripts/call_costs.py).
"""

import asyncio
import os
import re
from typing import Any

from pipecat.frames.frames import LLMRunFrame
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.worker import PipelineParams, PipelineWorker
from pipecat.processors.aggregators.llm_context import LLMContext
from pipecat.processors.aggregators.llm_response_universal import (
    LLMContextAggregatorPair,
    LLMUserAggregatorParams,
)
from pipecat.services.openai.live import events
from pipecat.services.openai.live.llm import OpenAILiveLLMService
from pipecat.services.openai.responses.llm import (
    OpenAIResponsesLLMService,
    OpenAIResponsesReasoningConfig,
)
from pipecat.transports.base_transport import BaseTransport
from pipecat.turns.user_turn_strategies import ExternalUserTurnStrategies
from pipecat.utils.errors import ErrorCategory
from pipecat.workers.runner import WorkerRunner

from app.session import CallSession
from app.tools import register_pipecat_tools
from app.voice.codex import BRAIN_PREAMBLE, VOICE_PROMPT, voice_prompt
from app.voice.codex.service import MAX_RECOVERIES, RECOVERY_PROMPT
from app.voice.codex.settings import VoiceSettings, spanish_greeting

LIVE_MODEL = os.getenv("GPTLIVE_MODEL", "gpt-live-1")
BRAIN_MODEL = os.getenv("GPTLIVE_BRAIN_MODEL", "gpt-5.6-luna")
VOICE = os.getenv("GPTLIVE_VOICE", "marin")
HANDOFF_RULES = """
Delegate every new clinic detail, correction and answer to the back office, including
an answer about insurance or private payment. A previous delegation answering a question
has finished: it is not still working. Do not say you are processing anything unless
there is actual delegated work in progress. When registration details are incomplete,
relay the back office's next missing-field question instead of promising to register.
"""

DRAIN_SECS = 8  # after the caller hangs up, before the session is torn down


class MeteredLive(OpenAILiveLLMService):
    """OpenAILiveLLMService that meters the call and survives a dropped socket.

    pipecat only logs the live seconds at debug level and turns the brain's tokens into
    metrics frames; the call log is where cost is added up afterwards.

    It also recovers like VOICE=codex does: the same model on the same call, so a socket
    that drops mid-call rebuilds the session and apologises instead of ending the call.
    """

    def __init__(self, *, call: CallSession, **kwargs: Any):
        super().__init__(**kwargs)
        self._call = call
        self._recoveries = 0
        self._recovering = False
        self._say_recovery = False
        self._backend_busy: set[str] = set()
        self._speech_revision = 0
        self._handoff_retries = 0

    async def _handle_evt_delegation_created(self, evt):
        self._backend_busy.add(evt.delegation.id)
        self._call.log(
            "brain.started", delegation_id=evt.delegation.id, target=evt.delegation.target
        )
        await super()._handle_evt_delegation_created(evt)

    async def _handle_evt_response(self, evt):
        key = evt.delegation_id or "unidentified"
        if evt.inner_type == "response.created":
            self._backend_busy.add(key)
        elif evt.inner_type in {"response.completed", "response.failed", "response.incomplete"}:
            self._backend_busy.discard(key)
            response = evt.event.get("response") or {}
            self._call.log(
                "brain.finished",
                delegation_id=evt.delegation_id,
                status=evt.inner_type,
                error=response.get("error"),
                incomplete_details=response.get("incomplete_details"),
            )
        elif evt.inner_type == "response.output_item.done":
            item = evt.event.get("item") or {}
            if item.get("type") == "message":
                text = " ".join(
                    c.get("text", "")
                    for c in item.get("content", [])
                    if c.get("type") == "output_text"
                )
                self._call.log("brain.reply", delegation_id=evt.delegation_id, text=text)
        await super()._handle_evt_response(evt)

    def note_speech(self, text: str, *, agent: bool) -> None:
        self._speech_revision += 1
        if (
            agent
            and len(text) < 180
            and "?" not in text
            and re.search(
                r"un momento|sigo con su gesti[oó]n|one moment|still working|let me check",
                text,
                re.IGNORECASE,
            )
        ):
            self.create_task(self._resume_empty_handoff(self._speech_revision), "empty-handoff")

    async def _resume_empty_handoff(self, revision: int) -> None:
        # Give normal automatic delegation time to arrive. Never start a duplicate
        # while a response/tool is running, after newer speech, or on a closed call.
        await asyncio.sleep(2)
        if (
            revision != self._speech_revision
            or self._backend_busy
            or self._open_function_calls
            or not self._session_started_on_connection
            or self._handoff_retries >= 2
        ):
            return
        self._handoff_retries += 1
        self._call.log("brain.handoff_resumed", attempt=self._handoff_retries)
        await self.send_client_event(events.ResponseCreateEvent())

    async def _report_usage(self, usage: events.Usage):
        await super()._report_usage(usage)
        if usage.seconds is not None:  # cumulative for the session: the last one counts
            self._call.log("usage", model=LIVE_MODEL, live_seconds=usage.seconds)

    async def push_error(
        self,
        error_msg: str,
        exception: Exception | None = None,
        fatal: bool = False,
        category: ErrorCategory | None = None,
        force_treat_as_permanent: bool = False,
    ):
        """Rebuild the session instead of ending the call when the socket drops mid-call.

        pipecat reports a closed connection as permanent for this service, which cancels the
        pipeline and takes the call with it. A session that already started and then lost its
        socket is the same failure VOICE=codex recovers from (`transport_closed`), so it gets
        the same answer, and the same ceiling. A startup failure (bad key, no credits, no
        session ever started) stays fatal: retrying it would only fail again.
        """
        if (
            force_treat_as_permanent
            and self._session_started_on_connection
            and not self._recovering
            and self._recoveries < MAX_RECOVERIES
        ):
            self._recovering = True
            self._recoveries += 1
            self._call.log("voice.recovering", attempt=self._recoveries, error=error_msg)
            # reset_conversation() must not run in the receive task this error came from.
            self.create_task(self._recover(), "voice-recovery")
            return
        await super().push_error(
            error_msg=error_msg,
            exception=exception,
            fatal=fatal,
            category=category,
            force_treat_as_permanent=force_treat_as_permanent,
        )

    async def _recover(self) -> None:
        """Open a new session seeded with the conversation so far, then apologise into it."""
        self._say_recovery = True
        try:
            await self.reset_conversation()
            self._call.log("voice.recovered", attempt=self._recoveries)
        except Exception as error:
            self._say_recovery = False
            self._call.log("voice.recovery_failed", attempt=self._recoveries, error=repr(error))
            await super().push_error(
                error_msg=f"Voice recovery failed: {error!r}",
                exception=error,
                force_treat_as_permanent=True,
            )
        finally:
            self._recovering = False

    async def _handle_evt_session_started(self, evt: events.SessionStartedEvent) -> None:
        await super()._handle_evt_session_started(evt)
        if self._say_recovery:
            # The rebuilt session has no opening instruction of its own (the greeting's
            # trailing developer message is long behind us in the context), so the line the
            # caller hears comes from here.
            self._say_recovery = False
            await self._send_context_append(None, RECOVERY_PROMPT, spoken=True)

    async def _report_backend_usage(self, response: dict[str, Any]):
        await super()._report_backend_usage(response)
        usage = response.get("usage")
        if isinstance(usage, dict):
            self._call.log(
                "usage",
                model=response.get("model") or BRAIN_MODEL,
                input_tokens=usage.get("input_tokens") or 0,
                cached_tokens=(usage.get("input_tokens_details") or {}).get("cached_tokens") or 0,
                output_tokens=usage.get("output_tokens") or 0,
            )


async def run_call(
    transport: BaseTransport,
    session: CallSession,
    *,
    settings: VoiceSettings | None = None,
) -> None:
    prompt = voice_prompt(settings) if settings is not None else VOICE_PROMPT
    voice = settings.voice if settings is not None else VOICE
    greeting = session.greeting
    if settings is not None and settings.opening_language == "es":
        greeting = spanish_greeting(session.started_at)

    llm = MeteredLive(
        call=session,
        api_key=os.environ["OPENAI_API_KEY"],
        settings=MeteredLive.Settings(
            model=LIVE_MODEL, system_instruction=prompt + HANDOFF_RULES, voice=voice
        ),
        delegation=MeteredLive.ResponsesDelegation(
            settings=OpenAIResponsesLLMService.Settings(
                model=BRAIN_MODEL,
                system_instruction=BRAIN_PREAMBLE + session.instructions(),
                reasoning=OpenAIResponsesReasoningConfig(effort="low"),
            ),
        ),
    )
    # A trailing developer message is how the Live API is asked to speak first.
    context = LLMContext(
        messages=[
            {
                "role": "developer",
                "content": f'The call has just connected. Say exactly: "{greeting}"',
            }
        ],
        tools=register_pipecat_tools(llm, session),
    )
    user_agg, assistant_agg = LLMContextAggregatorPair(
        context,
        # GPT-Live does its own turn-taking and barge-in: don't broadcast interruptions.
        user_params=LLMUserAggregatorParams(
            user_turn_strategies=ExternalUserTurnStrategies(enable_interruptions=False)
        ),
    )

    @user_agg.event_handler("on_user_turn_message_added")
    async def on_user_text(aggregator, message):
        llm.note_speech(message.content, agent=False)
        session.log("transcript", role="user", text=message.content)

    @assistant_agg.event_handler("on_assistant_turn_stopped")
    async def on_agent_text(aggregator, message):
        if message.content:
            llm.note_speech(message.content, agent=True)
            session.log(
                "transcript", role="agent", text=message.content, interrupted=message.interrupted
            )

    worker = PipelineWorker(
        Pipeline([transport.input(), user_agg, llm, transport.output(), assistant_agg]),
        params=PipelineParams(enable_metrics=True, enable_usage_metrics=True),
    )
    runner = WorkerRunner(handle_sigint=False)
    await runner.add_workers(worker)

    @transport.event_handler("on_client_connected")
    async def on_client_connected(transport, client):
        await worker.queue_frames([LLMRunFrame()])  # opens the Live session; it greets

    @transport.event_handler("on_client_disconnected")
    async def on_client_disconnected(transport, client):
        # Callers often accept and hang up in one breath ("yes, book it, thanks, bye"): the
        # brain is still recording when the socket closes. Keep the model session alive a
        # moment so that record lands before the session logs the outcome.
        session.log("drain", seconds=DRAIN_SECS)
        await asyncio.sleep(DRAIN_SECS)
        await runner.cancel()

    await runner.run()
