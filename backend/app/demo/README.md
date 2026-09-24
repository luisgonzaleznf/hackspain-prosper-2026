# Browser GPT-Live demo

This demo uses the same GPT-Live voice and persistent local patient/calendar tools
as Twilio. It bypasses the telephone network. AI API usage still applies; there are
no Twilio call charges. Confirmed changes are saved to the same local SQLite database.

Start the backend from `backend/`:

```sh
make roleplay-demo PORT=18762
```

Build and serve the frontend in another terminal:

```sh
cd frontend
pnpm build
ROSARIO_DEMO_API=http://127.0.0.1:18762 ROSARIO_CLINIC_API=http://127.0.0.1:8001 pnpm exec vite preview --host 127.0.0.1 --port 4180
```

Open <http://127.0.0.1:4180/demo/>, choose a scenario, press the microphone orb,
and allow microphone access. The first scenario registers a new patient by name only and books
their first visit. On subsequent calls that profile already exists (name + scenario phone).
Stop with the orb; Review call opens the recording and trace.

The root `.env` must provide `OPENAI_API_KEY`. Build the clinic database first with `make seed`.
Calls, transcripts, recordings and the calendar use the local console when
`ROSARIO_CLINIC_API` is set (override calls separately with `ROSARIO_CALLS_API`).
The console needs `make console CONSOLE_PORT=8001` in `backend/`.
Both backend processes must use the same `LOCAL_CLINIC_DB` if overriding the default.
The optional Resend email/account flow remains available when configured. Appointment
confirmations use the identified patient's email on file (never a reserved demo domain);
see [email setup](../../docs/appointment-email.md). Rehearsals change the diary for good:
re-seed to reset it. The cancellation card reads Ignacio's upcoming appointment from it.

Every rehearsal saves:

- `logs/calls/<call_id>.jsonl`: transcript, exact tool inputs/results, voice events,
  staged actions, recording status, and call end.
- `logs/audio/<call_id>.wav`: 24 kHz stereo, caller left and agent right.
- `logs/audio/<call_id>.timing.json`: audio frame timing.
- `logs/demo/actions.jsonl`: completed and failed calls, including calls with no action.

`/demo/review.html?call=<call_id>` plays the recording and shows the transcript and
expandable tool details. The full JSONL is downloadable there. Audio finalizes after
hang-up; a live review can be refreshed after the call ends. Recordings and the local
history survive a server restart; the live in-memory session snapshot does not.

These are synthetic clinic records. The role cards are starting points, not scripts
the agent sees. Audio, transcripts, and identifiers stay in this local/private setup.
For a failure review, share the call ID and what you expected to happen.
