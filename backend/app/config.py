"""Runtime settings, read once from the environment.

The `.env` is found by walking up from the working directory, so a git worktree under
`.claude/worktrees/` uses the main checkout's `.env` without a copy.
"""

import os
from pathlib import Path
from zoneinfo import ZoneInfo

from dotenv import find_dotenv, load_dotenv

load_dotenv(find_dotenv(usecwd=True))

VOICE = os.getenv("VOICE", "codex")
PORT = int(os.getenv("PORT", "7860"))
CALLS_DIR = Path(os.getenv("CALLS_DIR", "logs/calls"))
# Debug only: also save the caller alone as logs/calls/<call_id>.caller.wav for `make replay-call`.
RECORD_CALLER_AUDIO = os.getenv("RECORD_CALLER_AUDIO") == "1"
# Every call's audio, both legs on one timeline (app/recorder.py). Gitignored, like every WAV.
AUDIO_DIR = Path(os.getenv("AUDIO_DIR", "logs/audio"))

# Opt in for human demos only (see appointment_email.py).
APPOINTMENT_EMAILS_ENABLED = os.getenv("APPOINTMENT_EMAILS_ENABLED") == "1"
RESEND_API_KEY = os.getenv("RESEND_API_KEY", "")
RESEND_FROM_EMAIL = os.getenv("RESEND_FROM_EMAIL", "")
CUSTOMER_DB_PATH = Path(os.getenv("CUSTOMER_DB_PATH", "logs/demo/customers.sqlite3"))

# Every date in the clinic is Europe/Madrid; "tomorrow" resolves against the call's connect time.
TZ = ZoneInfo("Europe/Madrid")
