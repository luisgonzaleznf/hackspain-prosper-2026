"""Faster identification: find_patient's DNI/NIE path and the caller-ID chart in the prompt.
Offline: the clinic is replaced by a recorder."""

import asyncio
import json
from datetime import datetime

import pytest
from app import config
from app.prompt import instructions
from app.session import CallSession
from app.tools import call_tool
from integrations import local_clinic

NOW = datetime(2026, 9, 18, 19, 30, tzinfo=config.TZ)
IGNACIO = {
    "patient_id": "P00005",
    "given_name": "Ignacio",
    "first_surname": "Vázquez",
    "second_surname": "Moreno",
    "national_id": "65699248R",
    "date_of_birth": "1939-12-09",
    "phone": "731169716",
    "has_visited_before": True,
    "insurer": "cigna",
    "referrals": [],
    "note": "",
    "matched_fields": ["phone"],
}


class Directory:
    """Records every /directory query and answers with a fixed list."""

    def __init__(self, answer: list[dict]):
        self.answer = answer
        self.queries: list[dict] = []

    async def directory(self, **query):
        self.queries.append(query)
        return self.answer


@pytest.fixture(autouse=True)
def calls_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "CALLS_DIR", tmp_path)


def fake(monkeypatch, answer: list[dict]) -> Directory:
    d = Directory(answer)
    monkeypatch.setattr(local_clinic, "client", lambda *_, **__: d)
    return d


def session(held: list[dict] | None = None) -> CallSession:
    s = CallSession(call_id="00000000-0000-0000-0000-000000000001", started_at=NOW)
    if held:
        s.caller_matches = held
        s.remember_patients(held)
    return s


def find(s: CallSession, **args) -> dict:
    return asyncio.run(call_tool(s, "find_patient", args))


# ── the DNI/NIE path ────────────────────────────────────────────────


def test_id_of_a_patient_already_held_needs_no_lookup(monkeypatch):
    d = fake(monkeypatch, [])
    r = find(session([IGNACIO]), name="Ignacio Vázquez Moreno", national_id="65699248-r")
    assert d.queries == []
    assert [m["patient_id"] for m in r["matches"]] == ["P00005"]
    assert r["matches"][0]["matched_on"] == ["national_id"]


def test_unknown_id_is_looked_up_alone_without_the_slow_name(monkeypatch):
    d = fake(monkeypatch, [IGNACIO])
    r = find(session(), name="Ignacio Vázquez", national_id="65699248R")
    assert d.queries == [{"national_id": "65699248R"}]
    assert r["count"] == 1 and "note" not in r


def test_a_wrong_date_of_birth_still_excludes(monkeypatch):
    fake(monkeypatch, [])
    r = find(session([IGNACIO]), national_id="65699248R", date_of_birth="1940-12-09")
    assert r["count"] == 0
    assert "Nobody matches" in r["note"]


def test_the_name_never_filters_but_a_clear_mismatch_is_flagged(monkeypatch):
    fake(monkeypatch, [])
    r = find(session([IGNACIO]), name="Seth Pérez", national_id="65699248R")
    assert r["count"] == 1
    assert "Ignacio Vázquez Moreno" in r["note"]


def test_a_misheard_name_sharing_a_surname_is_not_flagged(monkeypatch):
    fake(monkeypatch, [])
    r = find(session([IGNACIO]), name="Ignasio Basquez Moreno", national_id="65699248R")
    assert "note" not in r


# ── what still goes to /directory unchanged ─────────────────────────


@pytest.mark.parametrize(
    "args",
    [
        {"name": "Ignacio Vázquez Moreno", "date_of_birth": "1939-12-09"},
        {"name": "Ignacio Vázquez Moreno"},
        {"national_id": "65699248R", "phone": "731169716"},  # the directory's own phone digit rule
        {"national_id": "65699248R", "date_of_birth": "9 Dec 1939"},  # /directory rejects it
    ],
)
def test_other_queries_go_to_the_directory_as_before(monkeypatch, args):
    d = fake(monkeypatch, [IGNACIO])
    find(session([IGNACIO]), **args)
    assert len(d.queries) == 1
    assert set(d.queries[0]) == set(args)


# ── the caller-ID chart in the prompt ───────────────────────────────


def test_one_caller_id_match_puts_its_chart_in_the_prompt():
    s = session([IGNACIO])
    s.from_number = "+34731169716"
    text = instructions(s)
    line = next(ln for ln in text.splitlines() if ln.startswith("CALLER ID"))
    chart = json.loads(line.split("already looked up: ", 1)[1].split("}. ", 1)[0] + "}")
    assert chart["patient_id"] == "P00005"
    assert chart["date_of_birth"] == "1939-12-09"
    assert "65699248R" not in line  # ids stay masked, as in find_patient
    assert "without calling find_patient" in text


def test_several_caller_id_matches_still_require_find_patient():
    s = session([IGNACIO, {**IGNACIO, "patient_id": "P00006", "given_name": "Lucía"}])
    s.from_number = "+34731169716"
    line = next(ln for ln in instructions(s).splitlines() if ln.startswith("CALLER ID"))
    assert "several people" in line and "find_patient" in line


def test_a_caller_id_patient_can_be_booked_without_find_patient():
    s = session([IGNACIO])
    s.remember_slots(
        [
            {
                "provider_id": "PR10",
                "location_id": "sur",
                "appointment_type_id": "orthopaedic_review",
                "start_time": "2026-09-21T09:30:00+02:00",
                "payable_with": ["cigna"],
            }
        ]
    )
    r = asyncio.run(
        call_tool(
            s,
            "record_booking",
            {
                "patient_id": "P00005",
                "provider_id": "PR10",
                "location_id": "sur",
                "appointment_type_id": "orthopaedic_review",
                "slot": "2026-09-21T09:30:00+02:00",
                "policy_id": "cigna",
            },
        )
    )
    assert "error" not in r, r
