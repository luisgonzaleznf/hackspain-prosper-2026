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
serializer and voice pipeline. `/ws` remains the scored Prosper endpoint.

The root `.env` supplies `TWILIO_ACCOUNT_SID`, `OPENAI_API_KEY` and `PLATFORM_API_KEY`. No Twilio
Auth Token is needed to serve TwiML or handle media. Keep the server and tunnel
running while receiving calls. Check `/health` for `voice: gptlive` and
`catalogue_loaded: true`.

Calls use the real synthetic clinic directory and availability. Outcomes are
stored in `backend/logs/calls/<Twilio CallSid>.jsonl`; they are **demo actions**, not
persisted appointments: Twilio call IDs aren't registered with Prosper's scorer.
Audio is stored in `backend/logs/audio/`, as with the existing voice server.

Optional [Resend emails](../docs/appointment-email.md) send a clearly labelled demo
summary after hang-up when the caller spells and confirms an address. Callers can
also request a local customer account and welcome email. Set `APPOINTMENT_EMAILS_ENABLED=1`,
`RESEND_API_KEY` and `RESEND_FROM_EMAIL` in the ignored `.env`, then restart this same
server. `TwilioCallSession` enables the human-only tools and finalizes them locally;
the scored `/ws` endpoint never sends email. No Twilio webhook changes are needed.

This demo inherits the existing public WebSocket setup. Account/destination checks
catch misconfiguration but do not authenticate Twilio signatures. Keep this a
short-lived demo tunnel: anyone with its URL can invoke the model and, when enabled,
email sending, incurring usage. Call traces and recordings can contain volunteered
names and email addresses; keep the tunnel and its review URLs within the rehearsal.
