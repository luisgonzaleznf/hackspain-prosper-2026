"""The tool-calling agent loop.

This is the load-bearing logic: a manual agentic loop over the Anthropic
Messages API. We keep it manual (rather than the SDK tool_runner) so the loop
is easy to read, log, and hack on during a hackathon.

The Anthropic client is created lazily so the module imports cleanly with no
API key — tests patch `anthropic.Anthropic` and never touch the network.
"""

from __future__ import annotations

import os
from typing import Any

import anthropic

from tools import TOOL_SCHEMAS, run_tool

# Default model. claude-sonnet-4-6 is a good speed/intelligence balance for a
# tool loop. Override with the MODEL env var.
DEFAULT_MODEL = os.environ.get("MODEL", "claude-sonnet-4-6")

SYSTEM_PROMPT = (
    "You are a concise, helpful assistant for a demo app. "
    "Use the get_time tool when asked about the current time or date, and the "
    "search tool to look up facts that might live in the knowledge base. "
    "Prefer calling a tool over guessing. Keep answers short."
)

# Hard ceiling on tool-loop iterations so a misbehaving model can't spin forever.
MAX_STEPS = 6


def _client() -> anthropic.Anthropic:
    """Construct the Anthropic client.

    Reads ANTHROPIC_API_KEY from the environment (the SDK default). Created per
    call so tests can patch `anthropic.Anthropic` before this runs.
    """
    return anthropic.Anthropic()


def run_agent(
    user_message: str,
    *,
    model: str = DEFAULT_MODEL,
    max_steps: int = MAX_STEPS,
    client: anthropic.Anthropic | None = None,
) -> dict[str, Any]:
    """Run a multi-step tool-calling loop and return the final answer + trace.

    Returns a dict:
      {
        "reply": <final assistant text>,
        "steps": [ {"type": "tool_use", "name": ..., "input": ..., "result": ...}, ... ],
      }

    The loop:
      1. Send the conversation (+ tools) to the model.
      2. If stop_reason == "tool_use": execute every tool_use block, append the
         assistant turn and a single user turn of tool_result blocks, repeat.
      3. Otherwise: collect the text blocks and return.
    """
    client = client or _client()

    messages: list[dict[str, Any]] = [{"role": "user", "content": user_message}]
    steps: list[dict[str, Any]] = []

    for _ in range(max_steps):
        response = client.messages.create(
            model=model,
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            tools=TOOL_SCHEMAS,
            messages=messages,
        )

        if response.stop_reason == "tool_use":
            # Append the assistant turn verbatim (must include tool_use blocks).
            messages.append({"role": "assistant", "content": response.content})

            tool_results: list[dict[str, Any]] = []
            for block in response.content:
                if block.type != "tool_use":
                    continue
                result = run_tool(block.name, dict(block.input))
                is_error = result.startswith("Error")
                steps.append(
                    {
                        "type": "tool_use",
                        "name": block.name,
                        "input": dict(block.input),
                        "result": result,
                    }
                )
                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result,
                        "is_error": is_error,
                    }
                )

            # All tool results go back in ONE user message.
            messages.append({"role": "user", "content": tool_results})
            continue

        # No more tool calls — gather the final text.
        reply = "".join(b.text for b in response.content if b.type == "text")
        return {"reply": reply.strip(), "steps": steps}

    # Hit the step cap without a final answer.
    return {
        "reply": "(stopped: reached the maximum number of tool-use steps)",
        "steps": steps,
    }
