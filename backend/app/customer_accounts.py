"""Local customer enrollment for human demos; never a Prosper patient registration."""

import asyncio
import hashlib
import sqlite3
from contextlib import closing
from dataclasses import dataclass
from datetime import datetime
from html import escape
from typing import TYPE_CHECKING
from uuid import uuid4

import httpx

from app import appointment_email, config

if TYPE_CHECKING:
    from app.session import CallSession


@dataclass
class AccountRequest:
    name: str
    email: str
    confirmed: bool = False


async def prepare(session: "CallSession", args: dict) -> dict:
    if not session.demo_mode or not appointment_email.enabled() or session.finished:
        return {"error": "Customer account creation is available only in a configured human demo."}
    session.customer_account = None
    if args["email"] == "":
        return {
            "status": "withdrawn",
            "note": "No customer account or welcome email will be created.",
        }
    if not isinstance(args["name"], str):
        return {"error": "Ask for the caller's name."}
    name = args["name"].strip()
    if not name or len(name) > 120 or any(ord(char) < 32 for char in name):
        return {"error": "Ask for the caller's name (up to 120 characters)."}
    try:
        email = appointment_email.normalize_address(args["email"])
    except ValueError as exc:
        return {"error": str(exc)}
    session.customer_account = AccountRequest(name=name, email=email)
    return {
        "status": "needs_confirmation",
        "name_to_read_back": name,
        "email_to_read_back": email,
        "note": "Read back the name and spell the complete email. Ask whether to create the demo customer account and send its welcome email. Wait for an explicit yes before confirm_customer_account. Nothing has been saved or sent yet.",
    }


async def confirm(session: "CallSession", args: dict) -> dict:
    if not session.demo_mode or not appointment_email.enabled() or session.finished:
        return {"error": "Customer account creation is unavailable."}
    request = session.customer_account
    if request:
        request.confirmed = False
    try:
        email = appointment_email.normalize_address(args["email"])
    except ValueError as exc:
        return {"error": str(exc)}
    if request is None or request.email != email:
        return {
            "error": "Use prepare_customer_account with the corrected details, read them back, and wait for an explicit yes first."
        }
    request.confirmed = True
    session.log("customer_account.confirmed")
    return {
        "status": "confirmed",
        "note": "The customer record will be saved in the local demo database and the welcome email sent after hang-up. Do not claim either has already happened. No clinic appointment is booked by creating this account.",
    }


def _save(request: AccountRequest) -> dict:
    config.CUSTOMER_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(config.CUSTOMER_DB_PATH, timeout=5)) as db, db:
        db.row_factory = sqlite3.Row
        db.execute("""CREATE TABLE IF NOT EXISTS customers (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE COLLATE NOCASE,
            created_at TEXT NOT NULL
        )""")
        inserted = (
            db.execute(
                "INSERT INTO customers (id, name, email, created_at) VALUES (?, ?, ?, ?) "
                "ON CONFLICT(email) DO NOTHING",
                (str(uuid4()), request.name, request.email, datetime.now(config.TZ).isoformat()),
            ).rowcount
            == 1
        )
        row = db.execute("SELECT * FROM customers WHERE email = ?", (request.email,)).fetchone()
        return dict(row) | {"created": inserted}


def _message(account: dict, address: str) -> dict:
    name = account["name"]
    account_id = account["id"]
    text = (
        f"Hola {name},\n\nTu cuenta de cliente en la demo de Rosario está lista.\n"
        f"Your Rosario demo customer account is ready.\n\n"
        f"Referencia / Reference: {account_id}\n\n"
        "Hemos guardado tu nombre y correo en la base de datos local de la demo. "
        "Your name and email have been saved in the local demo database.\n\n"
        "No se ha reservado ninguna cita médica. No medical appointment has been booked."
    )
    html = f"""<!doctype html><html lang="es"><head><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;background:#f3f5f2;font-family:Arial,sans-serif;color:#152a22;padding:24px 12px">
<div style="max-width:480px;margin:auto;background:white;border-radius:16px;padding:28px">
<p style="letter-spacing:2px;font-size:12px">ROSARIO · DEMO</p>
<h1 style="font-size:25px">Tu cuenta está lista</h1>
<p>Hola {escape(name)},</p><p>Hemos guardado tu nombre y correo en la base de datos local de la demo.</p>
<p>Your Rosario demo customer account is ready. Your name and email have been saved.</p>
<p style="font-size:12px;overflow-wrap:anywhere">Referencia / Reference: {escape(account_id)}</p>
<p style="font-size:12px;color:#657069">No se ha reservado ninguna cita médica. No medical appointment has been booked.</p>
</div></body></html>"""
    return {
        "from": config.RESEND_FROM_EMAIL,
        "to": [address],
        "subject": "Tu cuenta de Rosario está lista / Your account is ready [Demo]",
        "text": text,
        "html": html,
    }


async def finalize(session: "CallSession") -> dict | None:
    request = session.customer_account
    if not session.demo_mode or request is None or not request.confirmed:
        return None
    result: dict
    try:
        account = await asyncio.to_thread(_save, request)
    except Exception as exc:
        result = {"status": "failed", "error": type(exc).__name__, "email_status": "not_sent"}
        session.log("customer_account.failed", **result)
        return result
    result = {
        "status": "created" if account["created"] else "existing",
        "account_id": account["id"],
        "email_status": "not_sent",
    }
    session.log("customer_account.persisted", **result)
    try:
        if not appointment_email.enabled():
            raise ValueError("Email is no longer configured")
        payload = _message(account, request.email)
        digest = hashlib.sha256(
            f"{session.call_id}:{account['id']}:{request.email}".encode()
        ).hexdigest()
        email_id = await appointment_email.send_message(payload, f"customer/{digest}")
        result.update(email_status="accepted", email_id=email_id)
        session.log("customer_email.accepted", **result)
    except Exception as exc:
        result.update(email_status="failed", error=type(exc).__name__)
        if isinstance(exc, httpx.HTTPStatusError):
            result["http_status"] = exc.response.status_code
        session.log("customer_email.failed", **result)
    return result


INSTRUCTIONS = """\
HUMAN DEMO CUSTOMER ACCOUNTS
In this human demo, a caller who asks to create an account, sign up, register as a new customer,
or receive a welcome email can create a LOCAL DEMO CUSTOMER record with only their name and
email. This is separate from clinic patient registration (record_registration, for a patient who
wants an appointment) and creates no medical appointment. For this request, do not look the
person up in the clinic, ask for DNI, birth date, phone or insurer, or use
record_registration/record_no_action.
Ask for their name and spelled email, one question at a time, reusing details already given.
Call prepare_customer_account, read back the returned name and spell the entire email address,
and ask whether to create the demo account and send its welcome email. Wait for a clear yes in
a later turn, then call confirm_customer_account with that exact email. For a correction,
prepare_customer_account immediately resets confirmation: read back again and wait for a new
yes. Pass email="" to prepare_customer_account if they withdraw the account request.
After confirmation, explain the customer record will be saved and the welcome email sent when
this call ends, and let them hang up. Never claim it is already saved or delivered. This account
does not add a patient to Prosper's clinic records or make them eligible for an appointment.
"""
