"""hack-kit AI wrapper — the ONE chokepoint for model calls.

Feature code should import from here, never `import anthropic` directly. This is
where the model id, system prompt, retries, structured output, tool-calling, and
the provider swap all live, so swapping any of them is a one-file change.

Usage:
    from lib.ai import chat, stream, structured, run_with_tools, Model

    text = chat("Summarize this in one line: ...")
    text = chat("Plan this hard task", model=Model.HEAVY, effort="high")

    for piece in stream("Write a short story"):
        print(piece, end="", flush=True)

    class Person(BaseModel):
        name: str
        age: int
    person = structured("Extract: Alice is 30.", schema=Person)

Model ids are pinned (see CLAUDE.md). Do NOT invent ids.
"""

from __future__ import annotations

import os
from collections.abc import Callable, Iterator
from enum import Enum
from functools import lru_cache
from typing import Any, TypeVar

# Load .env once on import if python-dotenv is available; no-op otherwise.
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:  # pragma: no cover - dotenv is a normal dep, this is belt-and-suspenders
    pass


class Model(str, Enum):
    """Pinned model ids. Never invent ids — these are the only valid choices."""

    HEAVY = "claude-opus-4-8"  # planning, hard agentic work, the load-bearing AI feature
    DEFAULT = "claude-sonnet-4-6"  # most feature calls — good speed/quality balance
    FAST = "claude-haiku-4-5"  # classification, extraction, high-volume simple calls


# The default the wrapper uses when no model is passed. Overridable via env.
_DEFAULT_MODEL = os.environ.get("HACKKIT_MODEL", Model.DEFAULT.value)

# Models that use adaptive thinking + `effort` (the 4.6+ family). On these,
# `budget_tokens` 400s, so we never send it.
_ADAPTIVE_THINKING_MODELS = {
    Model.HEAVY.value,
    Model.DEFAULT.value,
}

T = TypeVar("T")


@lru_cache(maxsize=1)
def _client() -> Any:
    """Lazily build (and cache) the Anthropic client.

    Imported lazily so that importing lib.ai never hard-fails if the SDK or key
    is missing — the error surfaces only when you actually make a call.
    """
    import anthropic

    key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not key:
        raise RuntimeError(
            "ANTHROPIC_API_KEY is not set. Copy .env.example to .env and add your key, "
            "then re-run. (Run `make preflight` to check.)"
        )
    return anthropic.Anthropic(api_key=key)


def _resolve_model(model: Model | str | None) -> str:
    if model is None:
        return _DEFAULT_MODEL
    if isinstance(model, Model):
        return model.value
    return model


def _build_kwargs(
    model_id: str,
    effort: str | None,
    thinking: bool,
) -> dict[str, Any]:
    """Assemble the optional thinking/effort kwargs correctly per model family."""
    kwargs: dict[str, Any] = {}
    if model_id in _ADAPTIVE_THINKING_MODELS:
        if thinking:
            kwargs["thinking"] = {"type": "adaptive"}
        if effort is not None:
            kwargs["output_config"] = {"effort": effort}
    # FAST / non-adaptive models: skip thinking + effort (effort 400s on Haiku).
    return kwargs


def chat(
    prompt: str,
    *,
    model: Model | str | None = None,
    system: str | None = None,
    max_tokens: int = 16000,
    effort: str | None = None,
    thinking: bool = False,
) -> str:
    """One-shot text completion. Returns the joined text of the response.

    Args:
        prompt: the user message.
        model: a Model or raw id; defaults to HACKKIT_MODEL / Sonnet.
        system: optional system prompt.
        max_tokens: output cap. ~16000 is a safe non-streaming default.
        effort: "low" | "medium" | "high" (only applied on adaptive-thinking models).
        thinking: enable adaptive thinking (only on adaptive-thinking models).
    """
    model_id = _resolve_model(model)
    create_kwargs: dict[str, Any] = {
        "model": model_id,
        "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": prompt}],
        **_build_kwargs(model_id, effort, thinking),
    }
    if system is not None:
        create_kwargs["system"] = system

    resp = _client().messages.create(**create_kwargs)
    return _text_of(resp)


def stream(
    prompt: str,
    *,
    model: Model | str | None = None,
    system: str | None = None,
    max_tokens: int = 64000,
    effort: str | None = None,
    thinking: bool = False,
) -> Iterator[str]:
    """Stream a completion, yielding text chunks as they arrive.

    Use for long outputs (large max_tokens) to avoid HTTP timeouts.
    """
    model_id = _resolve_model(model)
    create_kwargs: dict[str, Any] = {
        "model": model_id,
        "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": prompt}],
        **_build_kwargs(model_id, effort, thinking),
    }
    if system is not None:
        create_kwargs["system"] = system

    with _client().messages.stream(**create_kwargs) as s:
        yield from s.text_stream


def structured(
    prompt: str,
    *,
    schema: type[T],
    model: Model | str | None = None,
    system: str | None = None,
    max_tokens: int = 16000,
) -> T:
    """Structured output: returns a validated instance of `schema` (a pydantic model).

    Uses the SDK's `messages.parse()`, which constrains the response to the schema
    and validates it for you.
    """
    model_id = _resolve_model(model)
    parse_kwargs: dict[str, Any] = {
        "model": model_id,
        "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": prompt}],
        "output_format": schema,
    }
    if system is not None:
        parse_kwargs["system"] = system

    resp = _client().messages.parse(**parse_kwargs)
    return resp.parsed_output  # type: ignore[no-any-return]


def run_with_tools(
    prompt: str,
    *,
    tools: list[dict[str, Any]],
    handlers: dict[str, Callable[[dict[str, Any]], Any]],
    model: Model | str | None = None,
    system: str | None = None,
    max_tokens: int = 16000,
    max_turns: int = 8,
) -> str:
    """Run a manual tool-use loop until the model stops calling tools.

    Args:
        tools: a list of tool definitions ({"name", "description", "input_schema"}).
        handlers: maps tool name -> a function (tool_input dict) -> result (str-able).
        max_turns: safety cap on the agentic loop.

    Returns the final text response.
    """
    model_id = _resolve_model(model)
    client = _client()
    messages: list[dict[str, Any]] = [{"role": "user", "content": prompt}]

    base: dict[str, Any] = {"model": model_id, "max_tokens": max_tokens, "tools": tools}
    if system is not None:
        base["system"] = system

    last = None
    for _ in range(max_turns):
        resp = client.messages.create(messages=messages, **base)
        last = resp

        if resp.stop_reason != "tool_use":
            break

        # Append the assistant turn (incl. tool_use blocks), then run each tool.
        messages.append({"role": "assistant", "content": resp.content})
        tool_results: list[dict[str, Any]] = []
        for block in resp.content:
            if getattr(block, "type", None) != "tool_use":
                continue
            handler = handlers.get(block.name)
            if handler is None:
                result_content: str = f"Error: no handler registered for tool {block.name!r}"
                is_error = True
            else:
                try:
                    result_content = str(handler(block.input))
                    is_error = False
                except Exception as e:  # noqa: BLE001 — surface tool failures to the model
                    result_content = f"Error running {block.name}: {type(e).__name__}: {e}"
                    is_error = True
            tool_results.append(
                {
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": result_content,
                    "is_error": is_error,
                }
            )
        messages.append({"role": "user", "content": tool_results})

    return _text_of(last) if last is not None else ""


def _text_of(resp: Any) -> str:
    """Join the text blocks of a Message response."""
    return "".join(
        block.text for block in resp.content if getattr(block, "type", None) == "text"
    )


# ─────────────────────────────────────────────────────────────────────
# Provider swap (optional, stub)
#
# Anthropic is primary. If you ever need an OpenAI/Gemini fallback, fill in
# these stubs and route `chat()` through `complete()` instead. Kept minimal so
# the primary path stays the obvious one.
# ─────────────────────────────────────────────────────────────────────


def _openai_complete(prompt: str, *, system: str | None, max_tokens: int) -> str:
    """STUB: OpenAI fallback. Implement only if you actually need it.

    Requires OPENAI_API_KEY and the `openai` package (not a default dep — add it
    with `uv add openai` if you wire this up).
    """
    raise NotImplementedError(
        "OpenAI fallback is a stub. Add `openai` (uv add openai), set OPENAI_API_KEY, "
        "and implement _openai_complete if you need it."
    )


def _gemini_complete(prompt: str, *, system: str | None, max_tokens: int) -> str:
    """STUB: Gemini fallback. Implement only if you actually need it.

    Requires GEMINI_API_KEY and the `google-genai` package (add with `uv add google-genai`).
    """
    raise NotImplementedError(
        "Gemini fallback is a stub. Add `google-genai` (uv add google-genai), set "
        "GEMINI_API_KEY, and implement _gemini_complete if you need it."
    )


def complete(
    prompt: str,
    *,
    provider: str = "anthropic",
    system: str | None = None,
    max_tokens: int = 16000,
) -> str:
    """Provider-routed one-shot completion. Defaults to Anthropic (the real path).

    `provider` is "anthropic" | "openai" | "gemini". The non-Anthropic paths are
    stubs — Anthropic is primary.
    """
    if provider == "anthropic":
        return chat(prompt, system=system, max_tokens=max_tokens)
    if provider == "openai":
        return _openai_complete(prompt, system=system, max_tokens=max_tokens)
    if provider == "gemini":
        return _gemini_complete(prompt, system=system, max_tokens=max_tokens)
    raise ValueError(f"Unknown provider: {provider!r}. Use 'anthropic', 'openai', or 'gemini'.")
