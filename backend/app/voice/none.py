"""VOICE=none — a silent stand-in for plumbing tests only (handshake → session → submit on hang-up).

It never speaks, so on a real Prosper call it is cut off for silence. Use a real voice layer there.
"""

from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.worker import PipelineWorker
from pipecat.transports.base_transport import BaseTransport
from pipecat.workers.runner import WorkerRunner

from app.session import CallSession


async def run_call(transport: BaseTransport, session: CallSession) -> None:
    worker = PipelineWorker(Pipeline([transport.input(), transport.output()]), enable_rtvi=False)
    runner = WorkerRunner(handle_sigint=False)
    await runner.add_workers(worker)

    @transport.event_handler("on_client_disconnected")
    async def on_client_disconnected(transport, client):
        await runner.cancel()

    await runner.run()
