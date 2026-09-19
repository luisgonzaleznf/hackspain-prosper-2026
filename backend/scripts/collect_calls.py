"""Gather every per-call log from all of this repo's checkouts into ./logs/calls, so it can be committed.

    uv run python scripts/collect_calls.py          # copy new calls, then: git add logs/calls && git commit

Each agent server writes logs/calls/<call_id>.jsonl in the checkout it runs from, so after a day of
worktrees the calls are scattered. This copies every one into the current checkout (call ids are
unique, existing files are refreshed if the source grew) and blanks two machine traces GPT-Live's
events carry: the Codex installation id and the WebRTC SDP (local IP addresses). No secrets are in
the logs; patient data is the organisers' synthetic set. Private repo only, never the public mirror.
"""

import glob
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "logs" / "calls"

_REDACT = {"installationId", "serverName", "sdp"}


def _scrub(obj):
    if isinstance(obj, dict):
        return {k: ("redacted" if k in _REDACT else _scrub(v)) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_scrub(v) for v in obj]
    if isinstance(obj, str) and obj[:1] in "{[":  # GPT-Live events nest JSON inside a string
        try:
            return json.dumps(_scrub(json.loads(obj)), ensure_ascii=False)
        except ValueError:
            return obj
    return obj


def redact(text: str) -> str:
    """Blank the machine traces field by field, keeping every line valid JSON."""
    out = []
    for line in text.splitlines():
        try:
            out.append(json.dumps(_scrub(json.loads(line)), ensure_ascii=False))
        except ValueError:
            out.append(line)  # a half-written last line of a live call: keep as is
    return "\n".join(out) + ("\n" if out else "")


def checkouts() -> list[Path]:
    out = subprocess.run(
        ["git", "-C", str(ROOT), "worktree", "list", "--porcelain"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    paths = [
        Path(line.split(" ", 1)[1]) for line in out.splitlines() if line.startswith("worktree ")
    ]
    # Orca-managed worktrees of the same repo live outside it.
    repo_name = paths[0].name if paths else ROOT.name
    paths += [Path(p) for p in glob.glob(os.path.expanduser(f"~/orca/workspaces/{repo_name}/*"))]
    return [p for p in dict.fromkeys(paths) if p.resolve() != ROOT.resolve()]


def is_prosper(call_id: str) -> bool:
    """Prosper's call ids are version-5 UUIDs; our simulators mint version-4 ones."""
    parts = call_id.split("-")
    return len(parts) == 5 and parts[2][:1] == "5"


def main() -> int:
    DEST.mkdir(parents=True, exist_ok=True)
    copied = refreshed = 0
    for checkout in checkouts():
        for src in sorted((checkout / "logs" / "calls").glob("*.jsonl")):
            dst = DEST / src.name
            text = redact(src.read_text(errors="replace"))
            if dst.exists():
                if len(dst.read_text(errors="replace")) >= len(text):
                    continue
                refreshed += 1
            else:
                copied += 1
            dst.write_text(text)
    # Redact what already sits here too (e.g. calls this checkout's own server wrote).
    for f in DEST.glob("*.jsonl"):
        f.write_text(redact(f.read_text(errors="replace")))
    ids = [f.stem for f in DEST.glob("*.jsonl")]
    prosper = sum(is_prosper(i) for i in ids)
    print(
        f"{copied} new, {refreshed} refreshed -> {DEST} now holds {len(ids)} calls "
        f"({prosper} placed by Prosper, {len(ids) - prosper} local simulations)"
    )
    bad = [i for i in ids if not _valid_jsonl(DEST / f"{i}.jsonl")]
    if bad:
        print(
            f"warning: {len(bad)} logs have unparseable lines (a call still in progress?): {bad[:5]}"
        )
    return 0


def _valid_jsonl(path: Path) -> bool:
    try:
        for line in path.read_text().splitlines():
            if line.strip():
                json.loads(line)
        return True
    except (ValueError, OSError):
        return False


if __name__ == "__main__":
    sys.exit(main())
