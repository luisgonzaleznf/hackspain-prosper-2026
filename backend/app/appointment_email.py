"""Appointment summaries, sent through Resend after the final outcome.

Use each patient's looked-up chart email automatically. A caller-confirmed address is
only needed when the chart has none; only call finalization can send a message.
"""

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime
from html import escape
from typing import TYPE_CHECKING

import httpx

from app import clinic, config

if TYPE_CHECKING:
    from app.session import CallSession


@dataclass
class Recipient:
    address: str
    confirmed: bool = False


def enabled() -> bool:
    return bool(
        config.APPOINTMENT_EMAILS_ENABLED
        and config.RESEND_API_KEY
        and config.RESEND_FROM_EMAIL
        and not config.EVAL_MODE
    )


def normalize_address(raw: str) -> str:
    """Validate one plain address. Spoken punctuation is resolved by the voice, never guessed."""
    if not isinstance(raw, str) or any(ord(char) < 32 or ord(char) == 127 for char in raw):
        raise ValueError("Spell one email address without control characters.")
    address = raw.replace(" ", "")
    local, separator, domain = address.rpartition("@")
    atom = r"[A-Za-z0-9!#$%&'*+/=?^_`{|}~-]+"
    label = r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?"
    if (
        not separator
        or len(address) > 254
        or len(local) > 64
        or not re.fullmatch(rf"{atom}(?:\.{atom})*", local)
        or not re.fullmatch(rf"(?:{label}\.)+[A-Za-z]{{2,63}}", domain)
    ):
        raise ValueError("That is not a complete email address. Ask the caller to spell it again.")
    return f"{local}@{domain.lower()}"


def patient_for_action(session: "CallSession", action: dict) -> str | None:
    if action["action"] == "BOOK":
        return action["patient_id"]
    if action["action"] == "RESCHEDULE":
        return session.appointments.get(action["appointment_id"], {}).get("patient_id")
    return None


def _has_appointment(session: "CallSession", patient_id: str) -> bool:
    return any(patient_for_action(session, action) == patient_id for action in session.actions)


def address_on_file(session: "CallSession", patient_id: str) -> str | None:
    """Read lookup evidence held by the backend, never an address supplied by the model."""
    try:
        return normalize_address(session.patients.get(patient_id, {}).get("email", ""))
    except ValueError:
        return None


async def set_recipient(session: "CallSession", args: dict) -> dict:
    if not session.demo_mode or not enabled():
        return {"error": "Email confirmations are unavailable. Do not promise an email."}
    if session.finished:
        return {"error": "This call has already finished."}
    patient_id = args["patient_id"]
    if patient_id not in session.patients:
        return {"error": "Find and identify this patient before capturing their email."}
    # Even an invalid correction invalidates the previous address: never send to a stale one.
    session.appointment_emails.pop(patient_id, None)
    if args["email"] == "":
        # Keep an explicit opt-out so finalization cannot fall back to the chart.
        session.appointment_emails[patient_id] = Recipient("")
        session.log("appointment_email.declined", patient_id=patient_id)
        return {"status": "declined", "note": "No email will be sent for this patient."}
    if not _has_appointment(session, patient_id):
        return {"error": "Record this patient's agreed booking or move before requesting email."}
    if address_on_file(session, patient_id):
        return {
            "status": "on_file",
            "note": "The backend will use this patient's email on file after hang-up. No address or email confirmation is needed; the supplied address was not used.",
        }
    try:
        address = normalize_address(args["email"])
    except ValueError as exc:
        return {"error": str(exc)}
    session.appointment_emails[patient_id] = Recipient(address)
    return {
        "status": "needs_confirmation",
        "email_to_read_back": address,
        "note": "Read back the full address, spelling the local part and punctuation. Wait for an explicit yes, then call confirm_appointment_email with this address. Nothing has been sent.",
    }


async def confirm_recipient(session: "CallSession", args: dict) -> dict:
    if not session.demo_mode or not enabled() or session.finished:
        return {"error": "Email confirmations are unavailable. Do not promise an email."}
    patient_id = args["patient_id"]
    if address_on_file(session, patient_id):
        return {
            "error": "This patient's email on file is selected automatically by the backend. Do not supply or confirm a replacement address."
        }
    recipient = session.appointment_emails.get(patient_id)
    if recipient:
        # A mismatching confirmation may be a correction sent to the wrong tool.
        # Fail closed instead of retaining consent to the older address.
        recipient.confirmed = False
    try:
        address = normalize_address(args["email"])
    except ValueError as exc:
        return {"error": str(exc)}
    if not recipient or recipient.address != address:
        return {
            "error": "Capture this address with set_appointment_email, read it back and wait for the caller to confirm it first."
        }
    if not _has_appointment(session, patient_id):
        return {"error": "There is no booking or move for this patient to email."}
    recipient.confirmed = True
    session.log("appointment_email.confirmed", patient_id=patient_id)
    return {
        "status": "confirmed",
        "note": "The final appointment summary will be sent after the call ends. It has not been sent yet; never claim delivery.",
    }


def message(session: "CallSession", action: dict, address: str) -> dict:
    """Build from lookup evidence and the final action, never from model-written email text."""
    patient_id = patient_for_action(session, action)
    if patient_id is None:
        raise ValueError("Only a looked-up patient's booking or move can be emailed")
    patient = session.patients[patient_id]
    when = datetime.fromisoformat(action["slot"])
    offered = session.slots[(action["provider_id"], action["location_id"], when)]
    cat = clinic.cached() or {}
    location: dict = next(
        (site for site in cat.get("locations", []) if site["id"] == action["location_id"]), {}
    )
    name = " ".join(
        patient.get(key, "") for key in ("given_name", "first_surname", "second_surname")
    ).strip()
    title = (
        "Cita reprogramada / Appointment moved"
        if action["action"] == "RESCHEDULE"
        else "Cita reservada / Appointment booked"
    )
    clinic_name = cat.get("clinic_name", "Clínica Arenal")
    fields = [
        ("Paciente / Patient", name),
        (
            "Fecha / Date",
            when.astimezone(config.TZ).strftime("%d/%m/%Y · %H:%M") + " (Europe/Madrid)",
        ),
        ("Profesional / Doctor", offered["provider_name"]),
        ("Centro / Clinic", location.get("name", action["location_id"])),
    ]
    if location.get("address"):
        fields.append(("Dirección / Address", location["address"]))
    if patient.get("registration_pending"):
        fields.append(
            (
                "Paciente nuevo / New patient",
                "Complete su registro en recepción al llegar (DNI/NIE y tarjeta del seguro). "
                "Please complete your registration at reception on arrival (ID and insurance card).",
            )
        )
    if action["action"] == "RESCHEDULE":
        previous = datetime.fromisoformat(
            session.appointments[action["appointment_id"]]["start_time"]
        )
        fields.append(
            (
                "Fecha anterior / Previous time",
                previous.astimezone(config.TZ).strftime("%d/%m/%Y · %H:%M") + " (Europe/Madrid)",
            )
        )
    disclaimer = (
        "Demo HackSpain: propuesta guardada localmente, sin modificar la agenda. "
        "Demo proposal saved locally; the clinic diary was not changed."
    ) + " No es una cita médica real. This is not a real medical appointment."
    text = (
        f"{clinic_name}\n{title}\n\n"
        + "\n".join(f"{label}: {value}" for label, value in fields)
        + f"\n\n{disclaimer}"
    )
    rows = "".join(
        f'<tr><td style="padding:12px 0;border-bottom:1px solid #e3e9e6;color:#52605a;font-size:12px">{escape(label)}<br><strong style="color:#152a22;font-size:17px">{escape(str(value))}</strong></td></tr>'
        for label, value in fields
    )
    html = f"""<!doctype html>
<html lang="es"><head><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;background:#f3f5f2;font-family:Arial,sans-serif;color:#152a22">
<table role="presentation" width="100%" cellspacing="0" cellpadding="0"><tr><td align="center" style="padding:24px 12px">
<table role="presentation" width="100%" style="max-width:520px;background:#fff;border-radius:16px" cellspacing="0" cellpadding="0"><tr><td style="padding:32px">
<p style="margin:0 0 24px;letter-spacing:2px;font-size:12px">ROSARIO · {escape(clinic_name)}</p>
<p style="color:#52715e;font-size:12px">HACKSPAIN 2026 · DEMO</p>
<h1 style="font-size:24px;line-height:1.3;margin:0 0 16px">{escape(title)}</h1>
<table role="presentation" width="100%" cellspacing="0" cellpadding="0">{rows}</table>
<p style="font-size:12px;line-height:1.6;color:#657069;margin:24px 0 0">{escape(disclaimer)}</p>
</td></tr></table></td></tr></table></body></html>"""
    return {
        "from": config.RESEND_FROM_EMAIL,
        "to": [address],
        "subject": f"{title} · {clinic_name} [Demo]",
        "text": text,
        "html": html,
    }


async def send_message(payload: dict, key: str) -> str:
    """Send one server-built message; callers persist outcomes before invoking this."""
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(
            "https://api.resend.com/emails",
            headers={"Authorization": f"Bearer {config.RESEND_API_KEY}", "Idempotency-Key": key},
            json=payload,
        )
    response.raise_for_status()
    email_id = response.json()["id"]
    if not isinstance(email_id, str) or not email_id:
        raise ValueError("Resend returned no email id")
    return email_id


async def send_for_actions(session: "CallSession", actions: list[dict]) -> list[dict]:
    """Best effort, after saving the demo outcome. Email failure never erases the proposal."""
    if not session.demo_mode or not enabled():
        return []
    results = []
    for action in actions:
        patient_id = patient_for_action(session, action)
        if patient_id is None or patient_id not in session.patients:
            continue
        recipient = session.appointment_emails.get(patient_id)
        if recipient is not None and not recipient.address:
            continue  # Caller explicitly declined email, including to their chart address.
        on_file = address_on_file(session, patient_id)
        if on_file:
            recipient = Recipient(on_file, confirmed=True)
        if not recipient or not recipient.confirmed:
            continue
        try:
            payload = message(session, action, recipient.address)
            digest = hashlib.sha256(
                json.dumps(
                    [session.call_id, action, payload], sort_keys=True, ensure_ascii=False
                ).encode()
            ).hexdigest()
            key = f"appointment/{digest}"
            if key in session.sent_appointment_emails:
                continue
            email_id = await send_message(payload, key)
            session.sent_appointment_emails.add(key)
            result = {
                "status": "accepted",
                "patient_id": patient_id,
                "action": action["action"],
                "email_id": email_id,
                "recipient_source": "patient_record" if on_file else "caller_confirmed",
            }
            session.log("appointment_email.accepted", **result)
        except Exception as exc:
            # Provider bodies/exceptions can echo addresses or credentials; log metadata only.
            result = {
                "status": "failed",
                "patient_id": patient_id,
                "action": action["action"],
                "error": type(exc).__name__,
            }
            if isinstance(exc, httpx.HTTPStatusError):
                result["http_status"] = exc.response.status_code
            session.log("appointment_email.failed", **result)
        results.append(result)
    return results
