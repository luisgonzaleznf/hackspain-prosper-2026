# Resend emails for the public demo

After a caller agrees to a booking or move, the backend automatically selects the
identified patient's email from the record returned by the clinic lookup. A new patient
registered by name in this call has no email on file. GPT-Live does not supply or recall the recipient. The booking
tool returns `appointment_email.status=on_file` so the agent can explain that confirmation
will go to the address on file without asking for it again. If no usable address is on
file, the status is `needs_address`: the caller spells an address, the agent reads it back,
and waits for an explicit yes before confirming it. At hang-up, Resend receives one message per final
appointment, with the patient, doctor, date/time in Europe/Madrid, site and address.
Moves include the previous time. HTML and plain text are supplied.

All clinic data in this project is synthetic. The email has a visible **Demo** label:
browser/Twilio outcomes are saved locally and do not change the clinic diary. These are
not real medical appointments. The scored `/ws` endpoint never offers or sends email,
even when the feature is enabled for human demo calls in the same server.

## Configure

Add these to the ignored repo-root `.env` used by `backend/Makefile`. With direct
`uv run` commands from `backend/`, use the same exported variables or `backend/.env`:

```dotenv
APPOINTMENT_EMAILS_ENABLED=1
RESEND_API_KEY=your-secret-key
RESEND_FROM_EMAIL="Rosario <citas@rosario.fyi>"
CUSTOMER_DB_PATH=logs/demo/customers.sqlite3
```

Restart the server after configuring it. The feature is disabled by default; missing
credentials or sender also disable it. When
disabled, the added prompts, tool schemas and customer-account scenario are absent.

The example uses the team's `rosario.fyi` sender; the API key must belong to the
Resend account that verified that domain. Otherwise use a domain you own and verify
its DNS records in Resend. The `resend.dev` test sender
only reaches the account owner's address, so it cannot serve arbitrary judges.
Once a domain is verified, its sending address does not need a separate mailbox.
Only server configuration contains the API key. No DNS changes or credentials are
part of this repository.

- [Verify a Resend domain](https://resend.com/docs/dashboard/domains/introduction)
- [Test sender restrictions](https://resend.com/docs/knowledge-base/403-error-resend-dev-domain)
- [Sending API](https://resend.com/docs/api-reference/emails/send-email)
- [Idempotency keys](https://resend.com/docs/dashboard/emails/idempotency-keys)

## Twilio and browser integration

The existing [Twilio integration](../integrations/README.md) starts a
`TwilioCallSession`, which enables human demo mode automatically. GPT-Live receives
the shared prompt and session-specific tools through `register_pipecat_tools`.
Its existing hang-up path calls `session.finish()`, which now delegates to
`finish_demo(source="twilio")`. No carrier setup changes are needed.

The browser demo starts `CallSession` with `demo_mode=True`, uses
`tools_for_session(session)` for its Codex voice, and calls this after disconnect:

```python
email_results = await session.finish_demo()
```

This saves the final proposals in the call JSONL, sends the requested emails and logs
`call_ended`. Repeated finalization is a no-op. Audio and normal call artifacts are still
saved by the existing handlers.

Outside human demo mode the tools and prompt exclude both email and customer enrollment,
and their handlers also reject direct invocation.

## Customer welcome emails

A caller can ask to create a demo customer account, or choose **Create your customer
account** in the browser. Rosario asks for a name and spelled email, reads both back,
then waits for explicit consent to save the record and send a welcome email.
Corrections reset confirmation; withdrawing the request saves and sends nothing.

At hang-up the customer is committed to SQLite **before** contacting Resend. An
existing email reuses its customer record without overwriting the saved name. A
database failure prevents the welcome email; an email failure leaves the saved
record intact and appears in the call trace and browser receipt. This creates no
login credentials, clinic patient record, or appointment eligibility.

The default database lives in ignored `backend/logs/demo/customers.sqlite3` when
running from `backend/`. Keep any custom database location private as well.

## Rehearse

1. Enable the feature and start the [Twilio server](../integrations/README.md) with
   `make serve VOICE=gptlive PORT=18761` from `backend/`, or the browser runner with
   `uv run python -m app.demo.bot --host 127.0.0.1 --port 7860` and open `/demo/`.
2. Use a synthetic patient on file and agree to a real returned slot.
3. With your own demo inbox saved on the patient profile, hear that confirmation will
   go to the email on file. There is no second email dictation or confirmation.
4. With no usable email on file, accept email, spell your address and confirm the read-back.
   Corrections to this fallback address need a fresh confirmation. To decline either path,
   say you do not want email. The appointment remains recorded either way.
5. Hang up and check the inbox. Only the final settled booking or move is emailed.

From `backend/`, explicitly send a rehearsal message to your own inbox with live clinic reads:

```bash
uv run python -m scripts.smoke_appointment_email --to you@example.org
uv run python -m scripts.smoke_appointment_email --to you@example.org --move --national-id SYNTHETIC_DNI
```

The second command needs a synthetic patient with an upcoming appointment and a later
eligible slot. This smoke command never calls the scorer or starts a public endpoint.
Its traces stay in ignored `logs/email-smoke/`. Phone-call transcripts and tool events
include the dictated address in the normal private call logs; use only volunteered
demo inboxes and synthetic clinic details. The current public demo's trace/audio URLs
have no login, and a live endpoint can incur model and email usage. Limit tunnel
exposure to the supervised rehearsal and keep these artifacts out of Git.

## Delivery evidence and failure behavior

`appointment_email.confirmed` records confirmation of a fallback address.
`appointment_email.accepted` records the Resend email ID, patient ID, action and
`recipient_source` (`patient_record` or `caller_confirmed`). It means the provider accepted the send; check
Resend's email dashboard and the phone inbox for actual delivery. `appointment_email.failed`
records the error class and HTTP status without logging provider bodies or credentials.

The sender reads each patient's own email on file at finalization, even if the model supplied
a different address. For patients without a usable address on file, corrections invalidate
the fallback address, including incomplete/invalid corrections. An explicit withdrawal
suppresses both paths. Unconfirmed fallback addresses, cancellations, registrations without
a booking, and refusals receive no appointment email. Customer enrollment has its own consent and welcome
message. Content comes from lookup evidence and the final staged action, not
free-form model text. Resend idempotency keys and per-session tracking suppress repeated
sends. A provider error never erases the appointment; there is no background retry queue.

Offline regression checks:

```bash
uv run pytest tests/test_appointment_email.py tests/test_customer_accounts.py tests/test_twilio_integration.py
```
