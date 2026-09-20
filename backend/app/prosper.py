"""Clinic client backed by the local writable SQLite snapshot."""

from typing import Any

from app import database

# /submit/<route> for each action verb the scorer records.
SUBMIT_ROUTES = {
    "REGISTER": "register",
    "BOOK": "book",
    "RESCHEDULE": "reschedule",
    "CANCEL": "cancel",
    "NO_ACTION": "no-action",
    "ESCALATE": "escalate",
}


class ProsperError(Exception):
    """A non-2xx answer from a read route, carrying the server's detail for the model."""

    def __init__(self, status: int, detail: Any):
        super().__init__(f"{status}: {detail}")
        self.status = status
        self.detail = detail


class ProsperClient:
    async def clinic(self) -> dict:
        return database.catalogue()


    async def directory(
        self,
        *,
        name: str | None = None,
        national_id: str | None = None,
        phone: str | None = None,
        date_of_birth: str | None = None,
    ) -> list[dict]:
        return database.directory(
            **{
                key: value
                for key, value in {
                    "name": name,
                    "national_id": national_id,
                    "phone": phone,
                    "date_of_birth": date_of_birth,
                }.items()
                if value
            }
        )

    async def availability(
        self,
        date_from: str,
        date_to: str,
        *,
        specialty_id: str | None = None,
        provider_id: str | None = None,
        location_id: str | None = None,
        patient_id: str | None = None,
        insurers: list[str] | None = None,
    ) -> dict:
        try:
            return database.availability(
                date_from,
                date_to,
                specialty_id=specialty_id,
                provider_id=provider_id,
                location_id=location_id,
                patient_id=patient_id,
                insurers=insurers,
            )
        except ValueError as error:
            raise ProsperError(422, str(error)) from error

    async def appointments(self, patient_id: str, when: str = "upcoming") -> list[dict]:
        return database.patient_appointments(patient_id, when)

    async def submit(self, action: dict) -> tuple[int, Any]:
        call_id = action["call_id"]
        return database.apply_action(call_id, {key: value for key, value in action.items() if key != "call_id"})


_client: ProsperClient | None = None


def client() -> ProsperClient:
    global _client
    if _client is None:
        _client = ProsperClient()
    return _client
