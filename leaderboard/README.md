# leaderboard — the scored agent, and everything needed to run it

The agent Prosper dials and the harness we experiment with: voice layers, brain
(prompt + tools + session), clinic/submit client, endpoint helper, local eval harness,
the organiser contract and case data, and the unit suite.

This copy is the agent that scored **145** — identical to the repo root's `app/`
and `tests/` at `main@f7a7787`. Keep it that way: if the root agent changes,
re-copy, don't let the two drift silently.

Call artifacts (JSONL, transcripts, audio) do **not** live here. They land in
[`../backend/logs/`](../backend/logs/) via `CALLS_DIR` / `AUDIO_DIR`, and the
post-run ledger workflow runs from `../backend/` (or the repo root).

## Layout

| Path | Role |
|---|---|
| `app/server.py` | FastAPI `/ws` server Prosper dials; owns the call lifecycle and submit |
| `app/session.py` | Per-call state, logging, staged actions, `finish()` |
| `app/prompt.py` | The receptionist brain's system prompt and rules |
| `app/tools.py` | Request-scoped tool contract the model calls (lookup, availability, record_*) |
| `app/clinic.py`, `app/prosper.py` | Clinic reads and the Prosper submit client |
| `app/constraints.py`, `app/dates.py` | Constraint tracking, vague-time resolution |
| `app/recorder.py` | Both-legs call recording + the `audio.timeline` quality summary |
| `app/voice/codex/`, `gptlive/`, `gemini/`, `none.py` | Voice layers, picked by `VOICE` |
| `app/voice/deadair.py`, `app/voice/clips/` | Dead-air watchdog and its nudge audio |
| `tests/` | The 30-file unit suite, run against **this** copy via `pytest.ini` |
| `docs/prosper/` | Organiser contract, clinic docs, `data/public-cases.json`, OpenAPI |
| `docs/reviews/` | The improvement-review notes `app/README.md` links to |
| `scripts/endpoint.sh`, `scripts/menubar/` | Endpoint policy: connect only while a run is live |
| `scripts/preflight.py`, `smoke_tools.py`, `fake_caller.py`, `sim_caller.py` | Pre-run checks and local dialling |

## Run an experiment

```bash
cp .env.example .env          # PLATFORM_API_KEY, VOICE, optional NGROK_DOMAIN
make preflight                # keys + tooling
make serve VOICE=codex        # ws://0.0.0.0:7860/ws
make session VOICE=codex      # server + tunnel, auto-disconnects when idle
make verify                   # ruff + mypy + pytest against this copy
```

`make session` is the one command for a run: it waits until Prosper can actually
reach us and disconnects itself 90 s after the last call. Save the printed
`wss://…/ws` in dashboard Settings → Integration before pressing Call / Run all.

**Before any Run All**, follow the Run All protocol in
[`../AGENTS.md`](../AGENTS.md): commit and push the exact code being served, open
or update a PR, and write the run down on it first.
