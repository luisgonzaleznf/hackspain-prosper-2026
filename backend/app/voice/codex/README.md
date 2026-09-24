# `VOICE=codex` — GPT-Live on the ChatGPT/Codex subscription

GPT-Live-1 (OpenAI's full-duplex voice model) driven through the local Codex CLI, so it runs on a
ChatGPT/Codex **subscription with no API key**. Default voice in `app/config.py`.

    VOICE=codex make serve                                    # :7860, /integrations/twilio/ws

Requires the Codex CLI ≥ 0.154, logged in with ChatGPT (`codex login`), on the machine running
the server. Pattern taken from `reference/gpt-live-voice` (copied, not imported).

## How a call runs

Two models per call, both on the subscription:

- **the voice** (GPT-Live, full duplex) talks to the caller, handles turn-taking and barge-in,
  and delegates anything about patients, slots or rules;
- **the brain** (the Codex thread agent, `gpt-5.6-luna`, low effort) gets each delegation, runs
  `app.tools` and hands back what the voice should say.

| File | What it does |
|---|---|
| `__init__.py` | `run_call`: pipeline `transport.input() → CodexLiveService → transport.output()`; voice prompt; brain = `BRAIN_PREAMBLE + session.instructions()` |
| `service.py` | pipecat processor: caller audio in, agent audio out (with a 600ms hangover gate), transcripts to `session.log`, greeting via `appendSpeech` |
| `peer.py` | one call = one `codex app-server` + one aiortc WebRTC peer; tool calls (`item/tool/call`) → `call_tool(session, …)` |
| `rpc.py` | async JSON-RPC client for `codex app-server` (requests, notifications, server→client requests) |

## Things learned the hard way (codex-cli 0.154)

- **Only WebRTC works on a subscription.** The websocket transport (audio as JSON-RPC) fails
  with `realtime conversation requires API key auth`, so our server is the WebRTC peer.
- **No STUN** (`RTCConfiguration(iceServers=[])`): OpenAI's side is ICE-lite and public;
  aiortc's default STUN lookup adds ~5s to every call.
- **`-c mcp_servers={}`** when spawning: otherwise the operator's MCP servers start on every call.
- **Strip `OPENAI_API_KEY` / `CODEX_API_KEY`** from the child env or it leaves subscription auth.
- **Live relay only**: the input track keeps ≤200ms of backlog. Audio queued while the
  session connects would otherwise delay every later turn by the same amount.
- **Tools**: `thread/start` takes them as `dynamicTools`; the thread agent calls back with
  `item/tool/call` (answered with `{"contentItems": [{"type": "inputText", …}], "success": …}`).
  `clientManagedHandoffs` must be false so delegations reach the thread agent.

## Measured

- 10 concurrent calls on one account: 10/10 greet and reply; reply 1.3–1.7s after the caller
  stops; greeting ~3s alone, ~4.7s in a 10-call burst (one app-server spawned per call).
- With tools: filler ~4s, first real answer ~10s after the caller stops (each brain step ~3s).
- Weekly plan usage stayed at 0% after ~40 calls (voice time counts against the same weekly
  Codex bucket as coding work).

## Limits

- The subscription is meant for the account holder's own use; other people calling it is a
  grey area. It shares the weekly allowance with Codex coding on the same account.
- The CLI's `realtime_conversation` feature is experimental; a CLI update can change the protocol.
