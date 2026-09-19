"""Put the recordings of a Run All into ./logs/run_audio, compressed, so they can be committed.

    uv run python scripts/collect_run_audio.py --last                  # the latest Run All
    uv run python scripts/collect_run_audio.py --since 08:16 --until 08:30
    then: git add logs/run_audio && git commit

Every call is recorded as logs/audio/<call_id>.wav (about 3 MB a call, gitignored). Practice calls
and evals stay that way: they would bloat the repo. A Run All is different: its private cases are
never published, so our recording is the only way a teammate can hear why a call failed. This
copies ONLY the calls Prosper placed (version-5 call ids) inside the run's window, as Opus at
24 kbps (about 0.4 MB a call, 8 MB a run), next to the recorder's .timing.json when there is one.

Nothing else runs while a Run All is in flight (one run at a time per team), so "placed by
Prosper inside the window" is the run. `--last` takes the newest group of at least 8 such calls
with no gap over 3 minutes between starts; a 10- or 20-call Switchboard burst looks the same, so
give --since/--until when the latest group is a burst. Private repo only, never the public mirror.
"""

import argparse
import json
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from collect_calls import ROOT, checkouts, is_prosper

DEST = ROOT / "logs" / "run_audio"
AUDIO_DIRS = ("logs/audio", "logs/calls", "logs/autopilot/calls")  # where recorders write WAVs
LOG_DIRS = ("logs/calls", "logs/autopilot/calls")
MIN_CALLS = 8
MAX_GAP_SECS = 180


def recordings() -> dict[str, Path]:
    """call_id -> the largest WAV found for it in any checkout."""
    found: dict[str, Path] = {}
    for checkout in [ROOT, *checkouts()]:
        for d in AUDIO_DIRS:
            for wav in (checkout / d).glob("*.wav"):
                call_id = wav.name.split(".")[0]
                if is_prosper(call_id) and (
                    call_id not in found or wav.stat().st_size > found[call_id].stat().st_size
                ):
                    found[call_id] = wav
    return found


def started_at(call_id: str, wav: Path) -> float:
    """When the call started: the first event of its call log, else the WAV's modification time."""
    for checkout in [ROOT, *checkouts()]:
        for d in LOG_DIRS:
            log = checkout / d / f"{call_id}.jsonl"
            try:
                with log.open() as f:
                    return float(json.loads(f.readline())["t"])
            except (OSError, ValueError, KeyError, TypeError):
                continue
    return wav.stat().st_mtime


def last_run(starts: dict[str, float]) -> list[str]:
    """The newest group of >= MIN_CALLS calls whose starts are never more than MAX_GAP_SECS apart."""
    ordered = sorted(starts, key=lambda c: starts[c])
    groups: list[list[str]] = []
    for call_id in ordered:
        if groups and starts[call_id] - starts[groups[-1][-1]] <= MAX_GAP_SECS:
            groups[-1].append(call_id)
        else:
            groups.append([call_id])
    big = [g for g in groups if len(g) >= MIN_CALLS]
    return big[-1] if big else []


def clock(text: str) -> float:
    """HH:MM (today, local time) or a full ISO timestamp."""
    if len(text) <= 5:
        hour, minute = text.split(":")
        return datetime.now().replace(hour=int(hour), minute=int(minute), second=0).timestamp()
    return datetime.fromisoformat(text).timestamp()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--last", action="store_true", help="the latest Run All found on disk")
    parser.add_argument("--since", help="window start, HH:MM today or ISO")
    parser.add_argument("--until", help="window end, HH:MM today or ISO (default: now)")
    args = parser.parse_args()
    if not args.last and not args.since:
        parser.error("give --last, or --since HH:MM [--until HH:MM]")
    if not shutil.which("ffmpeg"):
        print("ffmpeg is needed to compress the recordings (brew install ffmpeg).")
        return 1

    wavs = recordings()
    starts = {call_id: started_at(call_id, wav) for call_id, wav in wavs.items()}
    if args.last:
        chosen = last_run(starts)
    else:
        lo = clock(args.since)
        hi = clock(args.until) if args.until else datetime.now().timestamp()
        chosen = sorted((c for c in starts if lo <= starts[c] <= hi), key=lambda c: starts[c])
    if not chosen:
        print("No Prosper-placed recordings in that window. Was the recorder on?")
        return 1

    run_dir = DEST / datetime.fromtimestamp(starts[chosen[0]]).strftime("%Y%m%d-%H%M")
    run_dir.mkdir(parents=True, exist_ok=True)
    total = 0
    for call_id in chosen:
        out = run_dir / f"{call_id}.opus"
        if not out.exists():
            encode = ["-c:a", "libopus", "-b:a", "24k"]
            subprocess.run(
                ["ffmpeg", "-loglevel", "error", "-y", "-i", str(wavs[call_id]), *encode, str(out)],
                check=True,
            )
        timing = wavs[call_id].with_name(f"{call_id}.timing.json")
        if timing.exists():
            shutil.copyfile(timing, run_dir / timing.name)
        total += out.stat().st_size
    first = datetime.fromtimestamp(starts[chosen[0]]).strftime("%H:%M:%S")
    final = datetime.fromtimestamp(starts[chosen[-1]]).strftime("%H:%M:%S")
    print(
        f"{len(chosen)} calls ({first} to {final}) -> {run_dir.relative_to(ROOT)} "
        f"({total / 1e6:.1f} MB). Now: git add logs/run_audio && git commit"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
