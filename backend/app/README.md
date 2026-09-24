# Call infrastructure

A caller rings the clinic's number (Twilio) or opens the Role-play Studio in a browser, talks to
Rosario, and Rosario reads and writes the clinic database: `backend/data/clinic.sqlite3`
(gitignored; `make seed` builds it, `LOCAL_CLINIC_DB` overrides the path).

```
Twilio ──wss──▶ tunnel ──▶ app/server.py /integrations/twilio/ws   (Media Streams, 8 kHz µ-law)
                              │  session.start()  per call: caller-ID lookup, JSONL log
                              ▼
                        app/voice/<VOICE>.py         the conversation (speech ⇄ model)
                              │  tools: app/tools.py ──▶ integrations/local_clinic.py ──▶ clinic DB
                              │  confirmed writes ──▶ integrations/local_store.py (saved at once)
                              ▼
                        socket closes ─▶ session.finish() ─▶ outcome logged, follow-up email
```

| File | Role |
|---|---|
| `server.py` | `/integrations/twilio/ws`: handshake → `TwilioFrameSerializer(auto_hang_up=False)` → `TwilioCallSession` → voice layer → `finish()` on close. `/health`, and the Studio routes. |
| `session.py` | Per-call state. Actions are **staged** during the call so a change of mind never leaves a wrong record; `finish()` logs the outcome once. Nothing staged → an evidence-based `NO_ACTION` reason. Phone and browser calls (`integrations/local_session.py`) also save each confirmed write immediately. |
| `tools.py` | What the model calls: `find_patient`, `list_appointments`, `search_availability`, `record_*`. The `record_*` tools refuse anything this call did not look up: an unknown patient, an unoffered slot, a same-day slot, a plan that doesn't pay for the slot, a bad DNI check letter, a reason outside the closed vocabulary. |
| `prompt.py` | System prompt: receptionist rules + triage/red flags + dated calendar + catalogue + caller ID. |
| `clinic.py` | The catalogue: static from the clinic DB, calendar/closures/absences computed for today; DNI/NIE check letter; calendar text. `ClinicError`. |
| `calls_api.py`, `dashboard.py` | The console's read-only call log API, on its own local port. |
| `voice/` | Voice layers picked by `VOICE`; `none` is a silent plumbing stub. |

The clinic engine (`integrations/local_clinic.py`) generates free slots itself: a 15-minute grid
inside each doctor's hours at a site, minus booked appointments, closures, absences and the
patient's own diary, with the clinic's rules (age, referral, insurer network, coverage, site,
insurer authorisation, annual allowance, leave) reported per doctor in `blocked`.

## Run

```bash
make seed                     # build the clinic database (once, or to reset the diary)
make serve VOICE=gptlive      # :7860, Twilio stream at /integrations/twilio/ws
make console                  # the console API on localhost
```

Every call writes `logs/calls/<call_id>.jsonl`: caller-ID lookup, transcript, each tool call
with its result, staged actions, each saved write (`local_write`) and the outcome.

Optional [Resend appointment emails](../docs/appointment-email.md) send the final booking/move
summary after hang-up to the patient's email on file, or to an address the caller spells and
confirms. Disabled by default. Seeded charts use reserved demo domains (example.com, *.test),
which never receive mail. Customer enrollment also saves a local SQLite record before sending a
welcome email.

Every call is also recorded off the wire by `recorder.py`, below the voice layer:
`logs/audio/<call_id>.wav` (stereo, caller left, agent right, one timeline) and `.timing.json`
(per-frame arrival/send times), both gitignored. The JSONL gets `first_agent_audio` live and an
`audio.timeline` summary after the call: greeting time, response latency, dead air, barge-ins
and how fast the agent yields, agent stutter (underruns), caller-side stalls, levels, SNR and
clipping, plus a `flags` list.

## Voice-layer contract

`app/voice/<name>.py` exposes `async def run_call(transport, session) -> None`:

- speak `session.greeting` first; use `session.instructions()` as the system prompt;
- give the model `app.tools.tools_for_session(session)` (flat `{"name","description","parameters"}` specs) and route
  every call through `await app.tools.call_tool(session, name, args)`, which never raises.
  Pipecat services can use `register_pipecat_tools(llm, session)`;
- log speech with `session.log("transcript", role="user" | "agent", text=...)`;
- return when the socket closes. **Never finish the session**: the server calls `session.finish()`.
