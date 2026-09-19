import json

import pytest
from app import config
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
