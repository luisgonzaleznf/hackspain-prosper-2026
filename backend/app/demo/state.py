"""In-memory, presentation-safe state for Role-play Studio calls."""

from collections.abc import Mapping, Sequence
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from threading import RLock
from typing import TYPE_CHECKING, Any

from app import clinic, config
from app.demo.models import (
    DemoActionEvidence,
    DemoLedgerEntry,
    DemoMilestone,
    DemoSnapshot,
    DemoToolEvent,
    DemoTranscriptTurn,
)

if TYPE_CHECKING:
    from app.session import CallSession

_LEDGER_PATH = Path("logs/demo/actions.jsonl")

_MILESTONES = (
    ("connected", "Connected to the clinic assistant"),
    ("understood", "Understood the caller's request"),
    ("checked", "Checked the clinic records"),
    ("prepared", "Prepared a safe outcome"),
)

_TOOL_SUMMARIES = {
    "prepare_customer_account": "Captured the customer's name and email",
    "confirm_customer_account": "Confirmed customer account creation and welcome email",
    "resolve_names": "Matched the requested clinic details",
    "find_patient": "Checked the patient record",
    "list_appointments": "Checked upcoming appointments",
    "search_availability": "Checked available appointment times",
    "record_booking": "Prepared the requested booking",
    "record_reschedule": "Prepared the appointment change",
    "record_cancellation": "Prepared the cancellation",
    "record_registration": "Prepared the patient registration",
    "record_no_action": "Recorded that no clinic change is needed",
    "record_escalation": "Prepared a safe handoff to clinic staff",
    "clear_recorded_actions": "Cleared the previously prepared outcome",
}
_RECORD_TOOLS = {
    "confirm_customer_account",
    "record_booking",
    "record_reschedule",
    "record_cancellation",
    "record_registration",
    "record_no_action",
    "record_escalation",
}


def _new_snapshot(session_id: str, scenario_id: str) -> DemoSnapshot:
    return DemoSnapshot(
        session_id=session_id,
        scenario_id=scenario_id,
        status="connecting",
        milestones=[
            DemoMilestone(
                id=milestone_id,
                label=label,
                state="active" if index == 0 else "pending",
            )
            for index, (milestone_id, label) in enumerate(_MILESTONES)
        ],
        transcript=[],
        tools=[],
        actions=[],
    )


def _advance(snapshot: DemoSnapshot, milestone_id: str, *, failed: bool = False) -> None:
    target = next(i for i, item in enumerate(snapshot.milestones) if item.id == milestone_id)
    for index, item in enumerate(snapshot.milestones):
        if index < target and item.state != "failed":
            item.state = "complete"
        elif index == target:
            item.state = "failed" if failed else "complete"
        elif index == target + 1 and not failed and item.state == "pending":
            item.state = "active"


def _tool_summary(name: str, result: object) -> tuple[str, str]:
    # The raw arguments and result deliberately never enter the snapshot. Only a fixed description
    # and safe aggregate counts are allowed through this projection.
    errored = isinstance(result, Mapping) and bool(result.get("error"))
    if errored:
        return "error", f"Could not complete: {_TOOL_SUMMARIES.get(name, 'clinic check').lower()}"

    summary = _TOOL_SUMMARIES.get(name, "Completed a clinic check")
    if isinstance(result, Mapping):
        if name == "find_patient" and isinstance(result.get("count"), int):
            count = result["count"]
            summary = "Found one matching patient record" if count == 1 else f"Found {count} matching patient records"
        elif name == "search_availability" and isinstance(result.get("slots_found"), int):
            count = result["slots_found"]
            summary = f"Found {count} available appointment time{'s' if count != 1 else ''}"
        elif name == "list_appointments" and isinstance(result.get("appointments"), list):
            count = len(result["appointments"])
            summary = f"Found {count} appointment{'s' if count != 1 else ''} to review"
    return "complete", summary

def _catalogue_names() -> dict[str, str]:
    catalogue = clinic.cached() or {}
    records = [*(catalogue.get("providers") or []), *(catalogue.get("locations") or [])]
    return {str(item["id"]): str(item["name"]) for item in records}


def build_action_evidence(session: "CallSession") -> list[DemoActionEvidence]:
    """Explain staged actions using only records and slots observed by this call."""
    from integrations.local_session import LocalCallSession

    persistent = isinstance(session, LocalCallSession)
    names = _catalogue_names()
    evidence: list[DemoActionEvidence] = []
    for action in session.actions:
        verb = str(action["action"])
        fields: list[tuple[str, str]] = []
        checks: list[str] = []
        if verb == "BOOK":
            patient = session.patients.get(str(action["patient_id"]), {})
            slot_key = (
                str(action["provider_id"]),
                str(action["location_id"]),
                datetime.fromisoformat(str(action["slot"])),
            )
            slot = session.slots.get(slot_key, {})
            full_name = " ".join(
                str(patient.get(key) or "")
                for key in ("given_name", "first_surname", "second_surname")
            ).strip()
            fields = [
                ("Patient", full_name or "Verified patient"),
                ("Doctor", str(slot.get("provider_name") or names.get(str(action["provider_id"]), "Verified provider"))),
                ("Clinic", names.get(str(action["location_id"]), str(action["location_id"]))),
                ("Time", datetime.fromisoformat(str(action["slot"])).strftime("%A %d %B, %H:%M")),
                ("Policy", str(action["policy_id"]).replace("_", " ").title()),
            ]
            checks = [
                "Patient matched through clinic records",
                "Slot returned by live availability search",
                "Insurance accepted for this slot",
                "record_booking validation passed",
            ]
        elif verb in {"CANCEL", "RESCHEDULE"}:
            appointment = session.appointments.get(str(action["appointment_id"]), {})
            fields = [
                ("Appointment", datetime.fromisoformat(str(appointment["start_time"])).strftime("%A %d %B, %H:%M") if appointment.get("start_time") else "Verified upcoming appointment"),
                ("Doctor", names.get(str(appointment.get("provider_id") or action.get("provider_id") or ""), "Verified provider")),
                ("Clinic", names.get(str(appointment.get("location_id") or action.get("location_id") or ""), "Verified clinic")),
            ]
            checks = [
                "Patient identity matched",
                "Appointment returned by the live clinic diary",
                f"record_{'cancellation' if verb == 'CANCEL' else 'reschedule'} validation passed",
            ]
        elif verb == "ESCALATE":
            fields = [("Reason", str(action["reason"]).replace("_", " ").title())]
            checks = ["Safety rule matched", "No calendar action prepared", "record_escalation validation passed"]
        elif verb == "NO_ACTION":
            fields = [("Reason", str(action["reason"]).replace("_", " ").title())]
            checks = ["Clinic rule or availability checked", "record_no_action validation passed"]
        else:
            fields = [("Action", verb.replace("_", " ").title())]
            checks = ["Deterministic action validation passed"]
        labels = {"BOOK": "Booking prepared", "CANCEL": "Cancellation prepared", "RESCHEDULE": "Change prepared", "ESCALATE": "Escalated safely", "NO_ACTION": "No action required"}
        if persistent:
            labels.update(BOOK="Booking saved", CANCEL="Cancellation saved", RESCHEDULE="Change saved", REGISTER="Patient registered")
        evidence.append(
            DemoActionEvidence(
                action=verb,
                label=labels.get(verb, "Action prepared"),
                fields=fields,
                checks=checks,
            )
        )
    if session.customer_account_result:
        result = session.customer_account_result
        saved = result.get("status") in {"created", "existing"}
        evidence.append(
            DemoActionEvidence(
                action="REGISTER",
                label="Customer account saved" if saved else "Customer account could not be saved",
                fields=[
                    ("Account reference", result.get("account_id", "Unavailable")),
                    (
                        "Email",
                        "Accepted by Resend"
                        if result.get("email_status") == "accepted"
                        else "Not sent; check the trace",
                    ),
                ],
                checks=["Name and email read back and confirmed", "Saved in local SQLite database"]
                if saved
                else ["Database write failed; no email sent"],
            )
        )
    return evidence


class DemoSessionRegistry:
    """Thread-safe process-local snapshots fed by the voice call's ordinary log events."""

    def __init__(self) -> None:
        self._sessions: dict[str, DemoSnapshot] = {}
        self._claimed: set[str] = set()
        self._recorded: set[str] = set()
        self._lock = RLock()

    def create(self, session_id: str, scenario_id: str) -> DemoSnapshot:
        with self._lock:
            existing = self._sessions.get(session_id)
            if existing is not None:
                if existing.scenario_id != scenario_id:
                    raise ValueError(f"demo session {session_id} already uses another scenario")
                return existing.model_copy(deep=True)
            snapshot = _new_snapshot(session_id, scenario_id)
            self._sessions[session_id] = snapshot
            return snapshot.model_copy(deep=True)

    def claim(self, session_id: str) -> bool:
        """Return true exactly once so WebRTC renegotiation cannot start a second bot."""
        with self._lock:
            if session_id in self._claimed:
                return False
            self._claimed.add(session_id)
            return True

    def get(self, session_id: str) -> DemoSnapshot:
        with self._lock:
            try:
                return self._sessions[session_id].model_copy(deep=True)
            except KeyError as error:
                raise KeyError(session_id) from error

    def log(self, session_id: str, kind: str, **data: Any) -> DemoSnapshot:
        with self._lock:
            try:
                snapshot = self._sessions[session_id]
            except KeyError as error:
                raise KeyError(session_id) from error

            if kind == "call_started":
                snapshot.status = "live"
                _advance(snapshot, "connected")
            elif kind == "transcript":
                role = "agent" if data.get("role") in {"agent", "assistant"} else "user"
                text = str(data.get("text") or "").strip()
                if text:
                    snapshot.transcript.append(
                        DemoTranscriptTurn(
                            role=role,
                            text=text,
                            interrupted=bool(data.get("interrupted", False)),
                        )
                    )
                    if role == "user":
                        _advance(snapshot, "understood")
            elif kind == "tool":
                name = str(data.get("name") or "")
                status, summary = _tool_summary(name, data.get("result"))
                snapshot.tools.append(DemoToolEvent(name=name, status=status, summary=summary))
                _advance(snapshot, "checked", failed=status == "error")
                if name in _RECORD_TOOLS and status == "complete":
                    _advance(snapshot, "prepared")
            elif kind == "action_staged":
                _advance(snapshot, "prepared")
            elif kind == "actions_cleared":
                snapshot.actions = []
                prepared = next(item for item in snapshot.milestones if item.id == "prepared")
                prepared.state = "active"
            elif kind in {"voice_error", "demo_error"}:
                snapshot.status = "error"
                snapshot.error = "The demo call ended unexpectedly. Please try again."

            return snapshot.model_copy(deep=True)

    def outcome(
        self,
        session_id: str,
        actions: Sequence[Mapping[str, Any]],
        evidence: Sequence[DemoActionEvidence],
    ) -> DemoSnapshot:
        with self._lock:
            snapshot = self._sessions[session_id]
            snapshot.actions = deepcopy([dict(action) for action in actions])
            snapshot.evidence = [item.model_copy(deep=True) for item in evidence]
            if snapshot.actions:
                _advance(snapshot, "prepared")
            return snapshot.model_copy(deep=True)


    def end(
        self,
        session_id: str,
        actions: Sequence[Mapping[str, Any]] = (),
        evidence: Sequence[DemoActionEvidence] = (),
    ) -> DemoSnapshot:
        """Complete a demo, expose safe evidence, and persist it without submitting anything."""
        with self._lock:
            try:
                snapshot = self._sessions[session_id]
            except KeyError as error:
                raise KeyError(session_id) from error
            snapshot.status = "error" if snapshot.error else "complete"
            snapshot.actions = deepcopy([dict(action) for action in actions])
            snapshot.evidence = [item.model_copy(deep=True) for item in evidence]
            if snapshot.actions:
                _advance(snapshot, "prepared")
            if session_id not in self._recorded:
                entry = DemoLedgerEntry(
                    session_id=session_id,
                    scenario_id=snapshot.scenario_id,
                    completed_at=datetime.now(config.TZ).isoformat(),
                    evidence=[item.model_copy(deep=True) for item in snapshot.evidence],
                    status=snapshot.status,
                    error=snapshot.error,
                )
                _LEDGER_PATH.parent.mkdir(parents=True, exist_ok=True)
                with _LEDGER_PATH.open("a", encoding="utf-8") as ledger:
                    ledger.write(entry.model_dump_json() + "\n")
                self._recorded.add(session_id)
            return snapshot.model_copy(deep=True)

    def ledger(self, limit: int = 20) -> list[DemoLedgerEntry]:
        if not _LEDGER_PATH.is_file():
            return []
        lines = _LEDGER_PATH.read_text(encoding="utf-8").splitlines()
        entries = [DemoLedgerEntry.model_validate_json(line) for line in lines[-limit:] if line]
        return list(reversed(entries))


registry = DemoSessionRegistry()


def create_session(session_id: str, scenario_id: str) -> DemoSnapshot:
    return registry.create(session_id, scenario_id)

def claim_session(session_id: str) -> bool:
    return registry.claim(session_id)


def get_session(session_id: str) -> DemoSnapshot:
    return registry.get(session_id)


def log_event(session_id: str, kind: str, **data: Any) -> DemoSnapshot:
    return registry.log(session_id, kind, **data)

def update_outcome(
    session_id: str,
    actions: Sequence[Mapping[str, Any]],
    evidence: Sequence[DemoActionEvidence],
) -> DemoSnapshot:
    return registry.outcome(session_id, actions, evidence)


def end_session(
    session_id: str,
    actions: Sequence[Mapping[str, Any]] = (),
    evidence: Sequence[DemoActionEvidence] = (),
) -> DemoSnapshot:
    return registry.end(session_id, actions, evidence)
