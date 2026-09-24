"""Keep this package's tests inside this package.

The repo-root checkout is on `sys.path` for everything using the root venv (hack-kit is
installed editable), so a module missing from this copy — `scripts.call_ledger`, say —
would silently import the root's and the suite would test code this package does not ship.
Drop the root so a missing module fails loudly instead.
"""

import sys
from pathlib import Path

PACKAGE = Path(__file__).resolve().parents[1]
ROOT = PACKAGE.parent

sys.path[:] = [p for p in sys.path if p and Path(p).resolve() != ROOT]
if str(PACKAGE) not in sys.path:
    sys.path.insert(0, str(PACKAGE))


import pytest  # noqa: E402


@pytest.fixture(autouse=True)
def _private_clinic_db(tmp_path, monkeypatch):
    """Every test gets its own empty clinic database and no cached catalogue, so nothing
    reads or writes backend/data/clinic.sqlite3 or leaks a catalogue into the next test."""
    from app import clinic

    monkeypatch.setenv("LOCAL_CLINIC_DB", str(tmp_path / "clinic-db" / "clinic.sqlite3"))
    monkeypatch.setattr(clinic, "_catalogue", None)
    monkeypatch.setattr(clinic, "_built", None)
    monkeypatch.setattr(clinic, "_built_key", None)
