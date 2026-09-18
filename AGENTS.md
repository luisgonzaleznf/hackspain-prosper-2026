# HackSpain — Prosper Track 2026

Repo: https://github.com/luisgonzaleznf/hackspain-prosper-2026-private
Public mirror: https://github.com/luisgonzaleznf/hackspain-prosper-2026 — exists only for the HackSpain platform link; NEVER commit or push to it unless explicitly told.

## What we are building

A voice AI agent that answers inbound scheduling calls for a clinic the way a receptionist would: identify who is calling and what they need, look them up in clinic records, find real availability, then book, move, or cancel — or decline correctly when the clinic cannot do it, the caller needs a doctor, or the rules say no.

The voice model is one component of a system, not the system. The work lives around it: real lookups, real availability, checks before anything is written, state that survives a caller changing their mind, and enough visibility to explain any utterance after the fact.

## Timeline

Fri 18 – Sun 20 Sep 2026.

1. Stand up a callable endpoint (starter kit gives a talking agent in minutes).
2. Build and rehearse: self-dial freely against the published practice cases, answers included.
3. Run for score: organizers call with every case; results go to the leaderboard.
4. Two checkpoint freezes over the weekend — being early pays.
5. Sunday final boss: the jury calls the agent and reviews everything built around it.

## The 18 cases

One persona per case, each isolating a single front-desk difficulty on top of ordinary booking:

- Volume: one straightforward booking; ten bookings in one call.
- Identity: a caller unknown to the records; a caller matching four people.
- Constraints: a specific doctor; a specific site; "the soonest".
- Vague times: "next Thursday", "first thing Monday" — resolve to concrete slots.
- Refusals: requests the clinic's rules forbid — decline and state the right reason.
- A full diary with nothing free.
- Changes and cancellations.
- Third parties: a parent for a child, a daughter for her father.
- Medical escalation: route to a doctor, not a calendar.
- Languages: non-English callers, including the other languages of Spain.
- Noise: a terrible line; a caller who interrupts, corrects, and changes their mind; someone talking the agent into something it should not do.

## Scoring

**Leaderboard — automatic and literal.** After each call the agent reports what it did; the report either matches what the case accepts or the case fails. Binary, no partial credit. A correct refusal scores only if reported: report every action after every call — silence always fails.

**Jury — final boss, human.** Judges what the leaderboard ignores: how the call sounds, interruption handling, whether the caller feels known, call orchestration, live visibility, post-call insight, safety, language coverage, and demonstrated proof that the agent works.

## Build invariants

- Look up real records and real availability before offering anything.
- Verify identity before acting on records; check before any write (book, move, cancel).
- Keep call state durable across mid-call changes of mind.
- Log every decision so any agent utterance can be explained afterwards.
- Prefer declining with the correct stated reason over making a wrong booking.
