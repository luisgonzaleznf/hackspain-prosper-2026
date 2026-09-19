# `VOICE=gemini` — Gemini Live

`gemini-3.8-live-extended-thinking`: Google's audio-to-audio model (GA 2026-09-15). It hears the
caller and speaks back directly, reasoning in the background while it talks. No STT/TTS in the
loop. `gemini-3.8-live` is the same family without the extended reasoning, if latency matters
more than thinking (set `GEMINI_LIVE_MODEL`).

    VOICE=gemini make serve                                   # ws://:7860/ws
    uv run python scripts/sim_caller.py simple_booking        # eval (needs the codex voice's sim)

## How a call runs

`__init__.py:run_call` builds one pipecat pipeline per call:

    transport.input() → user aggregator → GeminiLiveLLMService → transport.output() → assistant aggregator

- **Prompt**: `session.instructions()` plus `TOOL_RULES` (below) as the system instruction.
- **Greeting**: the context opens with one message asking it to say `session.greeting` verbatim;
  `LLMRunFrame` on connect opens the Live session and triggers it.
- **Tools**: `app.tools.register_pipecat_tools(llm, session)` → every call goes through
  `call_tool(session, …)`, so the same checked, staged tools as every other voice.
- **Transcript**: `session.log("transcript", role="user"|"agent", …)` from the aggregators'
  `on_user_turn_message_added` / `on_assistant_turn_stopped`.
- The Twilio µ-law 8k ↔ PCM conversion is `TwilioFrameSerializer` in `app/server.py`.

## Credentials

In the main checkout's `.env` (gitignored; `app/config.py` finds it from any worktree):

| Var | Value |
|----|----|
| `GEMINI_API_KEY` | API key "HackSpain Prosper 2026 (Gemini Live)", restricted to the Gemini API |
| `GEMINI_LIVE_MODEL` | `gemini-3.8-live-extended-thinking` |
| `GEMINI_VOICE` | optional, default `Charon` |

The key lives in GCP project `gen-lang-client-0897248429` ("Video Gen"). Usage bills to that
project's billing account ("My Billing Account", `0108CA-F7A047-682989`), credits first (about
€25, no spend cap), not the €100 card; once credits run out it falls through to the card on that
account. Remaining credit:
<https://console.cloud.google.com/billing/0108CA-F7A047-682989/credits>. A call costs roughly
$0.04: sample cases, don't loop full sweeps. Revoke after the event:

    gcloud services api-keys delete 2409a561-9000-447e-b171-7569bc287dfe --project=gen-lang-client-0897248429

## What the model expects (and why the code looks like this)

- **Live API only**: a WebSocket session (`client.aio.live.connect(...)` in `google-genai`).
  `generate_content` does not reach it.
- **Audio in**: raw 16-bit little-endian PCM. Any sample rate works if the mime type declares
  it (`audio/pcm;rate=8000`); the server resamples. **Audio out**: 16-bit PCM at 24kHz.
- **`thinking_level` is required.** `LOW` is the lowest it accepts (`MINIMAL` is rejected).
  pipecat ≥ 1.11 defaults it to `LOW`.
- **Every tool call is NON_BLOCKING** and can't be declared BLOCKING: the model keeps talking
  while a tool runs. Hence `TOOL_RULES`: say it is checking, never confirm a booking or name a
  slot before the result arrives.
- **Pin `google-genai>=2.19`**: pipecat's `google` extra only requires 1.68 on Linux + Python
  3.13 (i.e. Docker), and older SDKs miss the `interaction_status` events this model uses to
  mark the end of a reply.
- **One Live session per socket.** Run All opens ten at once.
- pipecat's service speaks `language_code=en-US` in its speech config by default; the model
  still follows the caller's language (see the eval results in the PR).

Verified directly against the key (2026-09-18, raw `google-genai`, before this pipeline existed):
a session connected in 0.65s, accepted 8kHz PCM and replied with 3.3s of Spanish audio; first
audio 1.6s after connecting.

Raw `google-genai` fallback, if pipecat gets in the way (turn-taking, barge-in via
`sc.interrupted` and resampling are then all ours):

```python
from google import genai
from google.genai import types

client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
config = types.LiveConnectConfig(
    response_modalities=["AUDIO"],
    system_instruction="Eres la recepcionista de una clínica en Madrid...",
    thinking_config=types.ThinkingConfig(thinking_level="LOW"),
)
async with client.aio.live.connect(model=os.environ["GEMINI_LIVE_MODEL"], config=config) as s:
    # per incoming Twilio frame: pcm = audioop.ulaw2lin(base64.b64decode(payload), 2)
    await s.send_realtime_input(audio=types.Blob(data=pcm, mime_type="audio/pcm;rate=8000"))
    async for r in s.receive():
        sc = r.server_content
        if sc and sc.model_turn:
            for p in sc.model_turn.parts:
                if p.inline_data:  # PCM16 @ 24kHz: downsample to 8k, lin2ulaw, send as `media`
                    ...
```

## Docs

- Model: <https://ai.google.dev/gemini-api/docs/models/gemini-3.8-live-extended-thinking>
- Live API (SDK): <https://ai.google.dev/gemini-api/docs/live-api/get-started-sdk>
- Async tools: <https://ai.google.dev/gemini-api/docs/live-api/tools#async-function-calling>
