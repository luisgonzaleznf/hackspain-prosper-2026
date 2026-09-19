"""EVAL_MODE pins a call's "now" to the published case's reference_time; the real line never does."""

from datetime import datetime

from app import config, server


def test_ignored_outside_eval_mode(monkeypatch):
    monkeypatch.setattr(config, "EVAL_MODE", False)
    assert server._eval_reference_time({"eval_reference_time": "2026-09-18T09:00:00+02:00"}) is None


def test_pinned_in_eval_mode(monkeypatch):
    monkeypatch.setattr(config, "EVAL_MODE", True)
    got = server._eval_reference_time({"eval_reference_time": "2026-09-18T09:00:00+02:00"})
    assert got == datetime(2026, 9, 18, 9, 0, tzinfo=config.TZ)
    assert got.tzinfo is not None


def test_missing_or_bad_value_falls_back_to_real_clock(monkeypatch):
    monkeypatch.setattr(config, "EVAL_MODE", True)
    assert server._eval_reference_time({}) is None
    assert server._eval_reference_time({"eval_reference_time": "not a date"}) is None
