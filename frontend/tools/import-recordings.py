#!/usr/bin/env python3
"""Import the private repository's call logs and Opus recordings at one immutable revision."""

import argparse
import hashlib
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
from datetime import datetime, timezone
from fractions import Fraction

from recording_timing import transcript_ends

REPOSITORY = "luisgonzaleznf/hackspain-prosper-2026-private"
REVISION = "60de9119c3e61d90e193149886c00561d66a7856"
DATA = Path(__file__).resolve().parents[1] / ".recordings"
SNAPSHOT = "docs/private-calls/dashboard-export.json"
CALL_ID = re.compile(r"[A-Za-z0-9_-]+")


def dump(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, separators=(",", ":")) + "\n")
    os.replace(temporary, path)


def download(revision, destination):
    # gh owns authentication. Neither its token nor private download URLs are persisted.
    process = subprocess.Popen(
        ["gh", "api", f"repos/{REPOSITORY}/tarball/{revision}"], stdout=subprocess.PIPE
    )
    files = []
    try:
        with tarfile.open(fileobj=process.stdout, mode="r|gz") as archive:
            for member in archive:
                relative = PurePosixPath(*PurePosixPath(member.name).parts[1:])
                name = str(relative)
                if not member.isfile() or not (
                    name.startswith(("logs/calls/", "logs/run_audio/")) or name == SNAPSHOT
                ):
                    continue
                if relative.is_absolute() or ".." in relative.parts:
                    raise ValueError(f"Unsafe source path: {name}")
                target = destination / name
                target.parent.mkdir(parents=True, exist_ok=True)
                with archive.extractfile(member) as source, target.open("wb") as output:
                    shutil.copyfileobj(source, output)
                files.append({"path": name, "bytes": target.stat().st_size,
                              "sha256": hashlib.sha256(target.read_bytes()).hexdigest()})
        if process.wait() != 0:
            raise RuntimeError("GitHub download failed. Run gh auth status and retry the import.")
    finally:
        process.stdout.close()
        if process.poll() is None:
            process.terminate()
            process.wait()
    return files


def read_events(path):
    events = []
    for line_number, line in enumerate(path.read_text().splitlines(), 1):
        if not line.strip():
            continue
        event = json.loads(line)
        if not isinstance(event, dict) or not isinstance(event.get("kind"), str) or not finite(event.get("t")):
            raise ValueError(f"{path.name}:{line_number}: expected an event with kind and epoch timestamp")
        events.append({**event, "_line": line_number})
    return events


def finite(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def attribution(source):
    path = source / SNAPSHOT
    if not path.exists():
        return {}
    references = {}
    for run in json.loads(path.read_text())["runs"]:
        cases = run["cases"]
        mode = "practice" if run["public"] and len(cases) == 1 else "switchboard" if run["public"] else "run_all"
        for position, case in enumerate(cases, 1):
            if case.get("call_id"):
                references[case["call_id"]] = {
                    "run_id": run["run_id"], "mode": mode,
                    "problem_id": case.get("problem_id") or "", "case_id": case.get("case_id") or "",
                    "suite_position": position, "suite_total": len(cases),
                }
    return references


def audio_info(path, timing, events, warnings):
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "a:0", "-show_streams", "-of", "json", str(path)],
        capture_output=True, text=True,
    )
    if result.returncode:
        warnings.append("Recording is empty or invalid; ffprobe could not read an audio stream.")
        return None
    streams = json.loads(result.stdout).get("streams", [])
    if not streams:
        warnings.append("Recording contains no audio stream.")
        return None
    stream = streams[0]
    rate = int(stream.get("sample_rate", 0))
    channels = int(stream.get("channels", 0))
    # Opus granule duration includes encoder pre-skip. Subtract it for decoded PCM frames.
    frames = round(int(stream.get("duration_ts", 0)) * Fraction(stream.get("time_base", "0")) * rate)
    frames -= int(stream.get("initial_padding", 0))
    if stream.get("codec_name") != "opus" or rate <= 0 or channels <= 0 or frames <= 0:
        warnings.append("Recording has no playable Opus samples.")
        return None
    anchor = next((e for e in events if e["kind"] == "first_agent_audio" and finite(e.get("ms"))), None)
    origin = anchor["t"] - anchor["ms"] / 1000 if anchor else None
    if origin is None:
        warnings.append("Recording has no wall-clock anchor; transcript timestamps cannot be aligned exactly.")
    if timing is None:
        warnings.append("Recording timing file is missing.")
    inbound = timing.get("inbound_ms", []) if timing else []
    stamps = [(arrival - (stamp if stamp is not None else i * 20)) / 1000
              for i, (arrival, stamp) in enumerate(inbound)]
    drift = stamps[-1] - stamps[0] if len(stamps) > 1 else None
    return {
        "url": f"/api/calls/{path.stem}/audio", "channels": channels, "sample_rate": rate,
        "sample_width": None, "frames": frames, "duration_seconds": frames / rate,
        "timeline_clock": "wire_monotonic", "timeline_origin_at": origin,
        "caller_carrier_drift_seconds": drift,
    }


def materialize(directory, revision, files):
    source = directory / "source"
    references = attribution(source)
    logs = {path.stem: path for path in sorted((source / "logs/calls").glob("*.jsonl"))}
    recordings = {}
    runs = {}
    for path in sorted((source / "logs/run_audio").glob("*/*.opus")):
        if path.stem in recordings:
            raise ValueError(f"Call {path.stem} has recordings in multiple runs; refusing ambiguous audio.")
        recordings[path.stem] = path
        runs.setdefault(path.parent.name, []).append(path.stem)
    if not logs or not recordings:
        raise ValueError("Source must contain both logs/calls JSONL files and logs/run_audio Opus files.")
    missing_logs = sorted(recordings.keys() - logs.keys())
    if missing_logs:
        raise ValueError(f"Recordings have no matching call log: {', '.join(missing_logs)}")
    summaries, media, issues = [], {}, []
    event_count = 0
    for call_id, path in logs.items():
        if not CALL_ID.fullmatch(call_id):
            raise ValueError(f"Call ID is not safe for an API path: {call_id}")
        events = read_events(path)
        if not events:
            raise ValueError(f"{path.name}: empty call log has no source timestamp")
        event_count += len(events)
        warnings = []
        audio = None
        run = references.get(call_id)
        if call_id in recordings:
            recording = recordings[call_id]
            timing_path = recording.with_suffix(".timing.json")
            timing = json.loads(timing_path.read_text()) if timing_path.exists() else None
            audio = audio_info(recording, timing, events, warnings)
            # The collector's directory is the source attribution, not an inferred verdict.
            run = {"run_id": recording.parent.name, "mode": "recorded",
                   "problem_id": run["problem_id"] if run else "",
                   "case_id": run["case_id"] if run else "",
                   "suite_position": None, "suite_total": len(runs[recording.parent.name])}
            if audio:
                media[call_id] = str(recording.relative_to(directory))
                if audio["timeline_origin_at"] is not None and audio["channels"] == 2:
                    audio["transcript_end_seconds"] = transcript_ends(recording, events, audio["timeline_origin_at"])
        transcript = [e for e in events if e["kind"] == "transcript"]
        tools = [e for e in events if e["kind"] == "tool"]
        staged = [e for e in events if e["kind"] == "action_staged"]
        submissions = [e for e in events if e["kind"] == "submit"]
        errors = [e for e in events if e["kind"].endswith("error")]
        for event in events:
            if event["kind"] == "audio.timeline":
                warnings.extend(event.get("flags", []))
        warnings.extend(str(e.get("error", e["kind"])) for e in errors)
        first_t, last_t = min(e["t"] for e in events), max(e["t"] for e in events)
        ended = next((e for e in events if e["kind"] in ("stop_received", "socket_closed", "closed_by_agent", "call_ended")), None)
        status = f"submitted {submissions[-1]['status']}" if submissions else "ended" if ended else "incomplete"
        action = submissions[-1]["action"]["action"] if submissions else ""
        summary = {
            "call_id": call_id, "started_at": first_t, "modified_at": last_t,
            "modified_iso": datetime.fromtimestamp(last_t, timezone.utc).isoformat(),
            "status": status, "action": action,
            "duration_seconds": max(0, ended["t"] - first_t) if ended else None,
            "warnings": len(warnings), "has_audio": audio is not None, "run": run,
        }
        provenance = []
        for submit in submissions:
            recorded = next((e for e in reversed(staged) if e["_line"] < submit["_line"] and e.get("action") == submit["action"]), None)
            provenance.append({"lookup": None, "recorded": recorded, "submit": submit, "action": submit["action"]})
        detail = {
            "call_id": call_id, "summary": summary, "run": run, "warnings": warnings,
            "audio": audio, "transcript": transcript, "tools": tools, "staged_actions": staged,
            "submissions": submissions, "errors": errors, "provenance": provenance, "events": events,
        }
        dump(directory / "calls" / f"{call_id}.json", detail)
        summaries.append(summary)
        if call_id in recordings and (audio is None or audio["timeline_origin_at"] is None):
            issues.append({"call_id": call_id, "run_id": run["run_id"], "warnings": warnings})
    summaries.sort(key=lambda item: (-item["started_at"], item["call_id"]))
    dump(directory / "index.json", {"calls_dir": f"github:{REPOSITORY}@{revision}/logs/calls", "calls": summaries})
    manifest = {
        "repository": REPOSITORY, "revision": revision,
        "counts": {"calls": len(logs), "events": event_count, "recordings": len(recordings),
                   "playable_recordings": len(media), "runs": len(runs),
                   "timing_files": sum(f["path"].endswith(".timing.json") for f in files)},
        "runs": {run: {"recordings": len(ids), "playable_recordings": sum(cid in media for cid in ids), "call_ids": ids}
                 for run, ids in runs.items()},
        "audio_files": media, "issues": issues, "source_files": files,
    }
    dump(directory / "manifest.json", manifest)
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--revision", default=REVISION, help=f"Full commit SHA; default: {REVISION}")
    args = parser.parse_args()
    if not re.fullmatch(r"[0-9a-f]{40}", args.revision):
        parser.error("--revision must be a full 40-character commit SHA, not a mutable branch or tag")
    for binary in ("gh", "ffprobe", "ffmpeg"):
        if not shutil.which(binary):
            raise RuntimeError(f"Install {binary} before importing recordings.")
    DATA.mkdir(parents=True, exist_ok=True)
    destination = DATA / args.revision
    if destination.exists():
        cached = json.loads((destination / "manifest.json").read_text())
        manifest = materialize(destination, args.revision, cached["source_files"])
    else:
        with tempfile.TemporaryDirectory(prefix="import-", dir=DATA) as temp:
            staging = Path(temp) / "dataset"
            staging.mkdir()
            files = download(args.revision, staging / "source")
            manifest = materialize(staging, args.revision, files)
            staging.rename(destination)
    pointer = DATA / "current.tmp"
    dump(pointer, {"revision": args.revision})
    os.replace(pointer, DATA / "current.json")
    print(json.dumps({"revision": args.revision, "counts": manifest["counts"],
                      "runs": {key: value["recordings"] for key, value in manifest["runs"].items()},
                      "issues": manifest["issues"], "directory": str(destination)}, indent=2))


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, KeyError, RuntimeError, tarfile.TarError) as error:
        print(f"Recording import failed: {error}", file=sys.stderr)
        sys.exit(1)
