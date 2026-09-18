# agent-app — tool-calling agent starter

A minimal, **actually-runnable** FastAPI app that demonstrates a multi-step
tool-calling loop with the Anthropic SDK, plus a clean single-page chat UI.
Graft it into a hackathon project and replace the example tools with real ones.

## What's here

| File            | Role                                                                 |
| --------------- | -------------------------------------------------------------------- |
| `main.py`       | FastAPI app: serves the UI and a `/chat` endpoint                    |
| `agent.py`      | The tool-calling loop (manual agentic loop over the Messages API)    |
| `tools.py`      | Example tools: `get_time` and a fake `search`                        |
| `seed.py`       | Deterministic seed data + the canned demo prompt                     |
| `index.html`    | Single-page chat UI (no build step)                                  |
| `test_app.py`   | Pytest suite — Anthropic call mocked, **passes with no API key**     |

Default model: **`claude-sonnet-4-6`** (override with the `MODEL` env var).

## Run it

```bash
# from this directory
export ANTHROPIC_API_KEY=sk-ant-...        # required for live calls
uv run uvicorn main:app --reload
```

Open <http://127.0.0.1:8000>. The input is pre-filled with a demo prompt that
exercises both tools ("What's your refund policy, and what time is it right
now?"). Tool calls are shown inline in the chat.

> No `uv`? `pip install -e ".[dev]"` then `uvicorn main:app --reload`.

## Test it (no API key needed)

```bash
uv run pytest -q
```

The tests patch `anthropic.Anthropic`, so the loop's control flow — tool
dispatch, message shapes, termination — is verified without any network call.

## Lint / type-check

```bash
uv run ruff check .
uv run mypy .
```

## How the loop works

`run_agent()` in `agent.py`:

1. Send the conversation + tool schemas to the model.
2. If `stop_reason == "tool_use"`: run every `tool_use` block, append the
   assistant turn and **one** user turn containing all `tool_result` blocks,
   then loop.
3. Otherwise: concatenate the text blocks and return the reply + a tool trace.

A `MAX_STEPS` cap guards against a model that never stops calling tools.

## Make it yours

- **Add a tool:** write a function in `tools.py`, add its JSON schema to
  `TOOL_SCHEMAS`, register it in `TOOL_FUNCTIONS`. The loop picks it up.
- **Swap the model:** `export MODEL=claude-opus-4-8` (or `claude-haiku-4-5`).
- **Real retrieval:** replace `search()` with a vector store (see
  `../../recipes/rag.md`).
- **Streaming:** see `../../recipes/streaming-chat.md`.
