import json
from pathlib import Path

import app.demo.events as events


def write_rows(path: Path, rows: list[dict]) -> None:
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")


def test_projector_replays_safe_tool_lifecycle(tmp_path, monkeypatch):
    monkeypatch.setattr(events.config, "CALLS_DIR", tmp_path)
    session_id = "11111111-1111-1111-1111-111111111111"
    write_rows(
        tmp_path / f"{session_id}.jsonl",
        [
            {"t": 1, "kind": "codex", "event": "delegation.created", "detail": "{}"},
            {
                "t": 2,
                "kind": "codex",
                "event": "item/started",
                "detail": json.dumps({"item": {"type": "dynamicToolCall", "tool": "search_availability", "arguments": {"national_id": "SECRET"}}}),
            },
            {
                "t": 3,
                "kind": "tool",
                "name": "search_availability",
                "args": {"national_id": "SECRET"},
                "result": {"slots_found": 4, "earliest_slots": [{"patient_id": "SECRET"}]},
            },
            {"t": 4, "kind": "action_staged", "action": {"action": "BOOK", "patient_id": "SECRET"}},
        ],
    )

    projected, cursor = events.read_projected(session_id)

    assert cursor == 4
    assert [event["type"] for event in projected] == [
        "delegation.started",
        "tool.started",
        "tool.completed",
        "action.staged",
    ]
    encoded = json.dumps(projected)
    assert "SECRET" not in encoded
    assert projected[2]["summary"] == "Found 4 eligible appointment times"


def test_projector_resumes_after_jsonl_line_id(tmp_path, monkeypatch):
    monkeypatch.setattr(events.config, "CALLS_DIR", tmp_path)
    session_id = "22222222-2222-2222-2222-222222222222"
    write_rows(
        tmp_path / f"{session_id}.jsonl",
        [
            {"t": 1, "kind": "transcript", "role": "user", "text": "hello"},
            {"t": 2, "kind": "transcript", "role": "agent", "text": "hi"},
        ],
    )

    projected, cursor = events.read_projected(session_id, after=1)

    assert cursor == 2
    assert projected == [
        {
            "id": 2,
            "at": 2,
            "type": "conversation.agent",
            "participant": "ai",
            "label": "AI receptionist",
            "summary": "hi",
            "status": "complete",
            "details": {
                "event": "conversation.agent",
                "source": "ai",
                "recorded_at": 2,
            },
        }
    ]
