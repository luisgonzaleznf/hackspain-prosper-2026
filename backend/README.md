# backend — the agent, its clinic database and the call record

The voice agent (Twilio phone calls and the browser Studio), the clinic engine it reads and
writes, and the ROSARIO console API.

- **Clinic database.** Patients, the diary, closures and absences live in SQLite
  (`LOCAL_CLINIC_DB`, default `data/clinic.sqlite3`, gitignored). `make seed` rebuilds it from
  [`seed/`](seed/README.md): the 3 Arenal sites, 12 doctors, ~3000 patients and a densely booked
  4-week diary. Calls persist registrations, bookings, moves and cancellations as they happen.
- **Call artifacts.** `CALLS_DIR` / `AUDIO_DIR` default to `logs/` inside this package, so
  per-call JSONL and recordings land here for the console to read.

The phone and browser demos support opt-in [Resend appointment and welcome
emails](docs/appointment-email.md) from a verified custom domain. The
[Twilio integration](integrations/README.md) finalizes these locally at hang-up.

## Layout

| Path | Role |
|---|---|
| `app/` | The agent: server, session, prompt, tools, clinic catalogue, voice layers, recorder |
| `app/demo/` | Role-play Studio at `/demo/`, mounted on the call server (`make roleplay-demo`) |
| `app/dashboard.py`, `app/calls_api.py` | The ROSARIO console: read-only HTTP view of the call log (`make console`) |
| `integrations/` | The clinic engine (`local_clinic.py`), the database (`local_store.py`), Twilio |
| `seed/`, `scripts/seed_clinic.py` | The catalogue and the deterministic clinic seed |
| `tests/` | The unit suite, run against **this** copy via `pytest.ini` |
| `logs/calls/`, `logs/audio/` | Per-call JSONL and recordings. **Gitignored** |

## Run it

```bash
cp .env.example ../.env       # fill in the keys; .env stays out of git
make seed                     # build the clinic database (wipes local bookings)
make serve VOICE=codex        # writes logs/calls/<call_id>.jsonl here
make verify                   # ruff + mypy + pytest against this copy
make console                  # ROSARIO console on :8000
```
