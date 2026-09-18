# HackSpain 2026 — Prosper track

The challenge brief for this repo. Read it before `/brainstorm`. Anything marked **OPEN** is unconfirmed; resolve it with the Prosper team before freezing `CONTRACTS.md`.

Sources: the [track page](https://hackspain.app/tracks/prosper-ai) (log in first) and our own notes. For anything done through the HackSpain CLI (team, repo, feed, submission), use the `/hackspain` skill.

## Where we stand

- **Team:** `refugia2`, with 4 members. We're registered in the `prosper-ai` track.
- **Dates:** Friday 18 to Sunday 20 September 2026, in Madrid.
- **Repos:** we build in `hackspain-prosper-2026-private`. The public mirror `hackspain-prosper-2026` is the one to link with `hackspain team repo`, because the platform needs a public repo.

## Sponsor: Prosper AI

[Prosper AI](https://www.getprosper.ai/) builds HIPAA-compliant voice agents for healthcare admin phone work: scheduling, reminders, benefit checks, prior authorization, claims status and patient intake.

## What we build

We build an **inbound voice agent that answers a clinic's scheduling calls**, the way a receptionist would. It:

1. Answers the call.
2. Works out who is calling and what they need.
3. Looks the caller up in the clinic's records.
4. Finds real availability.
5. Books, moves or cancels the appointment.

Some calls must **not** end in a booking: the clinic can't do it, the caller needs a doctor now, or the rules forbid it. Spotting those counts as much as booking well.

The voice model is only one part of the system. Prosper says the strong teams build these around it:

- Real lookups and real availability.
- Checks before anything is written.
- State that survives a caller changing their mind.
- Enough visibility to explain why the agent said what it said.

## How the weekend runs

1. **Set up.** Register the team, get our key and stand up an **endpoint they can call**. A starter kit gets a talking agent running in minutes.
2. **Rehearse.** Call our own agent as often as we like against the published practice cases, which come with answers.
3. **Run for score.** When we're ready, they call our agent with every problem, check what it did and put the points on the leaderboard.
4. **Checkpoints.** The board freezes twice over the weekend and prizes go to whoever is leading at that moment, so scoring early pays.
5. **Sunday: the final boss.** The jury calls our agent themselves and we show them what we built.

## The 18 problems

Each problem has its own caller persona and tests one thing that makes a real front desk hard, on top of the same ordinary booking:

- A simple booking, and ten bookings at the same time (concurrency).
- A caller who isn't in the records yet, and a caller who matches four patients.
- A request for a specific doctor, a specific site, or "the soonest".
- Vague times ("next Thursday", "first thing Monday") that must resolve to a concrete slot.
- Requests the clinic's rules forbid. The agent must refuse them and give the right reason.
- A fully booked calendar with nothing free.
- Changing and cancelling appointments.
- Calls on someone else's behalf: a parent for a child, a daughter for her father.
- A caller who needs a doctor, not an appointment (triage and escalation).
- Callers who don't speak English, including other languages of Spain (Spanish, Catalan, Basque, Galician).
- A terrible phone line, a caller who interrupts, corrects and changes their mind, and a caller trying to talk the agent into something it shouldn't do.

## Scoring (two parts, added together)

1. **Leaderboard: automatic and strictly literal.** After each call, our agent reports what it did. The case passes only if that report matches what the case accepts. There is no partial credit and no points for a nice conversation. A correct refusal still has to be reported, because saying nothing is always wrong.
2. **Jury (the final boss): everything the leaderboard ignores.**
   - **The call itself,** judged as a real caller would: how it sounds, how it handles interruptions, and whether the clinic seems to know who is calling.
   - **What we built around it:** how a call is orchestrated, what we can see while it's happening, what we can learn from it afterwards, and whether we can show it working.
   - **Also counted:** safety, language handling, and how we know our own agent works (evals).

## Prizes

- Two gifts per checkpoint.
- **€1000** at the end.

## What this changes in the kit's posture

- **We need a live endpoint, not just a local app.** The scorer and the jury call our agent, so it must be reachable from the internet all weekend, either through a tunnel (e.g. ngrok or cloudflared) or a deploy. The rule "local only, recorded demo is the deliverable" in `CLAUDE.md` does not apply here. A recording is still useful for the submission, but the live agent is what gets scored.
- **The per-call outcome report is the key contract.** It decides every leaderboard point, so freeze its exact shape in `CONTRACTS.md` first, as soon as the starter kit reveals it.
- **Observability is scored.** A live view of each call and a way to review it afterwards are features in their own right, not polish.
- **Evals are cheap to set up.** The practice cases come with answers, so run them all automatically and track our pass rate before each scored run.

## Open questions (ask Prosper first)

- **OPEN: When exactly are the two checkpoints?** This sets our build order, since leading early pays.
- **OPEN: Where do we get the key and the starter kit?** And what voice or telephony stack does the kit use (its own, Twilio, Vapi, Retell, LiveKit, Pipecat…)? Do they give credits?
- **OPEN: What is the exact format of the per-call outcome report,** and how does it reach them?
- **OPEN: What does "the clinic's records and availability" mean?** Is it an API they host, or data we load ourselves?
- **OPEN: How many scored runs are allowed?** Is it unlimited, rate-limited, or does only the last or best run count?
- **OPEN: Which languages are tested,** and which of the languages of Spain?
