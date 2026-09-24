"""Appointment summaries, sent through Resend after the final outcome.

Use each patient's looked-up chart email automatically. A caller-confirmed address is
only needed when the chart has none; only call finalization can send a message. A chart
address on a reserved demo domain (example.com/.org/.net, *.test, *.example, *.invalid)
counts as no address: nothing is ever sent to it automatically.
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
        config.APPOINTMENT_EMAILS_ENABLED and config.RESEND_API_KEY and config.RESEND_FROM_EMAIL
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


_RESERVED_DOMAINS = {"example.com", "example.org", "example.net"}
_RESERVED_TLDS = {"test", "example", "invalid"}


def reserved(address: str) -> bool:
    """RFC 2606/6761 names: seeded demo charts use them so no real person is ever mailed."""
    domain = address.rpartition("@")[2].lower().rstrip(".")
    return (
        domain in _RESERVED_DOMAINS
        or any(domain.endswith("." + d) for d in _RESERVED_DOMAINS)
        or domain.rpartition(".")[2] in _RESERVED_TLDS
    )


def _chart_address(session: "CallSession", patient_id: str) -> str | None:
    try:
        return normalize_address(session.patients.get(patient_id, {}).get("email", ""))
    except ValueError:
        return None


def address_on_file(session: "CallSession", patient_id: str) -> str | None:
    """Read lookup evidence held by the backend, never an address supplied by the model."""
    address = _chart_address(session, patient_id)
    return None if address is None or reserved(address) else address


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
        "Cita reprogramada (demo) / Demo reschedule"
        if action["action"] == "RESCHEDULE"
        else "Cita reservada (demo) / Demo booking"
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
    text = f"{title}\n\n" + "\n".join(f"{label}: {value}" for label, value in fields)
    rows = "".join(
        f'<tr><td style="padding:14px 0;border-bottom:1px solid #2d1012;color:#a86d70;font-family:Plain,Helvetica,Arial,sans-serif;font-size:12px;font-weight:300;letter-spacing:0.5px;text-transform:uppercase">{escape(label)}<br><strong style="color:#fefefe;font-size:17px;font-weight:400;letter-spacing:0;text-transform:none">{escape(str(value))}</strong></td></tr>'
        for label, value in fields
    )
    html = f"""<!doctype html>
<html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<style>
@font-face {{ font-family:Plain;src:url('https://rosario.fyi/fonts/plain/plain-light.woff2') format('woff2');font-weight:300;font-style:normal }}
@font-face {{ font-family:Plain;src:url('https://rosario.fyi/fonts/plain/plain-regular.woff2') format('woff2');font-weight:400;font-style:normal }}
</style></head>
<body style="margin:0;background:#2d1012;font-family:Plain,Helvetica,Arial,sans-serif;font-weight:300;color:#fefefe">
<table role="presentation" width="100%" cellspacing="0" cellpadding="0"><tr><td align="center" style="padding:32px 12px">
<table role="presentation" width="100%" style="max-width:520px;background:#14090a;border:1px solid #2d1012;border-radius:35px" cellspacing="0" cellpadding="0"><tr><td style="padding:32px">
<h1 style="font-family:Plain,Helvetica,Arial,sans-serif;font-size:28px;line-height:1.3;margin:0 0 16px;font-weight:300;letter-spacing:-0.56px">{escape(title)}</h1>
<table role="presentation" width="100%" cellspacing="0" cellpadding="0">{rows}</table>
</td></tr></table></td></tr></table></body></html>"""
    return {
        "from": config.RESEND_FROM_EMAIL,
        "to": [address],
        "subject": f"{title} · {clinic_name}",
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
            if (chart := _chart_address(session, patient_id)) and reserved(chart):
                session.log(
                    "appointment_email.skipped",
                    patient_id=patient_id,
                    action=action["action"],
                    reason="reserved_domain",
                )
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
