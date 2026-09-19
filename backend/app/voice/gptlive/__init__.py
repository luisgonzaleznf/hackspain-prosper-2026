"""VOICE=gptlive: GPT-Live-1 through the OpenAI API (OPENAI_API_KEY). See README.md.

The same two-model shape as VOICE=codex, without the ChatGPT subscription:
- the voice (GPT-Live-1, full duplex) talks to the caller and delegates;
- the brain (a Responses model, OpenAI-hosted "Responses delegation") gets each delegation and
  calls app.tools, which pipecat executes here through `register_pipecat_tools`.

Every call logs what it costs as kind="usage": GPT-Live's billed audio seconds and each brain
response's tokens (see scripts/call_costs.py).
"""

import asyncio
import os
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
from pipecat.workers.runner import WorkerRunner

from app.session import CallSession
from app.tools import register_pipecat_tools
from app.voice.codex import BRAIN_PREAMBLE, VOICE_PROMPT

LIVE_MODEL = os.getenv("GPTLIVE_MODEL", "gpt-live-1")
BRAIN_MODEL = os.getenv("GPTLIVE_BRAIN_MODEL", "gpt-5.6-luna")
VOICE = os.getenv("GPTLIVE_VOICE", "marin")
DRAIN_SECS = 8  # after the caller hangs up, before the session is torn down


class MeteredLive(OpenAILiveLLMService):
    """OpenAILiveLLMService that also writes the call's billable usage to the call log.

    pipecat only logs the live seconds at debug level and turns the brain's tokens into
    metrics frames; the call log is where cost is added up afterwards.
    """

    def __init__(self, *, call: CallSession, **kwargs: Any):
        super().__init__(**kwargs)
        self._call = call

    async def _report_usage(self, usage: events.Usage):
        await super()._report_usage(usage)
        if usage.seconds is not None:  # cumulative for the session: the last one counts
            self._call.log("usage", model=LIVE_MODEL, live_seconds=usage.seconds)

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


async def run_call(transport: BaseTransport, session: CallSession) -> None:
    llm = MeteredLive(
        call=session,
        api_key=os.environ["OPENAI_API_KEY"],
        settings=MeteredLive.Settings(
            model=LIVE_MODEL, system_instruction=VOICE_PROMPT, voice=VOICE
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
                "content": f'The call has just connected. Say exactly: "{session.greeting}"',
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
        session.log("transcript", role="user", text=message.content)

    @assistant_agg.event_handler("on_assistant_turn_stopped")
    async def on_agent_text(aggregator, message):
        if message.content:
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
        # moment so that record lands; Prosper accepts submissions for 30 s after hang-up.
        session.log("drain", seconds=DRAIN_SECS)
        await asyncio.sleep(DRAIN_SECS)
        await runner.cancel()

    await runner.run()
