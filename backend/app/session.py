"""Per-call state: what this call has looked up, what it will report, and its JSONL log.

Actions are *staged* during the call and only POSTed by `finish()` once the socket closes
(the window stays open 30 s after hang-up). A submission can never be taken back, so staging
is what lets a caller change their mind on the third turn without leaving a wrong record.
"""

import json
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from loguru import logger

from app import appointment_email, clinic, config, customer_accounts, prosper

# Reported when a call ends with nothing staged: silence always fails, so a reason always goes out.
FALLBACK = {"action": "NO_ACTION", "reason": "out_of_scope"}
SEARCH_BATCH_SECS = 5.0  # searches this close to the last one belong to the same brain step
_TERMINAL = {"NO_ACTION", "ESCALATE"}


def _greeting(now: datetime) -> str:
    part = "morning" if now.hour < 14 else "afternoon" if now.hour < 20 else "evening"
    return f"Clínica Arenal, good {part}. How can I help you?"


@dataclass
class CallSession:
    call_id: str
    stream_sid: str = ""
    from_number: str | None = None
    started_at: datetime = field(default_factory=lambda: datetime.now(config.TZ))
    # Everything the record_* checks accept must have come from a lookup in this call.
    patients: dict[str, dict] = field(default_factory=dict)
    slots: dict[tuple[str, str, datetime], dict] = field(default_factory=dict)
    appointments: dict[str, dict] = field(default_factory=dict)
    caller_matches: list[dict] = field(default_factory=list)
    actions: list[dict] = field(default_factory=list)
    # Every search_availability of the call: {"t", "slots_found", "blocked": [restriction]}.
    # If the call ends with nothing staged, the last batch says why nothing was booked.
    searches: list[dict] = field(default_factory=list)
    finished: bool = False
    # Set once a dictated registration phone is flagged as one digit off the caller-ID number,
    # so the model is warned only once and a repeat (or a second try) is accepted, not looped.
    phone_mismatch_flagged: bool = False
    appointment_emails: dict[str, appointment_email.Recipient] = field(default_factory=dict)
    sent_appointment_emails: set[str] = field(default_factory=set)
    demo_mode: bool = False
    customer_account: customer_accounts.AccountRequest | None = None
    customer_account_result: dict | None = None
    # Agent-initiated hang-up (app/voice/autohangup.py): the voice layer sets
    # agent_finished when the agent's own transcript closed the call, and any later
    # caller speech clears it; in_flight_tools holds the hang-up while a clinic
    # tool is still running so a goodbye can never cut a booking write off.
    agent_finished: bool = False
    in_flight_tools: int = 0
    # Set by the auto hang-up watcher's audio hook (app/voice/autohangup.py):
    # the last time raw caller audio arrived above the speech floor, used to
    # push the goodbye grace back without clearing the arm.
    caller_sound_at: float | None = None

    @property
    def clinic_client(self) -> Any:
        return prosper.client()

    async def execute_tool(
        self, name: str, args: dict, handler: Callable[..., Awaitable[dict]]
    ) -> dict:
        return await handler(self, args)

    def tool_specs(self, specs: list[dict]) -> list[dict]:
        return specs

    @classmethod
    async def start(
        cls,
        call_id: str,
        stream_sid: str = "",
        from_number: str | None = None,
        started_at: datetime | None = None,
        demo_mode: bool | None = None,
    ) -> "CallSession":
        session = cls(call_id=call_id, stream_sid=stream_sid, from_number=from_number)
        if demo_mode is not None:
            session.demo_mode = demo_mode
        if started_at is not None:
            session.started_at = started_at
        session.log(
            "call_started",
            from_number=from_number,
            stream_sid=stream_sid,
            started_at=session.started_at.isoformat(),
        )
        try:
            await clinic.catalogue()
        except Exception as e:  # the call still runs; tools report the outage to the model
            session.log("catalogue_error", error=repr(e))
        if from_number:
            # Caller ID finds the line owner's chart before a word is said. A hint, never proof:
            # the caller is not always the patient.
            try:
                session.caller_matches = await session.clinic_client.directory(phone=from_number)
                session.remember_patients(session.caller_matches)
                session.log(
                    "caller_id_lookup", matches=[m["patient_id"] for m in session.caller_matches]
                )
            except Exception as e:
                session.log("caller_id_error", error=repr(e))
        return session

    @property
    def greeting(self) -> str:
        return _greeting(self.started_at)

    def instructions(self) -> str:
        from app.prompt import instructions

        return instructions(self)

    # ── log ─────────────────────────────────────────────────────────

    def log(self, kind: str, **data: Any) -> None:
        """Append one event to logs/calls/<call_id>.jsonl — enough to explain any utterance later."""
        config.CALLS_DIR.mkdir(parents=True, exist_ok=True)
        line = json.dumps({"t": time.time(), "kind": kind, **data}, ensure_ascii=False, default=str)
        with (config.CALLS_DIR / f"{self.call_id}.jsonl").open("a") as f:
            f.write(line + "\n")

    # ── what lookups returned ───────────────────────────────────────

    def remember_patients(self, matches: list[dict]) -> None:
        for m in matches:
            self.patients[m["patient_id"]] = m

    def remember_slots(self, slots: list[dict]) -> None:
        for s in slots:
            key = (s["provider_id"], s["location_id"], datetime.fromisoformat(s["start_time"]))
            self.slots[key] = s

    def remember_appointments(self, appointments: list[dict]) -> None:
        for a in appointments:
            self.appointments[a["appointment_id"]] = a

    # ── staged actions ──────────────────────────────────────────────

    def stage(self, action: dict) -> list[dict]:
        """Stage one action, replacing whatever it supersedes. Returns everything staged now.

        - NO_ACTION / ESCALATE are the whole outcome: they replace everything.
        - Any write drops a staged NO_ACTION / ESCALATE.
        - A new BOOK for a patient replaces their previous BOOK; a new REGISTER replaces the last;
          a RESCHEDULE/CANCEL replaces any earlier change to the same appointment.
        """
        verb = action["action"]
        if verb in _TERMINAL:
            self.actions = [action]
            self.appointment_emails.clear()
            return self.actions

        def superseded(old: dict) -> bool:
            if old["action"] in _TERMINAL:
                return True
            if verb == "BOOK":
                return old["action"] == "BOOK" and old["patient_id"] == action["patient_id"]
            if verb == "REGISTER":
                return old["action"] == "REGISTER"
            if verb in ("RESCHEDULE", "CANCEL"):
                return (
                    old["action"] in ("RESCHEDULE", "CANCEL")
                    and old["appointment_id"] == action["appointment_id"]
                )
            return False

        self.actions = [a for a in self.actions if not superseded(a)] + [action]
        return self.actions

    def clear_actions(self) -> None:
        self.actions = []
        self.appointment_emails.clear()

    def record_search(self, slots_found: int, blocked: list[str]) -> None:
        self.searches.append(
            {"t": time.monotonic(), "slots_found": slots_found, "blocked": blocked}
        )

    def last_search_batch(self) -> list[dict]:
        """The searches of the brain's latest step: a model often fires several in parallel
        (sites, days, doctors), and they finish in any order."""
        if not self.searches:
            return []
        last = self.searches[-1]["t"]
        return [s for s in self.searches if s["t"] >= last - SEARCH_BATCH_SECS]

    def fallback(self) -> dict:
        """The report for a call that staged nothing (silence always fails).

        The latest batch of searches is the best evidence left. If any of them found a slot,
        something was on offer: `out_of_scope`. If all came back empty with nothing blocked,
        `no_availability`; if one rule blocked every provider, that rule's reason (the
        restriction ids are the first eleven reasons, one-for-one). Anything else stays
        `out_of_scope`.
        """
        from app.tools import REASONS

        batch = self.last_search_batch()
        if batch and not any(s["slots_found"] for s in batch):
            rules = {r for s in batch for r in s["blocked"]}
            if not rules:
                return {"action": "NO_ACTION", "reason": "no_availability"}
            if len(rules) == 1 and (rule := rules.pop()) in REASONS:
                return {"action": "NO_ACTION", "reason": rule}
        return FALLBACK

    async def finish(self) -> list[dict]:
        """POST every staged action (or the fallback) once. Called by the server on hang-up."""
        if self.demo_mode:
            return await self.finish_demo()
        if self.finished:
            return []
        self.finished = True
        actions = self.actions
        if not actions:
            actions = [self.fallback()]
            self.log("fallback", action=actions[0], search_batch=self.last_search_batch())
        results = []
        for action in actions:
            payload = {**action, "call_id": self.call_id}
            status, body = await self._submit_once_retrying(payload)
            self.log("submit", action=action, status=status, response=body)
            if status not in (200, 409):
                logger.error(f"call {self.call_id}: submit {action['action']} -> {status} {body}")
            results.append({"action": action, "status": status, "response": body})
        self.log("call_ended", submitted=[r["status"] for r in results])
        return results

    async def finish_demo(self, *, source: str = "browser") -> list[dict]:
        """Finalize a human browser/Twilio demo; its call ID is not registered with Prosper.

        Persist the final proposal before sending real, clearly labelled demo emails.
        """
        if self.finished:
            return []
        self.finished = True
        actions = self.actions or ([] if self.customer_account else [self.fallback()])
        self.log("demo_outcome", source=source, actions=actions, submitted=False)
        self.customer_account_result = await customer_accounts.finalize(self)
        emails = await appointment_email.send_for_actions(self, self.actions)
        self.log("call_ended", source=source, actions=actions, submitted=False)
        if self.customer_account_result:
            return [{"action": "REGISTER_CUSTOMER", **self.customer_account_result}, *emails]
        return emails

    async def _submit_once_retrying(self, payload: dict) -> tuple[int, Any]:
        # One retry on a network failure only: the record is binary and the window is 30 s.
        for attempt in (1, 2):
            try:
                return await prosper.client().submit(payload)
            except Exception as e:
                self.log("submit_error", attempt=attempt, error=repr(e))
        return 0, "network error"
