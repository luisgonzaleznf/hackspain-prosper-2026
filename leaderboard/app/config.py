"""Runtime settings, read once from the environment.

The `.env` is found by walking up from the working directory, so a git worktree under
`.claude/worktrees/` uses the main checkout's `.env` without a copy.
"""

import os
from pathlib import Path
from zoneinfo import ZoneInfo

from dotenv import find_dotenv, load_dotenv

load_dotenv(find_dotenv(usecwd=True))

PLATFORM_API_KEY = os.getenv("PLATFORM_API_KEY", "")
PLATFORM_API_BASE_URL = os.getenv(
    "PLATFORM_API_BASE_URL", "https://hackspain.getprosperapp.com"
).rstrip("/")

VOICE = os.getenv("VOICE", "codex")
# Local evals only: honour the harness's `eval_reference_time` as the call's connect time, so
# published cases (anchored to their reference_time) stay comparable on any day. Prosper never
# sends it, and it is ignored unless this is set.
EVAL_MODE = os.getenv("EVAL_MODE") == "1"
PORT = int(os.getenv("PORT", "7860"))
# Call artifacts belong to the backend package, not this one.
CALLS_DIR = Path(os.getenv("CALLS_DIR", "../backend/logs/calls"))
# Debug only: also save the caller alone as logs/calls/<call_id>.caller.wav for `make replay-call`.
RECORD_CALLER_AUDIO = os.getenv("RECORD_CALLER_AUDIO") == "1"
# Every call's audio, both legs on one timeline (app/recorder.py). Gitignored, like every WAV.
AUDIO_DIR = Path(os.getenv("AUDIO_DIR", "../backend/logs/audio"))

# Every date in the clinic is Europe/Madrid; "tomorrow" resolves against the call's connect time.
TZ = ZoneInfo("Europe/Madrid")
