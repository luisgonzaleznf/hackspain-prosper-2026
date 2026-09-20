# HackSpain — Prosper 2026

Voice AI agent for clinic scheduling calls.

Private: [hackspain-prosper-2026-private](https://github.com/luisgonzaleznf/hackspain-prosper-2026-private)  
Public mirror (platform link only): [hackspain-prosper-2026](https://github.com/luisgonzaleznf/hackspain-prosper-2026)

## Layout

| | |
|---|---|
| `leaderboard/` | Scoring / case-report side of the track |
| `backend/` | Bridge to Prosper (records, availability, bookings). Room for thin extras if we need them. Call artifacts (logs, audio) live here for the UI to read. |
| `frontend/` | Landing + live dashboard (calendar and whatever else we manage to ship) |

## Docs

- [`AGENTS.md`](./AGENTS.md) — what we're building
- [Demo email setup](./backend/docs/appointment-email.md) — Resend, custom sender domain,
  confirmed appointment summaries and customer welcome emails for Twilio/browser calls
