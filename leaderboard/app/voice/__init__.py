"""Voice layers, picked by VOICE: each is app/voice/<name>.py exposing

    async def run_call(transport: BaseTransport, session: CallSession) -> None

Contract:
- speak `session.greeting` first; use `session.instructions()` as the system prompt;
- give the model `app.tools.TOOLS` and route every call through `app.tools.call_tool(session, ...)`
  (pipecat services: `app.tools.register_pipecat_tools(llm, session)`);
- log what was said: `session.log("transcript", role="user" | "agent", text=...)`;
- return once the socket closes. Never submit: the server calls `session.finish()`.
"""

import importlib

from pipecat.transports.base_transport import BaseTransport

from app import config
from app.session import CallSession


async def run_call(transport: BaseTransport, session: CallSession) -> None:
    module = importlib.import_module(f"app.voice.{config.VOICE}")
    await module.run_call(transport, session)
