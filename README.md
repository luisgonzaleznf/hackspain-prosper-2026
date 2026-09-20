<p align="center">
  <img src=".github/assets/rosario-logo.svg" width="640" alt="Rosario">
</p>

<p align="center">
  <a href="#results"><img src="https://img.shields.io/badge/HackSpain-2026-000000?style=flat-square" alt="HackSpain 2026"></a>
  <a href="#results"><img src="https://img.shields.io/badge/Prosper-172%20points-BC0400?style=flat-square" alt="Prosper: 172 recorded points"></a>
  <a href="#how-it-works"><img src="https://img.shields.io/badge/Python%20%2B%20React-000000?style=flat-square" alt="Built with Python and React"></a>
</p>

---

Rosario is a voice receptionist for clinics. It answers scheduling calls, looks up patients and available appointments, and records bookings, changes, cancellations or a reason it cannot help. It speaks Spanish, Catalan, Galician, Basque and English, with a console for listening back to calls and inspecting the decisions behind them.

The project uses Clínica Arenal's synthetic records for the Prosper track at HackSpain 2026.

[Quickstart](#run-locally) · [Results](#results) · [Public repository](https://github.com/luisgonzaleznf/hackspain-prosper-2026) · [Private repository](https://github.com/luisgonzaleznf/hackspain-prosper-2026-private)

## Why

A scheduling call can change halfway through. A caller corrects their insurer, asks for another doctor, switches language or calls on behalf of a parent. Rosario keeps the lookup results and appointment actions for each call, so it can handle a changed request without starting the conversation over.

The console pairs each transcript with the call's tool results and reported outcomes. You can listen to the call recording and inspect the records behind a decision.

## What happens on a call

Rosario asks for identifying details and looks up the patient before handling their request. It searches the clinic's availability with the requested specialty, doctor, site and time constraints. The action tools reject slots and appointments that do not match the call's lookup evidence.

A caller can request several appointments, move or cancel an existing one, or start a new-patient registration. Rosario can ask follow-up questions when several records match, explain a policy refusal, report that no eligible slot is available or escalate a medical request. Identity confirmation and consent still depend partly on the conversation; the tool checks are not a complete authorization system.

The scored agent keeps actions pending while the caller is talking, then submits the final outcomes after hang-up, including refusals and escalations. Browser and Twilio calls instead save confirmed patient registrations and appointment changes immediately to a local SQLite database. Later calls can find those records, and local bookings block overlapping slots.

Prosper's clinic API remains read-only. Scored booking reports and local demo appointments do not change its records. The calendar shows saved local appointments by default, with a separate Call reports view for scored scheduling reports.

## The console

<p align="center">
  <img src=".github/assets/rosario-console.png" width="1024" alt="Rosario's overview with call counts, reported bookings, response gaps and a chart of reception activity">
</p>

The overview shows call volume, reported bookings, call duration and measured response gaps. Calls open into a transcript, stereo recording and decision timeline. Selecting a message seeks the recording; selecting a tool marker opens its inputs and result. Raw events remain available when the summary is not enough.

Without a local call server configured, the call library reads an imported snapshot of private rehearsal logs. It contains 469 call logs and 139 playable recordings. These are archived calls, not simulated live activity. Rehearsal verdicts in the console are local comparisons against the published cases, not official leaderboard results.

The Roleplay Studio at `/demo/` starts a real browser conversation with the voice backend. Choose a caller role, allow microphone access and review the recording after hanging up. The separate `/talk` page plays recordings or previews the local microphone; it does not place a call.

Voice settings offer nine voice samples, an English or Spanish opening and optional tone guidance. The backend saves them through `/api/demo/settings` and applies them to new Studio calls. They do not change active calls, existing recordings or the scored agent.

## Phone calls and email

The public backend accepts inbound Twilio calls through the same clinic tools. With Resend enabled, callers can spell and confirm an email address to receive a labelled demo appointment summary after hang-up. They can also consent to a local customer record and a welcome email. That customer record does not create a clinic patient or a login.

Email is off by default. In the public backend, scored calls never send it, and browser and Twilio demo calls do not submit outcomes to Prosper. See the [Twilio setup](https://github.com/luisgonzaleznf/hackspain-prosper-2026/blob/main/backend/integrations/README.md) and [email setup](https://github.com/luisgonzaleznf/hackspain-prosper-2026/blob/main/backend/docs/appointment-email.md).

## Results

Rosario recorded **172 points** on 19 September 2026. The final evidence records all four cases passing in each of the 17 scored groups after the nearest-site and clinician-question fixes. The [private evidence commit](https://github.com/luisgonzaleznf/hackspain-prosper-2026-private/commit/75dfa5e18d9822e34e89f2855d875f5ccf9d0d0e) includes the final runs and their recordings.

That result covers the competition's scripted cases. It does not establish clinical readiness. The same evidence notes that short caller acknowledgements can still split an answer mid-sentence. The console's pinned recording snapshot predates those final runs, so its statistics are not a breakdown of the 172-point result.

## Run locally

### Frontend and recorded calls

Use Node.js 24, pnpm and Python 3. Start from this checkout's root:

```sh
cd frontend
pnpm install --frozen-lockfile
pnpm dev --host 127.0.0.1
```

Open [localhost:5173](http://localhost:5173) for the landing page or [localhost:5173/calls](http://localhost:5173/calls) for the console. The landing page works without credentials. The call library needs the private recording dataset.

To import it, install `gh`, `ffmpeg` and `ffprobe`, then authenticate a GitHub account with access to the private repository. In another terminal, from `frontend/`:

```sh
gh auth login
pnpm recordings:import
```

Reload the console after the import. Files stay in the ignored `frontend/.recordings/` directory. The importer uses a pinned revision; pass `--revision <full-commit-sha>` to select another one. Without private-repository access, the historical call library is unavailable. See the [console notes](frontend/CONSOLE.md) for call review behavior.

### Voice backend

The public repository contains the packaged backend and scored agent. If this checkout does not contain `backend/`, clone the public repository into a separate directory. From that repository's root, create the ignored environment file:

```sh
cp backend/.env.example .env
```

Set `PLATFORM_API_KEY` and `OPENAI_API_KEY` in that file. Browser and Twilio calls need Python 3.12 or newer, `uv`, and API access to the configured GPT-Live and reasoning models.

```sh
cd backend
uv sync --frozen
uv run --project . --env-file ../.env python -m app.demo.bot --host 127.0.0.1 --port 7860
```

With the frontend running, open [localhost:5173/demo/](http://localhost:5173/demo/). It proxies the Studio requests to port 7860. Set `ROSARIO_DEMO_API` when starting the frontend if the backend runs elsewhere. The backend's [Studio documentation](https://github.com/luisgonzaleznf/hackspain-prosper-2026/blob/main/backend/app/demo/README.md) covers the rehearsal and saved call files.

To show live calls and saved appointments, run `make console CONSOLE_PORT=8001` from `backend/` in another terminal. Restart the frontend with `ROSARIO_CLINIC_API=http://127.0.0.1:8001 pnpm dev --host 127.0.0.1`. Both backend processes must use the same `LOCAL_CLINIC_DB` if you override its default path. This mode does not need the private recording import.

## How it works

Python, FastAPI and Pipecat handle the call transport. GPT-Live handles speech and delegates clinic work to a reasoning model with patient, availability and action tools. Each call keeps its own lookup evidence and action history. JSONL logs record transcripts, tool results and outcomes, with stereo audio for review. The scored agent also supports a Codex subscription voice connection through an experimental protocol.

The console uses React, TypeScript and Vite. Its recording middleware serves imported logs and audio locally, or the frontend can connect to the local call and calendar server. The browser derives the transcript and decision timeline from recorded events. The landing page and brand assets share the frontend directory.

| Code | Purpose |
| --- | --- |
| [frontend/](frontend/) | Landing page, console, Roleplay Studio and recording importer. |
| [backend/](https://github.com/luisgonzaleznf/hackspain-prosper-2026/tree/main/backend) | Voice runtime, clinic tools, call logs, Twilio and optional email. |
| [leaderboard/](https://github.com/luisgonzaleznf/hackspain-prosper-2026/tree/main/leaderboard) | Scored agent and Prosper endpoint tooling, separate from demo email. |
| [frontend/CONSOLE.md](frontend/CONSOLE.md) | Console behavior and call review notes. |

The public and private repositories are not identical. The private repository retains call evidence and rehearsal tooling; the public repository omits private call material. Public `main` combines live Prosper reads with local patient and appointment storage. It does not ship a frozen clinic database or write appointments back to Prosper.

## Demo boundaries

Use synthetic clinic data and email addresses volunteered for the demo. The public demo endpoints and review URLs do not have a production login, and the Twilio integration does not validate request signatures. Keep tunnels limited to supervised calls; an exposed endpoint can incur model and email charges. Keep credentials, local databases and call recordings out of the public repository.
