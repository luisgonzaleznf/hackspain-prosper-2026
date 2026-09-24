"""Inbound PSTN calls: the TwiML webhook, and the session that serves them."""

import os
from dataclasses import dataclass
from urllib.parse import parse_qs
from xml.etree.ElementTree import Element, SubElement, tostring

from fastapi import APIRouter, HTTPException, Request, Response

from integrations.local_session import LocalCallSession

router = APIRouter(prefix="/integrations/twilio")
PHONE_NUMBER = "+15717135999"
ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "")


@router.post("/voice")
async def incoming_call(request: Request) -> Response:
    """Twilio posts caller details here before opening the bidirectional stream."""
    fields = parse_qs((await request.body()).decode())
    if not ACCOUNT_SID:
        raise HTTPException(503, "TWILIO_ACCOUNT_SID is not configured")
    if fields.get("AccountSid") != [ACCOUNT_SID] or fields.get("To") != [PHONE_NUMBER]:
        raise HTTPException(400, "Unexpected Twilio account or destination")
    if not fields.get("CallSid") or not fields.get("From"):
        raise HTTPException(400, "CallSid and From are required")
    response = Element("Response")
    stream = SubElement(
        SubElement(response, "Connect"),
        "Stream",
        url=str(request.url_for("twilio_ws").replace(scheme="wss")),
    )
    # Native Twilio start events omit caller ID. Pipecat reads this custom parameter.
    SubElement(stream, "Parameter", name="from_number", value=fields["From"][0])
    SubElement(stream, "Parameter", name="to_number", value=PHONE_NUMBER)
    SubElement(response, "Hangup")
    return Response(tostring(response, encoding="unicode"), media_type="application/xml")


@dataclass
class TwilioCallSession(LocalCallSession):
    """Clinic database reads, with confirmed patient/calendar writes saved as they happen."""

    demo_mode: bool = True

    async def finish(self) -> list[dict]:
        return await self.finish_demo(source="twilio")
