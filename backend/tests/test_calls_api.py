import json
from unittest.mock import AsyncMock

import pytest
from app import calls_api, config, prosper
from app.dashboard import app
from fastapi.testclient import TestClient

CALL = "00000000-0000-5000-8000-000000000001"

LINES = [
    {"t": 100.0, "kind": "call_started", "from_number": "+34600000000"},
    {"t": 101.0, "kind": "caller_id_lookup", "matches": ["P01842"]},
    {"t": 102.0, "kind": "transcript", "role": "agent", "text": "Clínica Arenal."},
    {"t": 103.0, "kind": "codex", "event": "noise"},
    {"t": 104.0, "kind": "tool", "name": "search_availability", "args": {}, "result": {"slots": 1}},
    {
        "t": 105.0,
        "kind": "action_staged",
        "action": {"action": "BOOK", "patient_id": "P01842"},
        "all_staged": [{"action": "BOOK", "patient_id": "P01842"}],
    },
    {
        "t": 110.0,
        "kind": "submit",
        "action": {"action": "BOOK", "patient_id": "P01842"},
        "status": 200,
        "response": {"ok": True},
    },
    {"t": 111.0, "kind": "call_ended", "submitted": [200]},
]


@pytest.fixture
def client(tmp_path, monkeypatch):
    calls_api._caller_names.clear()
    monkeypatch.setattr(prosper, "client", lambda: AsyncMock(directory=AsyncMock(return_value=[])))
    calls = tmp_path / "calls"
    calls.mkdir(exist_ok=True)  # the autouse _tmp_calls_dir fixture may have made it
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
    assert booked["status"] == "submitted"
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
        log.write(json.dumps({**LINES[-2], "t": 240.0}) + "\n")
        log.write(json.dumps({"t": 241.0, "kind": "call_ended"}) + "\n")
    calls = client.get("/api/calls").json()["calls"]
    completed = [call for call in calls if call["call_id"] == call_id]
    assert len(completed) == 1
    assert completed[0]["status"] == "submitted"
    assert completed[0]["duration_seconds"] == 30.0
    assert completed[0]["action"] == "BOOK"

def test_local_writes_keep_call_live_until_hangup_then_report_latest_saved_action(client, tmp_path):
    path = tmp_path / "calls" / f"{CALL}.jsonl"
    lines = [
        LINES[0],
        {
            "t": 105.0,
            "kind": "local_write",
            "action": {"action": "REGISTER"},
            "result": {"patient_id": "LP001"},
        },
        {
            "t": 110.0,
            "kind": "local_write",
            "action": {"action": "BOOK", "patient_id": "LP001"},
            "result": {"appointment_id": "LA001"},
        },
    ]
    path.write_text("".join(json.dumps(line) + "\n" for line in lines))
    summary = client.get(f"/api/calls/{CALL}").json()["summary"]
    assert summary["status"] == "in progress"

    with path.open("a") as log:
        log.write(json.dumps({"t": 120.0, "kind": "stop_received"}) + "\n")
    summary = client.get(f"/api/calls/{CALL}").json()["summary"]
    assert summary["status"] == "saved locally"
    assert summary["action"] == "BOOK"

    with path.open("a") as log:
        log.write(json.dumps({
            "t": 121.0,
            "kind": "demo_outcome",
            "actions": [{"action": "CANCEL", "appointment_id": "LA001"}],
            "submitted": False,
        }) + "\n")
    summary = client.get(f"/api/calls/{CALL}").json()["summary"]
    assert summary["action"] == "BOOK"


def test_demo_proposal_without_local_write_does_not_claim_saved_outcome(client, tmp_path):
    path = tmp_path / "calls" / f"{CALL}.jsonl"
    lines = [
        LINES[0],
        LINES[5],
        {
            "t": 110.0,
            "kind": "demo_outcome",
            "actions": [{"action": "BOOK", "patient_id": "P01842"}],
            "submitted": False,
        },
        {"t": 111.0, "kind": "call_ended", "submitted": False},
    ]
    path.write_text("".join(json.dumps(line) + "\n" for line in lines))
    summary = client.get(f"/api/calls/{CALL}").json()["summary"]
    assert summary["status"] == "ended"
    assert summary["action"] == "BOOK"



def test_detail_splits_the_log_the_way_the_console_reads_it(client):
    body = client.get(f"/api/calls/{CALL}").json()
    assert [t["text"] for t in body["transcript"]] == ["Clínica Arenal."]
    assert [t["name"] for t in body["tools"]] == ["search_availability"]
    assert len(body["submissions"]) == 1
    assert body["audio"] is None
    # Voice-layer chatter stays out of the timeline the screens project.
    assert not [e for e in body["events"] if e["kind"] == "codex"]
    assert all("_line" in e for e in body["events"])


def test_provenance_ties_a_submit_back_to_its_lookup(client):
    chain = client.get(f"/api/calls/{CALL}").json()["provenance"]
    assert len(chain) == 1
    assert chain[0]["action"]["action"] == "BOOK"
    assert chain[0]["lookup"]["name"] == "search_availability"
    assert chain[0]["recorded"]["kind"] == "action_staged"


def test_a_rejected_submit_is_not_reported_as_submitted(client, tmp_path):
    path = tmp_path / "calls" / f"{CALL}.jsonl"
    lines = [*LINES[:-2], {**LINES[-2], "status": 404}, LINES[-1]]
    path.write_text("".join(json.dumps(line) + "\n" for line in lines))
    body = client.get(f"/api/calls/{CALL}").json()
    assert body["summary"]["status"] == "rejected"
    assert "submit rejected: HTTP 404" in body["warnings"]


def test_unknown_call_and_traversal_are_404(client):
    assert client.get("/api/calls/nope").status_code == 404
    assert client.get("/api/calls/nope/audio").status_code == 404
    assert client.get("/api/calls/..%2F..%2Fetc%2Fpasswd").status_code == 404


def test_the_api_never_serves_a_raw_caller_number(client, tmp_path):
    """The console masks in the UI, but the full number must not leave the server."""
    path = tmp_path / "calls" / f"{CALL}.jsonl"
    path.write_text("".join(json.dumps(line) + "\n" for line in LINES))
    body = client.get(f"/api/calls/{CALL}").json()
    started = next(e for e in body["events"] if e["kind"] == "call_started")
    assert started["from_number"] == "+3···000"
    assert "+34600000000" not in json.dumps(body)
def test_caller_name_resolves_exact_logged_phone_match_and_is_cached(client, monkeypatch):
    directory = AsyncMock(return_value=[{
        "patient_id": "P01842", "given_name": "Ana",
        "first_surname": "García", "second_surname": "López",
    }])
    monkeypatch.setattr(prosper, "client", lambda: AsyncMock(directory=directory))
    body = client.get(f"/api/calls/{CALL}").json()
    assert body["caller_id"] == {
        "patient_id": "P01842", "name": "Ana García López", "source": "caller_id",
    }
    # The display fallback neither invents a lookup event nor changes the transcript.
    assert [e["kind"] for e in body["events"]] == [
        e["kind"] for e in LINES if e["kind"] != "codex"
    ]
    assert client.get(f"/api/calls/{CALL}").json()["caller_id"] == body["caller_id"]
    directory.assert_awaited_once_with(phone="+34600000000")


@pytest.mark.parametrize("patients", [[], [{"patient_id": "another", "given_name": "Ana"}], [
    {"patient_id": "P01842", "given_name": "Ana"}, {"patient_id": "another", "given_name": "Juan"},
]])
def test_changed_or_ambiguous_directory_match_does_not_supply_a_name(client, monkeypatch, patients):
    monkeypatch.setattr(prosper, "client", lambda: AsyncMock(directory=AsyncMock(return_value=patients)))
    assert client.get(f"/api/calls/{CALL}").json()["caller_id"] is None


@pytest.mark.parametrize("matches", [[], ["P01842", "P00001"]])
def test_no_unique_logged_match_skips_directory_lookup(client, tmp_path, monkeypatch, matches):
    directory = AsyncMock()
    monkeypatch.setattr(prosper, "client", lambda: AsyncMock(directory=directory))
    lines = [LINES[0], {**LINES[1], "matches": matches}, LINES[-1]]
    (tmp_path / "calls" / f"{CALL}.jsonl").write_text("\n".join(map(json.dumps, lines)))
    assert client.get(f"/api/calls/{CALL}").json()["caller_id"] is None
    directory.assert_not_awaited()


@pytest.mark.parametrize("error", [TimeoutError(), prosper.ProsperError(503, "Unavailable")])
def test_directory_failure_keeps_recording_and_transcript_available(client, monkeypatch, error):
    monkeypatch.setattr(prosper, "client", lambda: AsyncMock(directory=AsyncMock(side_effect=error)))
    response = client.get(f"/api/calls/{CALL}")
    assert response.status_code == 200
    assert response.json()["caller_id"] is None
    assert response.json()["transcript"][0]["text"] == "Clínica Arenal."
