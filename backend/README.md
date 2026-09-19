# backend — the same agent, plus the call record

A second copy of the scored agent (same lineage as [`../leaderboard/`](../leaderboard/)
and the repo root at `main@f7a7787`), with two differences:

1. **It owns the call artifacts.** `CALLS_DIR` / `AUDIO_DIR` default to `logs/` inside
   this package, so per-call JSONL and recordings land here for the frontend to read.
2. **It carries the post-run workflow.** `scripts/collect_calls.py`,
   `collect_run_audio.py`, `call_ledger.py`, `call_costs.py` and `docs/private-calls/`
   are here, so the mandatory after-every-Run-All ledger refresh can run from this
   package. (The repo root's copies remain the ones `AGENTS.md` names; this is a
   deliberate duplicate, not a replacement — do not let the two ledgers diverge.)

This is where extra tools and the HTTP surface the frontend needs will land.

## Layout

| Path | Role |
|---|---|
| `app/` | The agent: server, session, prompt, tools, clinic/Prosper client, voice layers, recorder |
| `app/demo/` | Role-play Studio at `/demo/`, mounted on the call server (`make roleplay-demo`) |
| `app/dashboard.py`, `app/calls_api.py` | The ROSARIO console: read-only HTTP view of the call log (`make console`) |
| `tests/` | The unit suite, run against **this** copy via `pytest.ini` |
| `docs/prosper/` | Organiser contract, clinic docs, case data, OpenAPI |
| `docs/private-calls/` | Call ledger, dashboard export, per-call dossiers. **Gitignored here** (`**/docs/private-calls/`) |
| `logs/calls/` | Per-call JSONL. Committed in the private repo; **gitignored in this public mirror** |
| `logs/audio/`, `logs/run_audio/` | Recordings. Kept on disk; **gitignored here** — private call material stays out of the mirror |
| `scripts/` | Serve/dial/endpoint helpers, plus collect + ledger |

## Run it

```bash
cp .env.example .env
make serve VOICE=codex        # writes logs/calls/<call_id>.jsonl here
make verify                   # ruff + mypy + pytest against this copy
make console                  # ROSARIO console on :8000
```

## After a Run All

```bash
make collect                                  # gather per-call JSONL from every checkout
make run-audio                                # the run's Prosper recordings as Opus
make ledger DASHBOARD=/path/to/fresh-export.json
```

A fresh authenticated dashboard export is required — a stale snapshot does not count.
See [`../AGENTS.md`](../AGENTS.md) and [`docs/private-calls/README.md`](docs/private-calls/README.md).
