# Team dashboard (logged in)

Investigated 2026-09-18 ~18:00 UTC in Chrome with the team's session. Everything was read-only: GET requests only, and no Call, Run All or Save pressed.

## Our team

| | |
|---|---|
| Team name | **refugia2** |
| team_id | `9a279f4e-d8e1-4811-a7a4-3c86da8447fd` |
| API key | active (the value is not shown on the dashboard; it came from the desk) |
| Endpoint | **`wss://placeholder.invalid/ws`**, still the placeholder. It must be set in **Settings → Integration** before any call can reach us |
| Standing / points | none yet |

### The first call has already happened (and failed)

At **18:00:04 UTC** a practice run hit us: run `a73fabee-1ef6-4a01-a47f-1fa76b7f5f6c`, `public: true`, one case, **The Simple Booking · silence**, call_id `d386ac72-…`.

- The result was `failed`, attribution `agent_issue`, signals `endpoint_unreachable` and `missing_record`.
- It came exactly on the hour. The docs say organisers place **smoke calls at every endpoint**; the only other explanation is someone on the team pressing Call.
- Practice runs score nothing. **But Settings now shows "Where you are losing cases: 1 on every field".** That is only this unreachable call.

What a practice run's detail exposes, which is useful to build our own tooling against:

```json
{"call_id":"…","label":"The Simple Booking · silence","status":"failed","problem_id":"simple_booking",
 "fields":[{"field":"slot","expected":"2026-09-19T11:00:00+02:00","submitted":null,"matched":false}, …],
 "transcript":[],"has_audio":false,"attribution":"agent_issue",
 "signal_codes":["endpoint_unreachable","missing_record"],"points":null,"points_available":null}
```

For public cases, `expected` is shown per field next to what we `submitted`. Private (scored) cases hide this until the Monday reveal.

## Pages

| Page | What's there |
|---|---|
| **Problems** | The open problems with a Scoring dots bar and a Submissions count. **Run all** sits top-right. Clicking a problem opens its statement and public cases, each with a **Call** button and a green action tag (`book`, `no action`, …) |
| **Clinic records** | Browse and search the 2,900 patients (name / DNI-NIE / phone), plus providers, sites, specialties, types and plans. A per-provider availability view is included. See [clinic.md](clinic.md) |
| **Runs** | Each run with its state and per-case verdicts as they land. Cancelling is safe |
| **Settings** | Team stats, **Integration** (Endpoint + Headers, then **Save endpoint**), API key status, "Last call to you", and **"Where you are losing cases"**, a per-field failure histogram |
| **Standings** | The public leaderboard |

The banner reads **€100 allowance card per team**, "for whatever you build on (OpenAI, ElevenLabs, anything else)". Claim it at the registration desk.

## Open problems right now

| # | problem_id | Weight | Public cases |
|---|---|---|---|
| 1 | `simple_booking` | 1 | 4 |
| 2 | `switchboard` | 0 | 3 bursts (5, 10, 20 simultaneous problem-1 calls) |
| 3 | `doctor_and_site` | 2 | 5 |

Today's accepted answers for these public cases match `data/public-cases.json`, since both are anchored to 09:00 on 18 Sep. Two notable ones:

- `doctor_and_site-570e40a3f718`: the caller wants a non-existent "Dr. Fuentes" and will see nobody else, so the answer is `NO_ACTION(provider_not_found)`.
- `doctor_and_site-9904a6d96cdd`: Sáez at Centro on a Monday. He is only at Centro on Fridays, so the answer is his earliest Centro slot on any day, `2026-09-25T09:30`, as a `first_visit`.

The Switchboard statement tells us to trigger it ourselves **before our first scored run**.

## Dashboard-internal API (session cookie, under `/leaderboard/api`)

Not part of the public contract, but it is what the UI calls.

**Reads (safe):**

| Route | Returns |
|---|---|
| `GET /session` | viewer `{team_id, organiser, dev, viewing_as}` |
| `GET /problems` | the open problems `[{id,title,number,weight,examples}]` |
| `GET /problems/{id}` | statement + public cases with `accepted` action lists and `dials` |
| `GET /problems/{id}/submissions` | `{passed, failed, attempts}` |
| `GET /teams/{team_id}` | stats, eligibility (`active_run`, `public_wait`, `private_wait`), integration, **runs with per-field expected/submitted**, submissions |
| `GET /board` | public standings, `frozen` flag |
| `GET /clinic` | the full catalogue ([clinic.md](clinic.md)) |
| `GET /clinic/patients?name=&national_id=&phone=&offset=&limit=` | patient search, `limit` ≤ 100 |
| `GET /clinic/patients/{patient_id}` | one record incl. **all past appointments** |
| `GET /clinic/providers/{id}/availability?date_from&date_to[&patient_id]` | a provider's slots with `payable_with` per slot, plus `blocked` |

On search: name search on the dashboard is **fuzzy and ranked**. "Maria Garcia" returned María González, Mario García, Laura García and more, each with `matched_fields: ["name"]`. Phone search takes E.164 (`+34…`). The public `/api/v1/directory` is documented as exact-field *filtering*; check its behaviour with the API key before relying on either.

**Writes (the buttons; don't script these casually):**

| Route | Button |
|---|---|
| `POST /problems/{id}/runs` | **Call**: one practice call. 30 s cooldown |
| `POST /runs` | **Run all**: the scored run. 15 min cooldown after it finishes; blocks the slot for ~18 min |
| `PUT /endpoint` `{endpoint, headers}` | **Save endpoint**. Replaces both fields |

## Leaderboard at 17:59 UTC

1. Lluc: 3.0 · 2. Test: 0.0. Not frozen. We're not on it until we complete a Run All.
