"""Phone-call tools that commit confirmed patient/calendar changes during the call."""

import asyncio
from collections.abc import Awaitable, Callable
from copy import deepcopy
from datetime import date, datetime
from functools import cached_property

from app import appointment_email, clinic, prompt
from app.session import CallSession

from integrations.local_clinic import LocalClinic
from integrations.local_store import LocalStore, normalized, phone_digits

WRITES = {"record_registration", "record_booking", "record_reschedule", "record_cancellation"}

LOCAL_RULES = """
PHONE CALLS — THE LOCAL PATIENT REGISTER AND CALENDAR
These rules replace the staged-report workflow in the general clinic instructions.
Patient registrations and calendar writes are saved immediately by the tools. Only
say a change is saved after a tool returns persisted=true. If a tool returns an error,
explain it and resolve it; never claim the operation succeeded. Never promise email:
email sending is not connected yet.

Always call find_patient with the patient's full name AND a second identifier supplied
by the caller (date_of_birth, national_id or phone), even when CALLER ID found one chart.
Caller ID alone is not verification. Ask about authorization for a relative as usual.

For an unknown patient, collect the existing registration fields, read back the details,
and ask permission to create the profile. Only then call record_registration with
confirmed=true. The successful result supplies patient_id; the new patient CAN book in
this same call. Search with that patient_id and the patient's actual insurer. Do not
invent referrals, insurance authorization or previous visits. Correcting a profile
created in this call uses record_registration again with its patient_id, corrected fields
and confirmed=true. Omit patient_id when registering a different person. If it already exists, find and verify it instead of creating a duplicate.

After the caller agrees to the exact doctor, site and time, call record_booking with
confirmed=true; it returns an appointment_id. A second different booking is an additional
appointment, NOT a replacement. To change a booking use list_appointments then
record_reschedule with confirmed=true; to withdraw it use record_cancellation with
confirmed=true. These work in this call and future calls. An identical retry doesn't
create a second appointment. Don't use clear_recorded_actions: writes are already saved.
NO_ACTION and ESCALATE do not erase saved registrations or appointments.
"""


class LocalCallSession(CallSession):
    @cached_property
    def store(self) -> LocalStore:
        return LocalStore()

    @cached_property
    def clinic_client(self) -> LocalClinic:
        return LocalClinic(self.store, self.started_at)

    @cached_property
    def verified(self) -> set[str]:
        return set()

    @cached_property
    def tool_lock(self) -> asyncio.Lock:
        return asyncio.Lock()

    @cached_property
    def registered_ids(self) -> set[str]:
        return set()

    registration_id: str | None = None
    saved: dict | None = None

    def instructions(self) -> str:
        # The scored workflow is a named prompt section, not offsets into mutable prose.
        clinic_rules = prompt.RULES.replace(prompt.STAGED_WRITE_RULES, "").replace(
            "it replaces ALL actions.", "it does not undo saved actions."
        )
        instructions = prompt.instructions(self, rules=clinic_rules)
        rules = LOCAL_RULES
        if self.demo_mode and appointment_email.enabled():
            rules = rules.replace(
                "Never promise email:\nemail sending is not connected yet.",
                "Follow the appointment email instructions: the backend uses the identified patient's email on file automatically after hang-up. Only request an address if the booking tool reports needs_address. Never claim delivery before the sender reports success.",
            )
        return instructions + "\n\n" + rules

    def tool_specs(self, specs: list[dict]) -> list[dict]:
        specs = [deepcopy(s) for s in specs if s["name"] != "clear_recorded_actions"]
        descriptions = {
            "record_registration": "Create a persistent local patient profile after the caller confirms the registration details. Returns patient_id, usable immediately to search and book. Correct a profile created in this call by calling again with corrected details and confirmation.",
            "record_booking": "Save an actual local appointment after the caller accepts its exact details. Returns appointment_id. A different booking adds an appointment; use record_reschedule to move an existing one.",
            "record_reschedule": "Persist a move of an upcoming appointment after the caller agrees to the new exact slot.",
            "record_cancellation": "Persist cancellation of an upcoming appointment after the caller agrees.",
            "record_no_action": "Record why no further action can be taken. Does not undo saved appointments or profiles.",
            "record_escalation": "Record why a human is needed. Does not undo saved appointments or profiles.",
        }
        for spec in specs:
            if spec["name"] in descriptions:
                spec["description"] = descriptions[spec["name"]]
            if spec["name"] == "record_registration":
                spec["parameters"]["properties"]["patient_id"] = {
                    "type": "string",
                    "description": "Only for correcting a profile created in this call. Omit for a new person.",
                }
            if spec["name"] in WRITES:
                spec["parameters"]["properties"]["confirmed"] = {
                    "type": "boolean",
                    "description": "True only after the caller explicitly agrees to this change.",
                }
                spec["parameters"]["required"].append("confirmed")
        return specs

    def _verify(self, args: dict, result: dict) -> None:
        matches = result.get("matches", [])
        if len(matches) != 1 or not args.get("name"):
            return
        patient = self.patients[matches[0]["patient_id"]]
        words = {normalized(w) for w in args["name"].split()}
        on_file = {
            normalized(w)
            for k in ("given_name", "first_surname", "second_surname")
            for w in patient[k].split()
        }
        if len(words) < 2 or not words <= on_file:
            return
        exact = (
            (args.get("date_of_birth") == patient["date_of_birth"])
            or (
                bool(args.get("national_id"))
                and normalized(args["national_id"]) == normalized(patient["national_id"])
            )
            or (
                bool(args.get("phone"))
                and phone_digits(args["phone"]) == phone_digits(patient["phone"])
            )
        )
        if exact:
            self.verified.add(patient["patient_id"])
            self.log("identity_verified", patient_id=patient["patient_id"])

    async def execute_tool(
        self, name: str, args: dict, handler: Callable[..., Awaitable[dict]]
    ) -> dict:
        async with self.tool_lock:
            self.saved = None
            if name == "clear_recorded_actions":
                return {
                    "error": "Changes are already saved. Use list_appointments and record_cancellation or record_reschedule after confirmation."
                }
            if name in WRITES and args.get("confirmed") is not True:
                return {
                    "error": "Ask the caller to confirm these exact details, then call again with confirmed=true. Nothing has been saved."
                }
            if name == "record_registration":
                self.registration_id = args.get("patient_id")
                if self.registration_id and self.registration_id not in self.registered_ids:
                    return {"error": "Only profiles created in this call can be corrected here."}
                if not self.registration_id:
                    self.registration_id = next(
                        (
                            pid
                            for pid in self.registered_ids
                            if self.patients[pid]["national_id"]
                            == clinic.normalize_national_id(args.get("national_id", ""))
                        ),
                        None,
                    )
                if (
                    args.get("date_of_birth")
                    and date.fromisoformat(args["date_of_birth"]) > self.started_at.date()
                ):
                    return {"error": "Date of birth cannot be in the future."}
                if args.get("national_id"):
                    duplicates = await self.clinic_client.directory(
                        national_id=clinic.normalize_national_id(args["national_id"])
                    )
                    if any(p["patient_id"] != self.registration_id for p in duplicates):
                        return {
                            "error": "This DNI/NIE already exists. Use find_patient with name and a second identifier; do not register it again."
                        }
            if name in {
                "record_booking",
                "record_reschedule",
                "record_cancellation",
                "list_appointments",
            }:
                appointment = self.appointments.get(args.get("appointment_id") or "", {})
                patient_id = args.get("patient_id") or appointment.get("patient_id")
                if patient_id not in self.verified:
                    return {
                        "error": "Verify the patient with find_patient: full name plus date of birth, DNI/NIE or phone before using their calendar."
                    }
                if name == "record_booking" and (
                    previous := self.store.existing_booking(self.call_id, args)
                ):
                    return {
                        **previous,
                        "persisted": True,
                        "note": "This exact booking is already saved; no duplicate was created.",
                    }
                if name in {"record_reschedule", "record_cancellation"}:
                    current = await self.clinic_client.appointments(patient_id)
                    matching = next(
                        (a for a in current if a["appointment_id"] == args["appointment_id"]), None
                    )
                    if matching is None or matching["start_time"] != appointment["start_time"]:
                        return {
                            "error": "This appointment has changed or is no longer upcoming. Call list_appointments again."
                        }
                if name in {"record_booking", "record_reschedule"}:
                    start = datetime.fromisoformat(args["slot"])
                    if start.tzinfo is None:
                        return {
                            "error": "Use the exact timezone-aware slot returned by search_availability."
                        }
                    # Only revalidate a slot the caller was actually offered for this call.
                    offered = self.slots.get((args["provider_id"], args["location_id"], start))
                    if offered is None:
                        return {"error": "Search availability and offer a returned slot first."}
                    data = await self.clinic_client.availability(
                        start.date().isoformat(),
                        start.date().isoformat(),
                        patient_id=patient_id,
                        provider_id=args["provider_id"],
                        location_id=args["location_id"],
                        insurers=[args["policy_id"]],
                        exclude_appointment_id=args.get("appointment_id"),
                    )
                    fresh = next(
                        (
                            s
                            for s in data["slots"]
                            if datetime.fromisoformat(s["start_time"]) == start
                        ),
                        None,
                    )
                    if fresh is None:
                        return {
                            "error": "That slot is no longer available or eligible for this patient. Search again; nothing has changed."
                        }
                    self.remember_slots([fresh])
            try:
                result = await handler(self, args)
            except ValueError as error:
                return {"error": str(error)}
            if name == "find_patient":
                self._verify(args, result)
                result["verified_patient_ids"] = sorted(self.verified)
                if result.get("count") == 0:
                    result["note"] = (
                        "No matching patient. Recheck the details; if new, collect registration details and consent, then register and book using the returned patient_id."
                    )
            if self.saved:
                result.update(
                    self.saved,
                    persisted=True,
                    note="Saved in the clinic's local records. Confirm success to the caller. Email has not been sent.",
                )
            return result

    def stage(self, action: dict) -> list[dict]:
        verb = action["action"]
        if verb in {"REGISTER", "BOOK", "RESCHEDULE", "CANCEL"}:
            appointment = self.appointments.get(action.get("appointment_id", ""))
            patient_id = action.get("patient_id") or (appointment or {}).get("patient_id")
            patient = self.patients.get(patient_id or "")
            slot = None
            if verb in {"BOOK", "RESCHEDULE"}:
                slot = self.slots[
                    (
                        action["provider_id"],
                        action["location_id"],
                        datetime.fromisoformat(action["slot"]),
                    )
                ]
            self.saved = self.store.save(
                self.call_id,
                action,
                patient=patient,
                appointment=appointment,
                slot=slot,
                registration_id=self.registration_id,
            )
            if verb == "REGISTER":
                self.registration_id = self.saved["patient_id"]
                self.registered_ids.add(self.registration_id)
                self.remember_patients([self.saved["patient"]])
                self.verified.add(self.saved["patient_id"])
            if "appointment" in self.saved:
                self.remember_appointments([self.saved["appointment"]])
            self.log("local_write", action=action, result=self.saved)
        if action not in self.actions:
            self.actions.append(action)
        return self.actions

    async def finish_demo(self, *, source: str = "browser") -> list[dict]:
        # Local writes already happened. Email only the currently saved booking,
        # never an earlier slot that was moved or cancelled during this call.
        diary = self.store.appointments()
        self.actions = [
            action
            for action in self.actions
            if action["action"] not in {"BOOK", "RESCHEDULE"}
            or any(
                appointment["start_time"] == action["slot"]
                and appointment["provider_id"] == action["provider_id"]
                and appointment["location_id"] == action["location_id"]
                and (
                    appointment["patient_id"] == action.get("patient_id")
                    if action["action"] == "BOOK"
                    else appointment["appointment_id"] == action["appointment_id"]
                )
                for appointment in diary
            )
        ]
        return await super().finish_demo(source=source)

    async def finish(self) -> list[dict]:
        if self.finished:
            return []
        self.finished = True
        self.log(
            "call_ended",
            source="twilio",
            actions=self.actions or [self.fallback()],
            submitted=False,
        )
        return []
