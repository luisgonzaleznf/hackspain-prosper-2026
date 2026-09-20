from typing import Literal

from pydantic import BaseModel, Field


class DemoPersona(BaseModel):
    id: str
    title: str
    name: str
    phone: str
    facts: list[tuple[str, str]]
    objective: str
    opening_hint: str
    expected_outcome: Literal["BOOK", "CANCEL", "ESCALATE"]


class DemoStartRequest(BaseModel):
    scenario_id: str
    from_number: str | None = Field(default=None, pattern=r"^\+?[0-9]{9,15}$")

class DemoMilestone(BaseModel):
    id: str
    label: str
    state: Literal["pending", "active", "complete", "failed"]


class DemoToolEvent(BaseModel):
    name: str
    status: Literal["running", "complete", "error"]
    summary: str


class DemoTranscriptTurn(BaseModel):
    role: Literal["user", "agent"]
    text: str
    interrupted: bool = False

class DemoActionEvidence(BaseModel):
    action: Literal["BOOK", "CANCEL", "RESCHEDULE", "REGISTER", "NO_ACTION", "ESCALATE"]
    label: str
    fields: list[tuple[str, str]]
    checks: list[str]


class DemoLedgerEntry(BaseModel):
    session_id: str
    scenario_id: str
    completed_at: str
    evidence: list[DemoActionEvidence]
    status: str = "complete"
    error: str | None = None


class DemoSnapshot(BaseModel):
    session_id: str
    scenario_id: str
    status: Literal["connecting", "live", "ending", "complete", "error"]
    milestones: list[DemoMilestone]
    transcript: list[DemoTranscriptTurn]
    tools: list[DemoToolEvent]
    actions: list[dict]
    evidence: list[DemoActionEvidence] = Field(default_factory=list)
    error: str | None = None
