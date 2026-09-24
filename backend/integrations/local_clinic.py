"""Merge Prosper reads with locally registered patients and booked appointments."""

from datetime import date, datetime

from app import clinic, config, prosper

from integrations.local_store import LocalStore, overlaps


class LocalClinic:
    def __init__(self, store: LocalStore, now: datetime):
        self.store = store
        self.now = now

    async def directory(self, **query) -> list[dict]:
        local = self.store.directory(**query)
        remote = await prosper.client().directory(**query)
        return remote + local

    async def appointments(self, patient_id: str, when: str = "upcoming") -> list[dict]:
        local = self.store.appointments(patient_id, include_cancelled=True)
        remote = (
            []
            if self.store.patient(patient_id)
            else await prosper.client().appointments(patient_id, "all")
        )
        replaced = {a["appointment_id"] for a in local}
        merged = [a for a in remote if a["appointment_id"] not in replaced]
        merged += [a for a in local if a["status"] == "booked"]
        return sorted(
            [
                a
                for a in merged
                if when == "all"
                or (datetime.fromisoformat(a["start_time"]) > self.now) == (when == "upcoming")
            ],
            key=lambda a: datetime.fromisoformat(a["start_time"]),
        )

    async def availability(
        self,
        date_from: str,
        date_to: str,
        *,
        patient_id=None,
        insurers=None,
        exclude_appointment_id=None,
        **filters,
    ) -> dict:
        patient = self.store.patient(patient_id) if patient_id else None
        plans = insurers or ([patient["insurer"]] if patient else None)
        data = await prosper.client().availability(
            date_from,
            date_to,
            patient_id=None if patient else patient_id,
            insurers=plans,
            **filters,
        )
        if patient:
            cat = await clinic.catalogue()
            providers = {p["id"]: p for p in cat["providers"]}
            specialties = {s["id"]: s for s in cat["specialties"]}
            kept = []
            blocked = list(data["blocked"])
            for slot in data["slots"]:
                specialty = specialties[providers[slot["provider_id"]]["specialty_id"]]
                reason = None
                # A name-only registration has no date of birth yet: the age check waits
                # for reception, and the agent routes children under 14 to paediatrics.
                if patient.get("date_of_birth"):
                    dob = date.fromisoformat(patient["date_of_birth"])
                    day = datetime.fromisoformat(slot["start_time"]).astimezone(config.TZ).date()
                    months = (
                        (day.year - dob.year) * 12 + day.month - dob.month - (day.day < dob.day)
                    )
                    if months < specialty["min_age_months"] or (
                        specialty["max_age_months"] is not None
                        and months > specialty["max_age_months"]
                    ):
                        reason = "not_eligible_age"
                if (
                    not reason
                    and specialty["referral_required"]
                    and specialty["id"] not in patient["referrals"]
                ):
                    reason = "referral_required"
                if reason:
                    item = {"provider_id": slot["provider_id"], "restriction": reason}
                    if item not in blocked:
                        blocked.append(item)
                    continue
                # Prosper cannot check patient-specific insurer authorizations for an ID
                # it does not own. Keep first GP/paediatric visits usable; don't invent
                # authorization/allowance for insured specialist care.
                if specialty["id"] not in {"general_practice", "paediatrics"} and plans != [
                    "privado"
                ]:
                    raise prosper.ProsperError(
                        422,
                        "Insurance authorization for a locally registered patient's specialist visit needs staff verification. Do not claim it is covered. Private payment is an option only if the caller explicitly chooses it.",
                    )
                if data["appointment_type"]["new_patient_requirement"] != "new_only":
                    raise prosper.ProsperError(
                        422, "The clinic did not return a first-visit slot for this new patient."
                    )
                kept.append(slot)
            data = {**data, "slots": kept, "blocked": blocked}
        occupied = self.store.appointments()
        # Include the identified patient's Prosper diary too: the provider being free
        # does not imply the patient can attend two appointments at the same time.
        if patient_id:
            occupied += await self.appointments(patient_id)
        data = {
            **data,
            "slots": [
                slot
                for slot in data["slots"]
                if not any(
                    a["appointment_id"] != exclude_appointment_id
                    and (a["provider_id"] == slot["provider_id"] or a["patient_id"] == patient_id)
                    and overlaps(slot, a)
                    for a in occupied
                )
            ],
        }
        return data
