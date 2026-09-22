"""Keep this package's tests inside this package, and off the real call log.

The repo-root checkout is on `sys.path` for everything using the root venv (hack-kit is
installed editable), so a module missing from this copy — `scripts.call_ledger`, say —
would silently import the root's and the suite would test code this package does not ship.
Drop the root so a missing module fails loudly instead.
"""

import sys
from pathlib import Path

import pytest
from app import config as app_config

PACKAGE = Path(__file__).resolve().parents[1]
ROOT = PACKAGE.parent

sys.path[:] = [p for p in sys.path if p and Path(p).resolve() != ROOT]
if str(PACKAGE) not in sys.path:
    sys.path.insert(0, str(PACKAGE))


@pytest.fixture(autouse=True)
def _tmp_calls_dir(tmp_path, monkeypatch):
    """Tests that log through real CallSessions must not litter logs/calls/.

    config.CALLS_DIR is read inside session.log() at call time, so pointing it
    at a temp dir per test keeps the console's real data clean.
    """
    calls = tmp_path / "calls"
    calls.mkdir(exist_ok=True)  # a test fixture may have made it already
    monkeypatch.setattr(app_config, "CALLS_DIR", calls)
