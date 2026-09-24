# Twilio inbound calls

Number: **+1 571-713-5999**. The caller dials normally and talks to the existing
GPT-Live voice layer and clinic tools.

From `backend/`:

```sh
make serve VOICE=gptlive PORT=18761
# Separate terminal; use a configured static ngrok domain when available:
PORT=18761 NGROK_DOMAIN=your-domain.ngrok-free.app make tunnel
# Or an immediate temporary tunnel (URL changes when restarted):
cloudflared tunnel --url http://127.0.0.1:18761
```

In Twilio, configure the number's **A call comes in** as **Webhook / HTTP POST**:
`https://YOUR-TUNNEL/integrations/twilio/voice`.

The webhook emits `<Connect><Stream>` pointing to `/integrations/twilio/ws` and
passes `from_number` as a custom parameter. The stream reuses the server's Twilio
serializer and voice pipeline.

The root `.env` supplies `TWILIO_ACCOUNT_SID` and `OPENAI_API_KEY`. No Twilio
Auth Token is needed to serve TwiML or handle media. Keep the server and tunnel
running while receiving calls. Check `/health` for `voice: gptlive` and
`catalogue_loaded: true`.

Calls read and write the clinic database, `backend/data/clinic.sqlite3` (gitignored;
`make seed` builds it with synthetic patients and a realistic diary). The directory,
diaries and availability all come from it (`local_clinic.py`, `local_store.py`).
Registrations, bookings, moves and cancellations persist immediately after caller
confirmation. Future calls see those records, and bookings block overlapping slots;
a cancellation frees its slot. `LOCAL_CLINIC_DB` can override the database path; voice
and console must use the same database. Re-seeding resets the diary.

The local console's `/calendar` shows a window of the diary, with the appointments
calls made or changed linked to their call. Start it with `make console CONSOLE_PORT=8001`
after building the frontend (`cd ../frontend && pnpm build`). For Vite development,
set `ROSARIO_CLINIC_API=http://127.0.0.1:8001`. The calendar API is only on the local
console server, never on the public phone server.

Decisions and saved writes are also logged in
`backend/logs/calls/<Twilio CallSid>.jsonl`. Audio is stored in `backend/logs/audio/`.

Optional [Resend emails](../docs/appointment-email.md) send a clearly labelled demo
summary after hang-up to the identified patient's email on file, read directly by the backend.
Only if no usable email is on file does the caller need to spell and confirm an address. Callers can
also request a local customer account and welcome email. Set `APPOINTMENT_EMAILS_ENABLED=1`,
`RESEND_API_KEY` and `RESEND_FROM_EMAIL` in the ignored `.env`, then restart this same
server. `TwilioCallSession` enables the human-only tools and finalizes them locally.
Chart addresses on reserved demo domains (example.com, *.test) are never emailed.
No Twilio webhook changes are needed.

This demo inherits the existing public WebSocket setup. Account/destination checks
catch misconfiguration but do not authenticate Twilio signatures. Keep this a
short-lived demo tunnel: anyone with its URL can invoke the model and, when enabled,
email sending, incurring usage. Call traces and recordings can contain volunteered
names and email addresses; keep the tunnel and its review URLs within the rehearsal.
