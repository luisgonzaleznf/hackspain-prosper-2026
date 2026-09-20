"""Client for the Prosper platform API: the read-only clinic EHR and the submit routes.

Reference: docs/prosper/api-reference.md. Every route but /health needs X-Api-Key.
One shared httpx client serves every concurrent call.
"""

from typing import Any

import httpx

from app import config

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
    def __init__(self, base_url: str, api_key: str, timeout: float = 10.0):
        self._http = httpx.AsyncClient(
            base_url=base_url, headers={"X-Api-Key": api_key}, timeout=timeout
        )

    async def _get(self, path: str, params: dict | list | None = None) -> Any:
        resp = await self._http.get(path, params=params)
        if resp.status_code != 200:
            try:
                detail = resp.json().get("detail", resp.text)
            except ValueError:
                detail = resp.text
            raise ProsperError(resp.status_code, detail)
        return resp.json()

    async def clinic(self) -> dict:
        """The whole catalogue: calendar, restrictions, providers, sites, specialties, types, plans."""
        return await self._get("/api/v1/clinic")

    async def directory(
        self,
        *,
        name: str | None = None,
        national_id: str | None = None,
        phone: str | None = None,
        date_of_birth: str | None = None,
    ) -> list[dict]:
        """Patient search. `name` alone is fuzzy and ranked; the other fields filter exactly."""
        params = {
            k: v
            for k, v in {
                "name": name,
                "national_id": national_id,
                "phone": phone,
                "date_of_birth": date_of_birth,
            }.items()
            if v
        }
        return (await self._get("/api/v1/directory", params))["matches"]

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
        """Slots plus the one appointment type that fits, and `blocked` naming any rule that bit."""
        params: list[tuple[str, str]] = [("date_from", date_from), ("date_to", date_to)]
        for key, value in (
            ("specialty_id", specialty_id),
            ("provider_id", provider_id),
            ("location_id", location_id),
            ("patient_id", patient_id),
        ):
            if value:
                params.append((key, value))
        params += [("insurer", i) for i in insurers or []]
        return await self._get("/api/v1/availability", params)

    async def appointments(self, patient_id: str, when: str = "upcoming") -> list[dict]:
        """The patient's diary; the only source of an appointment_id."""
        data = await self._get(f"/api/v1/patients/{patient_id}/appointments", {"when": when})
        return data["appointments"]

    async def submit(self, action: dict) -> tuple[int, Any]:
        """POST one action to /api/v1/submit/<route>. `action` carries `action` + `call_id` + fields.

        Returns (status, body) instead of raising: 200 accepted, 409 duplicate (fine),
        410 window closed, 404 unknown call, 422 malformed.
        """
        body = {k: v for k, v in action.items() if k != "action"}
        resp = await self._http.post(f"/api/v1/submit/{SUBMIT_ROUTES[action['action']]}", json=body)
        try:
            return resp.status_code, resp.json()
        except ValueError:
            return resp.status_code, resp.text


_client: ProsperClient | None = None


def client() -> ProsperClient:
    global _client
    if _client is None:
        _client = ProsperClient(config.PLATFORM_API_BASE_URL, config.PLATFORM_API_KEY)
    return _client
