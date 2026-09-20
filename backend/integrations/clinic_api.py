"""Local-only console view of persisted appointments; no public voice-server route."""

from datetime import datetime

from app import config
from fastapi import APIRouter

from integrations.local_store import LocalStore

router = APIRouter(prefix="/api/clinic")


@router.get("/calendar")
def calendar() -> dict:
    records = []
    for a in LocalStore().appointments(include_cancelled=True):
        records.append(
            {
                "id": a["appointment_id"],
                "appointmentId": a["appointment_id"],
                "callId": a["call_id"],
                "kind": "CANCEL" if a["status"] == "cancelled" else "BOOK",
                "recordedAt": a["updated_at"],
                "slot": a["start_time"],
                "previousSlot": None,
                "day": datetime.fromisoformat(a["start_time"])
                .astimezone(config.TZ)
                .date()
                .isoformat(),
                "patient": a["patient_name"],
                "patientId": a["patient_id"],
                "caller": None,
                "provider": a.get("provider_name", a["provider_id"]),
                "site": a["location_id"],
                "supersededBy": None,
                "practice": False,
                "persisted": True,
            }
        )
    return {"records": records}
