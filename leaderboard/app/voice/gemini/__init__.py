"""VOICE=gemini: Gemini Live (audio-to-audio) as the whole voice stack. See README.md.

One Live session per call. The model hears the caller, calls app.tools itself (every call is
NON_BLOCKING on this model family, so the prompt makes it wait for results), and speaks back.
"""

import os

from pipecat.frames.frames import LLMRunFrame
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.worker import PipelineParams, PipelineWorker
from pipecat.processors.aggregators.llm_context import LLMContext
from pipecat.processors.aggregators.llm_response_universal import LLMContextAggregatorPair
from pipecat.services.google.gemini_live.llm import GeminiLiveLLMService
from pipecat.transports.base_transport import BaseTransport
from pipecat.workers.runner import WorkerRunner

from app.session import CallSession
from app.tools import register_pipecat_tools

DEFAULT_MODEL = "gemini-3.8-live-extended-thinking"

# Appended to session.instructions(): this model runs every tool in the background.
TOOL_RULES = """

HOW YOUR TOOLS BEHAVE ON THIS LINE
Every tool runs in the background while you keep talking, and its result reaches you a moment
later. So when you call a tool, say briefly that you are checking ("One moment, let me check")
and then stop talking until the result arrives. Never name a slot, say a patient was found,
confirm a booking or say anything was recorded before that tool's result has arrived. When one
lookup depends on another (the patient before availability), wait for the first result."""

GREETING = 'The call has just connected. Greet the caller now, saying exactly: "{greeting}"'


async def run_call(transport: BaseTransport, session: CallSession) -> None:
    llm = GeminiLiveLLMService(
        api_key=os.environ["GEMINI_API_KEY"],
        settings=GeminiLiveLLMService.Settings(
            model=os.getenv("GEMINI_LIVE_MODEL", DEFAULT_MODEL),
            voice=os.getenv("GEMINI_VOICE", "Charon"),
            system_instruction=session.instructions() + TOOL_RULES,
        ),
    )
    context = LLMContext(
        messages=[{"role": "user", "content": GREETING.format(greeting=session.greeting)}],
        tools=register_pipecat_tools(llm, session),
    )
    user_agg, assistant_agg = LLMContextAggregatorPair(context)

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
        params=PipelineParams(enable_metrics=True),
    )
    runner = WorkerRunner(handle_sigint=False)
    await runner.add_workers(worker)

    @transport.event_handler("on_client_connected")
    async def on_client_connected(transport, client):
        await worker.queue_frames([LLMRunFrame()])  # opens the Live session and greets

    @transport.event_handler("on_client_disconnected")
    async def on_client_disconnected(transport, client):
        await runner.cancel()

    await runner.run()
