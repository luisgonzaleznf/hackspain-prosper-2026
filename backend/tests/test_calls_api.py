import json

import pytest
from app import config
from app.dashboard import app
from fastapi.testclient import TestClient
from integrations.local_store import LocalStore

CALL = "00000000-0000-5000-8000-000000000001"

LINES = [
    {"t": 100.0, "kind": "call_started", "from_number": "+34600000000"},
    {"t": 101.0, "kind": "caller_id_lookup", "matches": ["P01842"]},
    {"t": 102.0, "kind": "transcript", "role": "agent", "text": "Clínica Arenal."},
    {"t": 103.0, "kind": "codex", "event": "noise"},
    {"t": 104.0, "kind": "tool", "name": "search_availability", "args": {}, "result": {"slots": 1}},
    {
        "t": 105.0,
        "kind": "local_write",
        "action": {"action": "BOOK", "patient_id": "P01842"},
        "result": {"appointment_id": "LA1", "patient_id": "P01842"},
    },
    {
        "t": 105.1,
        "kind": "action_staged",
        "action": {"action": "BOOK", "patient_id": "P01842"},
        "all_staged": [{"action": "BOOK", "patient_id": "P01842"}],
    },
    {
        "t": 105.2,
        "kind": "tool",
        "name": "record_booking",
        "args": {"patient_id": "P01842", "confirmed": True},
        "result": {"appointment_id": "LA1", "persisted": True},
    },
    {"t": 111.0, "kind": "call_ended", "actions": [{"action": "BOOK", "patient_id": "P01842"}]},
]
WRITE = LINES[5]


@pytest.fixture
def client(tmp_path, monkeypatch):
    calls = tmp_path / "calls"
    calls.mkdir()
    body = "".join(json.dumps(line) + "\n" for line in LINES)
    (calls / f"{CALL}.jsonl").write_text(body)
    # A half-written last line is what a live call looks like on disk.
    (calls / "00000000-0000-4000-8000-000000000002.jsonl").write_text(
        json.dumps(LINES[0]) + '\n{"t": 200.0, "kind": "transc'
    )
    monkeypatch.setattr(config, "CALLS_DIR", calls)
    monkeypatch.setattr(config, "AUDIO_DIR", tmp_path / "audio")
    return TestClient(app)


def test_index_summarises_every_call_newest_first(client):
    body = client.get("/api/calls").json()
    assert len(body["calls"]) == 2
    assert [c["started_at"] for c in body["calls"]] == sorted(
        [c["started_at"] for c in body["calls"]], reverse=True
    )
    booked = next(c for c in body["calls"] if c["call_id"] == CALL)
    assert booked["status"] == "saved"
    assert booked["action"] == "BOOK"
    assert booked["duration_seconds"] == 11.0
    assert booked["has_audio"] is False


def test_a_half_written_line_does_not_break_the_index(client):
    body = client.get("/api/calls").json()
    partial = next(c for c in body["calls"] if c["call_id"].endswith("002"))
    # The exact string the console's `isActive` looks for; a call still on the
    # socket has to reach the Live screen.
    assert partial["status"] == "in progress"


@pytest.mark.parametrize("kind", ["call_ended", "stop_received", "socket_closed", "closed_by_agent"])
def test_hangup_stops_the_live_call_clock_before_cleanup_finishes(client, tmp_path, kind):
    path = tmp_path / "calls" / f"{CALL}.jsonl"
    lines = [
        LINES[0],
        {"t": 130.0, "kind": kind},
        {"t": 140.0, "kind": "recording.saved"},
    ]
    path.write_text("".join(json.dumps(line) + "\n" for line in lines))
    summary = client.get(f"/api/calls/{CALL}").json()["summary"]
    assert summary["status"] == "ended"
    assert summary["duration_seconds"] == 30.0


def test_new_call_appears_immediately_and_keeps_its_identity_after_hangup(client, tmp_path):
    call_id = "live-call"
    path = tmp_path / "calls" / f"{call_id}.jsonl"
    path.write_text(json.dumps({"t": 200.0, "kind": "call_started"}) + "\n")
    calls = client.get("/api/calls").json()["calls"]
    assert calls[0]["call_id"] == call_id
    assert calls[0]["status"] == "in progress"
    assert calls[0]["duration_seconds"] == 0.0

    with path.open("a") as log:
        log.write(json.dumps({"t": 230.0, "kind": "stop_received"}) + "\n")
        log.write(json.dumps({**WRITE, "t": 240.0}) + "\n")
        log.write(json.dumps({"t": 241.0, "kind": "call_ended"}) + "\n")
    calls = client.get("/api/calls").json()["calls"]
    completed = [call for call in calls if call["call_id"] == call_id]
    assert len(completed) == 1
    assert completed[0]["status"] == "saved"
    assert completed[0]["duration_seconds"] == 30.0
    assert completed[0]["action"] == "BOOK"


def test_detail_splits_the_log_the_way_the_console_reads_it(client):
    body = client.get(f"/api/calls/{CALL}").json()
    assert [t["text"] for t in body["transcript"]] == ["Clínica Arenal."]
    assert [t["name"] for t in body["tools"]] == ["search_availability", "record_booking"]
    assert [w["kind"] for w in body["writes"]] == ["local_write"]
    assert body["audio"] is None
    # Voice-layer chatter stays out of the timeline the screens project.
    assert not [e for e in body["events"] if e["kind"] == "codex"]
    assert all("_line" in e for e in body["events"])


def test_provenance_ties_a_saved_write_back_to_its_lookup(client):
    chain = client.get(f"/api/calls/{CALL}").json()["provenance"]
    assert len(chain) == 1
    assert chain[0]["action"]["action"] == "BOOK"
    assert chain[0]["lookup"]["name"] == "search_availability"
    assert chain[0]["recorded"]["kind"] == "action_staged"
    assert chain[0]["write"]["kind"] == "local_write"


def test_a_refused_confirmed_write_is_reported_as_write_failed(client, tmp_path):
    path = tmp_path / "calls" / f"{CALL}.jsonl"
    refused = {
        "t": 106.0,
        "kind": "tool",
        "name": "record_booking",
        "args": {"patient_id": "P01842", "confirmed": True},
        "result": {"error": "That time was just booked."},
    }
    unconfirmed = {**refused, "args": {"patient_id": "P01842"}, "result": {"error": "Ask first."}}
    lines = [*LINES[:5], unconfirmed, refused, LINES[-1]]
    path.write_text("".join(json.dumps(line) + "\n" for line in lines))
    body = client.get(f"/api/calls/{CALL}").json()
    assert body["summary"]["status"] == "write failed"
    assert body["warnings"] == ["write failed: That time was just booked."]
    assert body["writes"] == [] and body["provenance"] == []


def test_a_call_that_saved_nothing_shows_its_logged_outcome(client, tmp_path):
    path = tmp_path / "calls" / f"{CALL}.jsonl"
    ended = {"t": 111.0, "kind": "call_ended", "actions": [{"action": "NO_ACTION", "reason": "x"}]}
    path.write_text("".join(json.dumps(line) + "\n" for line in [*LINES[:5], ended]))
    summary = client.get(f"/api/calls/{CALL}").json()["summary"]
    assert (summary["status"], summary["action"]) == ("ended", "NO_ACTION")


def test_caller_id_names_the_one_chart_from_the_clinic_directory(client):
    assert client.get(f"/api/calls/{CALL}").json()["caller_id"] is None  # nobody on file
    chart = {
        "patient_id": "P01842",
        "given_name": "Rosa",
        "first_surname": "Gil",
        "second_surname": "Pardo",
        "national_id": "12345678Z",
        "phone": "600000000",
    }
    with LocalStore().connect() as db:
        db.execute(
            "INSERT INTO patients VALUES (?, ?, ?)", ("P01842", "12345678Z", json.dumps(chart))
        )
    assert client.get(f"/api/calls/{CALL}").json()["caller_id"] == {
        "patient_id": "P01842",
        "name": "Rosa Gil Pardo",
        "source": "caller_id",
    }


def test_unknown_call_and_traversal_are_404(client):
    assert client.get("/api/calls/nope").status_code == 404
    assert client.get("/api/calls/nope/audio").status_code == 404
    assert client.get("/api/calls/..%2F..%2Fetc%2Fpasswd").status_code == 404
