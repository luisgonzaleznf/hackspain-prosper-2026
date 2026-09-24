"""Keep this package's tests inside this package, and off the real call log.

The repo-root checkout is on `sys.path` for everything using the root venv (hack-kit is
installed editable), so a module missing from this copy — `scripts.call_ledger`, say —
would silently import the root's and the suite would test code this package does not ship.
Drop the root so a missing module fails loudly instead.

Tests must not litter the console's real `logs/calls/`: an autouse fixture points
`config.CALLS_DIR` at a per-test tmp dir. It is set via a string target (not an
imported module) so this file works under `uv run pytest` (console script: the
package is on sys.path only after the block below runs).
"""

import sys
from pathlib import Path

import pytest

PACKAGE = Path(__file__).resolve().parents[1]
ROOT = PACKAGE.parent

sys.path[:] = [p for p in sys.path if p and Path(p).resolve() != ROOT]
if str(PACKAGE) not in sys.path:
    sys.path.insert(0, str(PACKAGE))


@pytest.fixture(autouse=True)
def _private_clinic_db(tmp_path, monkeypatch):
    """Every test gets its own empty clinic database and no cached catalogue, so nothing
    reads or writes backend/data/clinic.sqlite3 or leaks a catalogue into the next test."""
    from app import clinic

    monkeypatch.setenv("LOCAL_CLINIC_DB", str(tmp_path / "clinic-db" / "clinic.sqlite3"))
    monkeypatch.setattr(clinic, "_catalogue", None)
    monkeypatch.setattr(clinic, "_built", None)
    monkeypatch.setattr(clinic, "_built_key", None)


@pytest.fixture(autouse=True)
def _tmp_calls_dir(tmp_path, monkeypatch):
    """Tests that log through real CallSessions must not litter logs/calls/.

    session.log() reads config.CALLS_DIR at call time, so pointing it at a
    per-test directory keeps the console's real data clean.
    """
    calls = tmp_path / "calls"
    calls.mkdir(exist_ok=True)
    monkeypatch.setattr("app.config.CALLS_DIR", calls)
