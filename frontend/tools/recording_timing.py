"""Audio-derived replay positions. JSONL publication timestamps remain unchanged."""

import math
import statistics
import subprocess
import sys
from array import array

RATE = 8000
FRAME = 160
AUDIBLE_RMS = 200
MERGE_S = 0.4
MIN_TURN_S = 0.15


def frame_levels(samples):
    """20 ms stereo RMS, removing correlated leakage from the quieter channel."""
    caller, agent = [], []
    for start in range(0, len(samples) - 2 * FRAME + 1, 2 * FRAME):
        left = right = cross = 0
        for i in range(start, start + 2 * FRAME, 2):
            a, b = samples[i], samples[i + 1]
            left += a * a
            right += b * b
            cross += a * b
        # Lossy stereo can put a quiet copy of caller speech in the agent lane.
        # Remove only the component correlated with the louder channel.
        if left > right:
            right = max(0, right - cross * cross / left)
        elif right:
            left = max(0, left - cross * cross / right)
        caller.append(math.sqrt(left / FRAME))
        agent.append(math.sqrt(right / FRAME))
    return caller, agent


def speech_intervals(levels, threshold):
    """Use the recorder's 400 ms gap merge and 150 ms click rejection."""
    intervals = []
    for i, level in enumerate(levels):
        if level <= threshold:
            continue
        start, end = i * FRAME / RATE, (i + 1) * FRAME / RATE
        if intervals and start - intervals[-1][1] <= MERGE_S:
            intervals[-1][1] = end
        else:
            intervals.append([start, end])
    return [(start, end) for start, end in intervals if end - start >= MIN_TURN_S]


def align_transcripts(samples, events, origin):
    caller, agent = frame_levels(samples)
    audio_report = next((e for e in reversed(events) if e["kind"] == "audio.timeline"), {})
    noise_dbfs = audio_report.get("caller", {}).get("noise_dbfs")
    if isinstance(noise_dbfs, (int, float)) and math.isfinite(noise_dbfs):
        floor = 32768 * 10 ** (noise_dbfs / 20)
    else:
        listening = [level for level, other in zip(caller, agent, strict=True) if other > AUDIBLE_RMS]
        if not listening:
            last = next((i for i in range(len(caller) - 1, -1, -1) if caller[i] > 0), -1)
            listening = sorted(caller[:last + 1])[:max(1, (last + 1) // 5)]
        floor = statistics.median(listening) if listening else 0
    spans = {
        "user": speech_intervals(caller, max(AUDIBLE_RMS, 2 * floor)),
        "agent": speech_intervals(agent, AUDIBLE_RMS),
    }
    ends = {}
    previous = {"user": -1, "agent": -1}
    previous_role = None
    fragment_start = 0
    for event in events:
        if event["kind"] != "transcript" or not event.get("text", "").strip():
            continue
        role = event.get("role")
        if role not in spans:
            continue
        logged = event["t"] - origin
        if role != previous_role:
            fragment_start = logged
        candidate = next(((start, end) for start, end in reversed(spans[role])
                          if start <= logged and (previous[role] < end or (
                              previous_role == role and start <= fragment_start < end
                          ))), None)
        previous_role = role
        if candidate is None:
            continue
        # A completed transcript may arrive while its audio is still playing.
        # Use the complete speech interval, not a truncation at the log timestamp.
        _, end = candidate
        if end > previous[role]:
            fragment_start = logged
        ends[str(event["_line"])] = round(end, 3)
        previous[role] = end
    return ends


def transcript_ends(path, events, origin):
    result = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(path), "-ar", str(RATE), "-ac", "2",
         "-f", "s16le", "pipe:1"], capture_output=True,
    )
    if result.returncode:
        raise RuntimeError(f"Could not decode speech timing for {path.name}: {result.stderr.decode().strip()}")
    samples = array("h")
    samples.frombytes(result.stdout)
    if sys.byteorder != "little":
        samples.byteswap()
    return align_transcripts(samples, events, origin)
