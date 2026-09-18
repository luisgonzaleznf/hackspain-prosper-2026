# HackSpain 2026 — Prosper track

The challenge brief for this repo. Read it before `/brainstorm`. Anything marked **OPEN** is unconfirmed; resolve it with the Prosper team before freezing `CONTRACTS.md`.

## Sponsor: Prosper AI

[Prosper AI](https://www.getprosper.ai/) builds HIPAA-compliant voice agents for healthcare admin phone work: scheduling, reminders, benefit checks, prior authorization, claims status and patient intake.

## Challenge: Prosper Voice Wars

Build a **scheduling voice agent** for healthcare that holds up under realistic call conditions:

- **Background noise** on the caller's side.
- **Confused callers**: people who ramble, contradict themselves, forget details or change their minds.

## Prizes and scoring

- There is a **leaderboard with checkpoints**.
- **Two gifts per checkpoint.**
- **€1000** for the winner at the end.

## Open questions (ask Prosper first)

- **OPEN: What and when are the checkpoints?** This is the top priority because it sets our build order.
- **OPEN: How is the leaderboard scored?** Is it an automated caller or test harness, human judges, or both? What metrics count (booking success, latency, handling of noise and confusion)?
- **OPEN: How does the evaluator reach our agent?** A phone number, a WebSocket or HTTP endpoint, or a recorded demo? If it has to call a live agent, our local-only posture needs a tunnel (e.g. ngrok) and the demo has to run live, not only as a recording.
- **OPEN: Is a voice or telephony stack required or provided?** For example Twilio, Vapi, Retell, LiveKit, Pipecat, Deepgram or ElevenLabs. Do they provide credits?
- **OPEN: What language do callers speak?** Spanish, English or both?
- **OPEN: Is there a scheduling backend to integrate with** (calendar, EHR mock or availability API), or do we bring our own?
