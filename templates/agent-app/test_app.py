"""Tests that exercise the tool loop with the Anthropic call mocked.

No API key required: we patch `anthropic.Anthropic` so `client.messages.create`
returns scripted responses. This lets us assert the loop's control flow —
tool dispatch, the assistant/tool_result message shapes, and termination.

Run:  uv run pytest -q
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

from fastapi.testclient import TestClient

import agent
import main
from tools import get_time, run_tool, search


# ---------------------------------------------------------------------------
# Helpers to build fake Anthropic response objects (duck-typed).
# ---------------------------------------------------------------------------


def _text_block(text: str) -> SimpleNamespace:
    return SimpleNamespace(type="text", text=text)


def _tool_use_block(block_id: str, name: str, tool_input: dict) -> SimpleNamespace:
    return SimpleNamespace(type="tool_use", id=block_id, name=name, input=tool_input)


def _response(stop_reason: str, content: list) -> SimpleNamespace:
    return SimpleNamespace(stop_reason=stop_reason, content=content)


def _scripted_client(responses: list) -> MagicMock:
    """A fake Anthropic client whose .messages.create yields each response in turn."""
    client = MagicMock()
    client.messages.create.side_effect = responses
    return client


# ---------------------------------------------------------------------------
# Tool unit tests (no model involved).
# ---------------------------------------------------------------------------


def test_get_time_includes_timezone_label() -> None:
    assert "America/New_York" in get_time("America/New_York")


def test_search_finds_seed_doc() -> None:
    assert "Refunds are issued" in search("refund policy")


def test_search_handles_miss() -> None:
    assert "No results" in search("quantum entanglement")


def test_run_tool_unknown_returns_error_string() -> None:
    assert run_tool("nope", {}).startswith("Error")


# ---------------------------------------------------------------------------
# Agent loop tests (model mocked).
# ---------------------------------------------------------------------------


def test_single_tool_call_loop() -> None:
    """Model asks for one tool, then answers from the result."""
    responses = [
        _response("tool_use", [_tool_use_block("t1", "get_time", {"timezone": "UTC"})]),
        _response("end_turn", [_text_block("It is 14:30 UTC.")]),
    ]
    client = _scripted_client(responses)

    result = agent.run_agent("what time is it?", client=client)

    assert result["reply"] == "It is 14:30 UTC."
    assert len(result["steps"]) == 1
    step = result["steps"][0]
    assert step["name"] == "get_time"
    assert "current time in UTC" in step["result"]
    # Two model calls: one to request the tool, one to answer.
    assert client.messages.create.call_count == 2


def test_loop_sends_tool_results_in_one_user_message() -> None:
    """The second model call must carry the assistant tool_use turn + a user
    turn whose content is a list of tool_result blocks."""
    responses = [
        _response(
            "tool_use",
            [
                _tool_use_block("a", "get_time", {}),
                _tool_use_block("b", "search", {"query": "shipping"}),
            ],
        ),
        _response("end_turn", [_text_block("done")]),
    ]
    client = _scripted_client(responses)

    agent.run_agent("two things please", client=client)

    second_call_messages = client.messages.create.call_args_list[1].kwargs["messages"]
    # [user, assistant(tool_use), user(tool_result list)]
    assert second_call_messages[-1]["role"] == "user"
    result_blocks = second_call_messages[-1]["content"]
    assert {b["type"] for b in result_blocks} == {"tool_result"}
    assert len(result_blocks) == 2
    assert all("tool_use_id" in b for b in result_blocks)


def test_no_tool_call_returns_immediately() -> None:
    responses = [_response("end_turn", [_text_block("hello there")])]
    client = _scripted_client(responses)

    result = agent.run_agent("hi", client=client)

    assert result["reply"] == "hello there"
    assert result["steps"] == []
    assert client.messages.create.call_count == 1


def test_loop_respects_max_steps() -> None:
    """A model that never stops calling tools is cut off at max_steps."""
    looping = _response("tool_use", [_tool_use_block("x", "get_time", {})])
    client = MagicMock()
    client.messages.create.return_value = looping

    result = agent.run_agent("loop forever", max_steps=3, client=client)

    assert "maximum number of tool-use steps" in result["reply"]
    assert client.messages.create.call_count == 3


# ---------------------------------------------------------------------------
# HTTP endpoint tests (agent mocked).
# ---------------------------------------------------------------------------


def test_chat_endpoint(monkeypatch) -> None:
    monkeypatch.setattr(
        main,
        "run_agent",
        lambda message: {"reply": f"echo: {message}", "steps": []},
    )
    client = TestClient(main.app)

    res = client.post("/chat", json={"message": "ping"})

    assert res.status_code == 200
    assert res.json() == {"reply": "echo: ping", "steps": []}


def test_index_and_health_served() -> None:
    client = TestClient(main.app)

    assert client.get("/").status_code == 200
    assert "hack-kit agent" in client.get("/").text

    health = client.get("/health").json()
    assert health["status"] == "ok"
    assert health["demo_prompt"]
