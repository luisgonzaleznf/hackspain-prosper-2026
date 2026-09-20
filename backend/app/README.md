# Call infrastructure

Prosper dials our WebSocket, plays a patient, and scores what we report after hang-up.
Organiser docs: [`docs/prosper/`](../docs/prosper/README.md).

```
Prosper ──wss──▶ tunnel ──▶ app/server.py /ws        (Twilio Media Streams, 8 kHz µ-law)
                              │  CallSession.start()  per call: caller-ID lookup, JSONL log
                              ▼
                        app/voice/<VOICE>.py         the conversation (speech ⇄ model)
                              │  tools: app/tools.py ──▶ app/prosper.py ──▶ clinic API (live)
                              ▼
                        socket closes ─▶ session.finish() ─▶ POST /api/v1/submit/<action>
```

| File | Role |
|---|---|
| `server.py` | `/ws`: handshake → `TwilioFrameSerializer(auto_hang_up=False)` → `CallSession` → voice layer → `finish()` on close. `/health`. |
| `session.py` | Per-call state. Actions are **staged** during the call and POSTed once at hang-up (the window is 30 s), so a change of mind never leaves a wrong record. Nothing staged → a fallback `NO_ACTION(out_of_scope)`, because silence always fails. |
| `tools.py` | What the model calls: `find_patient`, `list_appointments`, `search_availability`, `record_*`, `clear_recorded_actions`. The `record_*` tools refuse anything this call did not look up: an unknown patient, an unoffered slot, a same-day slot, a plan that doesn't pay for the slot, a bad DNI check letter, a reason outside the closed vocabulary. |
| `prompt.py` | System prompt: receptionist rules + triage/red flags + dated calendar + catalogue + caller ID. |
| `clinic.py` | Catalogue cache (`GET /api/v1/clinic`), DNI/NIE check letter, calendar text. |
| `prosper.py` | httpx client for the clinic reads and the submit routes. |
| `voice/` | Voice layers picked by `VOICE`; `none` is a silent plumbing stub. |

## Run

```bash
make serve VOICE=codex        # ws://localhost:7860/ws  (reads PLATFORM_API_KEY from .env)
make session VOICE=codex      # connect for one run (auto-disconnects); see "Endpoint policy" in AGENTS.md
make smoke                    # live: a public case through the tools + a submit Prosper accepts
make fake-call WAV=x.wav N=10 # fake Prosper calls at the local server (8 kHz mono PCM16 wav)
```

Every call writes `logs/calls/<call_id>.jsonl`: caller-ID lookup, transcript, each tool call
with its result, staged actions, and what Prosper answered on submit.

Every call is also recorded off the wire by `recorder.py`, below the voice layer:
`logs/audio/<call_id>.wav` (stereo, caller left, agent right, one timeline) and `.timing.json`
(per-frame arrival/send times), both gitignored. The JSONL gets `first_agent_audio` live and an
`audio.timeline` summary after the submit: greeting time, response latency, dead air, barge-ins
and how fast the agent yields, agent stutter (underruns), caller-side stalls, levels, SNR and
clipping, plus a `flags` list. Scored calls have no Prosper audio until Monday's reveal; this is ours.

## Voice-layer contract

`app/voice/<name>.py` exposes `async def run_call(transport, session) -> None`:

- speak `session.greeting` first; use `session.instructions()` as the system prompt;
- give the model `app.tools.TOOLS` (flat `{"name","description","parameters"}` specs) and route
  every call through `await app.tools.call_tool(session, name, args)`, which never raises.
  Pipecat services can use `register_pipecat_tools(llm, session)`;
- log speech with `session.log("transcript", role="user" | "agent", text=...)`;
- return when the socket closes. **Never submit**: the server calls `session.finish()`.
