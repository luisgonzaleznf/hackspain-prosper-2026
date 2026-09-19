# Prosper Track: organiser docs

Captured 2026-09-18 ~19:50 CEST from https://hackspain.getprosperapp.com (the site redirects to `/leaderboard/`). The site is a single-page app, so the text was pulled by rendering each docs page in a headless browser. The raw API schema and the practice-case file came straight from their public URLs. **The live site wins over this copy.** Organisers say rule changes are announced with old and new wording, so re-scrape if something smells off.

## Files

| File | What it is |
|---|---|
| [pages/01-overview.md](pages/01-overview.md) | "El Turno: the short version." One page covering what you build, how the weekend runs and how scoring works |
| [pages/02-challenge.md](pages/02-challenge.md) | Who Prosper is, the challenge, **who wins**, and the jury criteria |
| [pages/03-quickstart.md](pages/03-quickstart.md) | Get on the phone: account/key, WebSocket server, ngrok, endpoint config, calling yourself, what to build first |
| [pages/04-call-contract.md](pages/04-call-contract.md) | The wire (Twilio Media Streams), the submission window, `POST /submit/<action>`, the `reason` vocabulary |
| [pages/05-clinic.md](pages/05-clinic.md) | Clínica Arenal: the read-only EHR, its rules and traps, the calendar, and the scheduling guidelines the jury scores |
| [pages/06-scoring-rules.md](pages/06-scoring-rules.md) | What passes, the two lanes, points, call limits, failure attribution, recordings, freeze/reveal times |
| [pages/07-normalization.md](pages/07-normalization.md) | Exactly what the scorer forgives (DNI, names, phone, email, slot, enums) |
| [pages/08-problems.md](pages/08-problems.md) | The 18 problems, weights, open status, triage table, red flags |
| [pages/09-api-docs.md](pages/09-api-docs.md) | Pointer page to ReDoc/Swagger |
| [dashboard.md](dashboard.md) | **Logged-in dashboard:** our team (refugia2), the first failed smoke call, the pages, and the dashboard's internal API |
| [clinic.md](clinic.md) | **The clinic catalogue as tables:** sites + coordinates, the 12 providers with schedules and languages, specialties, plans, types, restrictions, patient-directory stats |
| [api-reference.md](api-reference.md) | Every endpoint, parameter and schema, generated from the OpenAPI spec |
| [public-cases.md](public-cases.md) | Index of all 73 published practice cases with their accepted answers |
| [data/openapi.json](data/openapi.json) | Raw OpenAPI 3 schema (`GET /api/openapi.json`, no key needed) |
| [data/public-cases.json](data/public-cases.json) | Raw published cases: persona, caller prompt, audio, expected actions |

## Dates (Europe/Madrid)

| When | What | Source |
|---|---|---|
| Fri 18 Sep | Challenge opens. Collect account + key + €100 card at the desk | site |
| **Sat 19 Sep 11:00** | Checkpoint prize #1: team ranked first on the board | organiser WhatsApp |
| **Sat 19 Sep 22:00** | Checkpoint prize #2: team ranked first on the board | organiser WhatsApp |
| **Sun 20 Sep 06:00** | **Wall freezes.** Only Run Alls completed by then count | scoring rules |
| Sun 20 Sep | Final boss: the jury calls the agent and reviews the platform | site |
| Mon 21 Sep 00:00 | Reveal: transcripts and audio of scored (private) calls open to each team | scoring rules |
| End of event | Final prize, €1,000. The leaderboard is **not** the only criterion; the jury's final test counts too | organiser WhatsApp |

The organisers said they would DM the full test details to each team that messages them privately with its team name. **That still needs doing by a human on the team.**

## Setup facts

- **Accounts come from the desk only.** It gives you an email login, a generated dashboard password and the team API key `pk-…`, each shown once. A lost key is rotated at the desk; a lost password means a new account. You also get a **€100 prepaid card** for all spend (models, STT/TTS, tunnels), with no top-up.
- **API host:** `https://hackspain.getprosperapp.com` serves `/api/v1/*`. `GET /api/v1/health` → `{"status":"healthy"}` works without a key. Everything else needs the `X-Api-Key` header; a bad key returns `403 {"detail":"Invalid API key"}`.
- **Endpoint:** you set it yourself on dashboard **Settings → Integration** as `wss://host/path`, with the path included. Optional headers go one per line, and header values are write-only. A run snapshots the endpoint when it is admitted.
- **Wire:** Twilio Media Streams over a plain WebSocket. The sequence is `connected` → `start` → `media` → `stop`. Audio is 8 kHz µ-law in 20 ms base64 frames. `sequenceNumber`, `chunk` and `timestamp` are **strings**, and every key is camelCase.
  - `start.callSid` **is the `call_id`**. Never mint your own.
  - `start.customParameters.from_number` holds the E.164 caller ID. It is **absent when withheld**. Treat it as a hint: it finds the line owner's chart, and the caller is not always the patient.
  - There is no server-side barge-in, and `clear` does nothing on their side. Turn-taking is entirely ours.
- **Concurrency:** Run All opens **10 sockets at once**, and the Switchboard burst opens up to **20**. Build a fresh pipeline for every connection and share no state across them.
- **Submissions:** `POST /api/v1/submit/{register|book|reschedule|cancel|no-action|escalate}`, one action per request, with snake_case JSON.
  - The window closes **30 s after their socket closes**. Late → `410`. A duplicate → `409` (that is expected). A bad body → `422`. An unknown `call_id` → `404`.
  - `200` means received, not passed.
  - **An empty submission always fails.** A refusal still needs `no-action` with a reason.
- **Limits:**
  - Calls are capped at **3 min**. Silence, meaning no audible audio from us, cuts the call and counts against the agent.
  - One queued or active run at a time, across both lanes.
  - **30 s** between practice calls. **15 min** cooldown after a Run All finishes.
  - A Run All takes about 18 min, so plan on one every ~33 min.

## Scoring

- `points = Σ over problems (pass fraction of its 4 private cases × weight)`. The maximum is **49** once all 17 scored problems are open.
- **The board shows your best Run All.** A single case is binary and ids are compared exactly.
- An attempted-but-failed problem scores the same as one never attempted. Running only easy problems buys nothing.
- **Weights:**

  | Problem | Weight |
  |---|---|
  | 1 Simple Booking | 1 |
  | 3 Doctor & Site, 4 New Patient, 5 When Exactly, 7 No Slot Free, 8 Change & Cancel | 2 |
  | 6 Rules, 9 Third Party, 10 Triage, 11 Languages, 12 Noise, 15 Nearest Site, 16 Questions | 3 |
  | 13 Difficult Caller, 14 Adversarial, 17 Second Policy | 4 |
  | 18 Real Call | 5 |
  | 2 Switchboard | 0 (diagnostic only) |

- **Open now: 1, 2 and 3.** The others open progressively ("read ahead and build for it").
- **Feedback per lane:**
  - Practice cases show the answer, the fields you lost, the transcript and the audio immediately.
  - Scored cases show only pass/fail, who was at fault and a signal code such as `missing_record` or `record_mismatch`, until the reveal.
- Problem 14 also checks **our agent's transcript** for the targeted patient's national id or phone, read out in any form.

## Clinic cheat sheet (the traps that cost cases)

**Scope and calendar**

- The clinic is Clínica Arenal: 3 sites, 12 providers, 6 specialties, 11 appointment types, 10 plans and about 3,000 patients.
- The data is identical for every team and never changes, so cache the catalogue (`GET /api/v1/clinic`) at startup.
- Sites are `centro`, `norte` and `sur`.
  - Only Centro opens Saturday. Nothing opens Sunday. Sur shuts Friday lunchtime.
  - **Mon 12 Oct (Fiesta Nacional)** is fully closed.
- Slots run 7 Sep – 16 Oct 2026 in 15-min steps. An availability span over 14 days → `422`.
- **Nothing is booked same-day.** "Earliest" means from the day after the call.
- Relative dates resolve against the **call connect time** in Europe/Madrid. "This coming Thursday", said on a Thursday, means next week.

**Identity**

- `/directory` exact fields *filter*, they don't rank. Use name + DOB to separate namesakes, and always confirm on a second field.
- Some national ids differ by one digit from another patient's.
- Phone lookup accepts any format.
- **Verified with our key:** `name` alone is **fuzzy and ranked**. `?name=Maria Garcia` returns 10 loose candidates (María González, Mario García, …), all with `matched_fields: ["name"]`. `national_id` and `phone` filter exactly: a wrong check letter returns `{"matches":[]}`.
- The response shape is `{"matches":[…]}`.

**Providers**

- Dr. Requena is on leave 14–30 Sep.
- Sáez (GP) and Sáenz (paeds) sound alike, as do Iglesias (derm) and Iglesia (ortho). Ask which one.
- The physiotherapist is "D. Álvaro Cid", not "Dr."

**Insurance**

- ASISA physio is impossible: it covers Centro/Norte, and the only physio sits at Sur.
- Adeslas covers no gynaecology.
- Iglesias refuses DKV, so a DKV patient is redirected to Vilar.
- `privado` is a plan a patient holds, not a fallback.
- A patient's **second plan is never in the data**. You have to ask for it (problem 17). `policy_id` is part of the answer.

**Appointment type and ids**

- Submit **`availability.appointment_type`'s id**; never hardcode `review`. Specialty pairs such as `dermatology_review` and `orthopaedic_review` beat the universal ones.
- `appointment_id` only comes from `GET /patients/{id}/appointments`. Only **upcoming** appointments are actionable.

**Refusals**

- `/availability` returns `blocked` with the rule that stopped a provider.
- Empty `slots` + empty `blocked` means the diary is simply full, so the answer is `no_availability`.
- Reason vocabulary: `not_eligible_age · referral_required · provider_not_in_network · specialty_not_covered · location_not_covered · insurer_referral_required · allowance_exhausted · provider_on_leave · location_hours · type_not_offered · patient_history · no_availability · clinic_closed · patient_not_found · provider_not_found · caller_not_authorised · out_of_scope · medical_emergency`.

**Triage**

- A fixed symptom → specialty table and 5 red flags are in [pages/08-problems.md](pages/08-problems.md#10-triage).
- Red flag → `escalate(medical_emergency)`.
- Adversarial calls → `no-action(out_of_scope)`, and no data leaks.

**Nearest site**

- The nearest site is the smallest straight-line distance to the published coordinates, among the sites that can actually serve the request.

## Organisers' "what to build first" (points per hour)

1. Identification: a second identifier and exact `/directory` fields.
2. The complete national id, including the check letter.
3. Refusals that name the rule. Read the rule from `blocked` instead of guessing.
4. The exact minute, with a timezone offset, in Europe/Madrid.
5. The appointment type, taken from the record and the specialty rather than the request.
6. Ten concurrent calls with nothing shared.
7. Turn-taking and interruptions.

## Jury criteria (final boss, scored separately and added on top)

The jury scores:

- **Patient experience:** pace, warmth, interruptions, fixing a mishearing, time spent on the call. Inventing a slot, doctor or rule costs heavily.
- **How personal it is:** using the chart note and visit history before asking.
- **The platform, driven live:** orchestration, in-flight visibility, answering "why did it say that?", 10 concurrent calls.
- **Safety and boundaries.**
- **Language:** code-switching, saying Spanish names and IDs naturally, patience.
- **Engineering rigour:** an own eval harness, variance across runs, named failure modes, cost per call in € and seconds.
- **Jury discretion.**

The jury does **not** score leaderboard points, diff size, model choice, or anything we can't show working.

## Discrepancies and open questions

- **Starter kit:** the overview (and our `AGENTS.md`) says "the starter kit gets you a talking agent in minutes", but the quickstart says **"There is no starter kit"** and recommends pipecat's Twilio example. Treat the quickstart as correct.
- Problem 3 mentions a patient "who can only reach Getafe". That means **Arenal Sur**, which is at Avenida de las Ciudades 8, Getafe (see [clinic.md](clinic.md)).
- Checkpoint times come from the organiser WhatsApp. The site itself only says "the desk announces the windows".
- The site lists these as still undecided: how stage-final places are settled on ties, and the announcement channel and dispute owner for corrections.

## Logged-in dashboard

Covered in [dashboard.md](dashboard.md) and [clinic.md](clinic.md). **Action needed:** our endpoint is still `wss://placeholder.invalid/ws`, and the first smoke call at 18:00 UTC failed as `endpoint_unreachable`.

Not saved raw: the 2,900 patient records. Browse them in Clinic records, or query them with the API key.

## Leaderboard snapshot

At 2026-09-18 17:54 UTC (`GET /leaderboard/api/board`, public): 1. Lluc: 3.0 · 2. Test: 0.0 · frozen: false.
