"""Twilio inbound webhook for the standalone ROSARIO media stream."""

import os
from urllib.parse import parse_qs
from xml.etree.ElementTree import Element, SubElement, tostring

from fastapi import APIRouter, HTTPException, Request, Response

router = APIRouter()
ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "")
PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER", "")


@router.post("/twiml")
@router.post("/integrations/twilio/voice")
async def incoming_call(request: Request) -> Response:
    fields = parse_qs((await request.body()).decode())
    if not fields.get("CallSid") or not fields.get("From"):
        raise HTTPException(400, "CallSid and From are required")
    if ACCOUNT_SID and fields.get("AccountSid") != [ACCOUNT_SID]:
        raise HTTPException(400, "Unexpected Twilio account")
    if PHONE_NUMBER and fields.get("To") != [PHONE_NUMBER]:
        raise HTTPException(400, "Unexpected destination")
    caller = fields["From"][0]
    response = Element("Response")
    stream = SubElement(
        SubElement(response, "Connect"),
        "Stream",
        url=str(request.url_for("twilio_ws").replace(scheme="wss")),
    )
    SubElement(stream, "Parameter", name="from_number", value=caller)
    if fields.get("To"):
        SubElement(stream, "Parameter", name="to_number", value=fields["To"][0])
    SubElement(response, "Hangup")
    return Response(tostring(response, encoding="unicode"), media_type="application/xml")
