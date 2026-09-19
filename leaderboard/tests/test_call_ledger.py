import json
import sys

import pytest
from scripts import call_ledger as ledger

CID = "00000000-0000-5000-8000-000000000001"
CANCEL = {"action": "CANCEL", "appointment_id": "A001"}


@pytest.mark.parametrize(
    "other",
    [
        [{"action": "CANCEL", "appointment_id": "A002"}],
        [{"action": "CANCEL", "appointment_id": "a001"}],
        [CANCEL, CANCEL],
        [{"action": "CANCEL"}],
    ],
)
def test_distinct_outcomes_stay_distinct(other):
    assert ledger.outcome_fingerprint([CANCEL]) != ledger.outcome_fingerprint(other)


def test_refusal_reason_and_booking_fields_are_preserved():
    assert ledger.outcome_fingerprint(
        [{"action": "NO_ACTION", "reason": "out_of_scope"}]
    ) != ledger.outcome_fingerprint([{"action": "NO_ACTION", "reason": "no_availability"}])
    booking = {"action": "BOOK", "patient_id": "P001", "slot": "2026-09-21T09:00:00"}
    assert ledger.outcome_fingerprint([booking]) != ledger.outcome_fingerprint(
        [{**booking, "slot": "2026-09-21T10:00:00"}]
    )


def test_order_and_call_id_do_not_change_outcome():
    second = {"action": "CANCEL", "appointment_id": "A002"}
    assert ledger.outcome_fingerprint([CANCEL, second]) == ledger.outcome_fingerprint(
        [
            {"appointment_id": "A002", "action": "CANCEL", "call_id": "another-call"},
            CANCEL,
        ]
    )


@pytest.mark.parametrize("actions", [[], [None], [{}], [{"appointment_id": "A001"}]])
def test_missing_action_payload_is_unresolved(actions):
    assert ledger.outcome_fingerprint(actions) == "unresolved"


def test_log_and_submissions_preserve_same_complete_outcome(monkeypatch, tmp_path):
    actions = [CANCEL, {"action": "BOOK", "patient_id": "P001", "slot": "some-slot"}]
    events = [{"kind": "call_started", "t": 1}] + [
        {"kind": "submit", "t": i + 2, "action": a} for i, a in enumerate(actions)
    ]
    logged = ledger.summarize(CID, "test", events)
    assert json.loads(logged["submitted"]) == actions
    assert logged["action"] == "BOOK|CANCEL"
    assert (
        logged["outcome_fingerprint"]
        == ledger.summarize(CID, "test", [events[0], *reversed(events[1:])])["outcome_fingerprint"]
    )

    monkeypatch.setattr(sys, "argv", ["call_ledger.py"])
    monkeypatch.setattr(ledger, "OUT", tmp_path / "ledger")
    monkeypatch.setattr(ledger, "fran_calls", lambda: [])
    monkeypatch.setattr(ledger, "local_calls", lambda: [])
    monkeypatch.setattr(ledger, "public_phones", dict)
    monkeypatch.setattr(ledger, "ROOT", tmp_path)
    monkeypatch.setattr(ledger, "dashboard_cases", lambda: ({}, ""))
    monkeypatch.setattr(ledger, "submissions", lambda: {CID: ("2026-09-19T00:00:00Z", actions)})
    ledger.main()
    submitted = json.loads((tmp_path / "ledger.json").read_text())[0]
    assert submitted["outcome_fingerprint"] == logged["outcome_fingerprint"]
    assert json.loads(submitted["submitted"]) == actions
    assert submitted["has_log"] is False


def test_dashboard_refresh_joins_official_row(monkeypatch, tmp_path):
    export = tmp_path / "export.json"
    export.write_text(
        json.dumps(
            {
                "runs": [
                    {
                        "run_id": "official-run",
                        "public": False,
                        "started_at": "2026-09-19T08:44:00Z",
                        "cases": [{"call_id": CID, "status": "passed", "transcript": "omit"}],
                    }
                ]
            }
        )
    )
    monkeypatch.setattr(ledger, "SNAPSHOT", tmp_path / "snapshot.json")
    ledger.refresh_snapshot(export)
    cases, _ = ledger.dashboard_cases()
    assert cases[CID]["dash_run_id"] == "official-run"
    assert cases[CID]["case_key"] == "RA-0919-0844Z#01"
    assert cases[CID]["dash_status"] == "passed"
    assert "transcript" not in ledger.SNAPSHOT.read_text()
