"""Problem 11: "the provider you book has to speak their language". search_availability's
`language` filter, from the catalogue's per-provider languages (Prosper's API has none).

Mirrors languages-aa19667cb074: a Catalan caller asks for a Catalan-speaking doctor; the
earliest orthopaedics slot is PR06 (en/es), the expected answer is PR10 (ca/es) at Norte."""

import asyncio
from datetime import datetime

import pytest
from app import clinic, config, prosper
from app.prompt import RULES
from app.session import CallSession
from app.tools import TOOLS, call_tool

NOW = datetime(2026, 9, 18, 9, 0, tzinfo=config.TZ)
CATALOGUE = {
    "providers": [
        {"id": "PR06", "name": "Dr. Emilio Iglesia", "languages": ["en", "es"]},
        {"id": "PR10", "name": "Dra. Nuria Peral", "languages": ["ca", "es"]},
    ],
    "locations": [
        {"id": "centro", "name": "Arenal Centro"},
        {"id": "norte", "name": "Arenal Norte"},
    ],
}


def slot(provider: str, site: str, start: str) -> dict:
    return {
        "provider_id": provider,
        "provider_name": provider,
        "specialty_id": "orthopaedics",
        "location_id": site,
        "appointment_type_id": "orthopaedic_review",
        "start_time": start,
        "payable_with": ["asisa"],
    }


SLOTS = [
    slot("PR06", "centro", "2026-09-22T08:45:00+02:00"),
    slot("PR10", "norte", "2026-09-25T10:45:00+02:00"),
]


class FakeProsper:
    def __init__(self, slots):
        self.slots = slots

    async def availability(self, date_from, date_to, **filters):
        return {
            "slots": list(self.slots),
            "blocked": [],
            "appointment_type": {"id": "orthopaedic_review", "name": "Review", "guidance": ""},
        }


@pytest.fixture(autouse=True)
def setup(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "CALLS_DIR", tmp_path)
    monkeypatch.setattr(clinic, "_catalogue", CATALOGUE)


def search(monkeypatch, slots=SLOTS, **extra) -> tuple[dict, CallSession]:
    monkeypatch.setattr(prosper, "client", lambda: FakeProsper(slots))
    s = CallSession(call_id="00000000-0000-0000-0000-0000000000cc", started_at=NOW)
    args = {"specialty_id": "orthopaedics", "date_from": "2026-09-19", "date_to": "2026-10-02"}
    return asyncio.run(call_tool(s, "search_availability", args | extra)), s


def test_without_a_language_the_earliest_doctor_comes_first(monkeypatch):
    r, _ = search(monkeypatch)
    assert r["earliest_slots"][0]["provider_id"] == "PR06"


def test_a_catalan_speaker_gets_only_catalan_speaking_doctors(monkeypatch):
    r, _ = search(monkeypatch, language="ca")
    assert [x["provider_id"] for x in r["earliest_slots"]] == ["PR10"]
    assert r["earliest_slots"][0]["slot"] == "2026-09-25T10:45:00+02:00"
    assert any("speak Catalan" in n for n in r["notes"])


def test_no_catalan_speaker_free_says_slots_exist_with_other_doctors(monkeypatch):
    r, s = search(monkeypatch, slots=[SLOTS[0]], language="ca")
    assert r["slots_found"] == 0
    assert any("1 slot(s) exist" in n and "Catalan" in n for n in r["notes"])
    # The window is not actually full or blocked: that would contradict the note above and
    # push the model to the wrong fallback (languages defect 2).
    assert not any("diary is simply full" in n for n in r["notes"])
    assert not any("`blocked` names the rule" in n for n in r["notes"])
    assert s.fallback() == {"action": "NO_ACTION", "reason": "no_availability"}


def test_a_truly_full_diary_still_says_so_even_with_a_language_filter(monkeypatch):
    # No slots at all, filtered or not, and nothing blocked: the diary really is full.
    r, _ = search(monkeypatch, slots=[], language="ca")
    assert r["slots_found"] == 0
    assert any("diary is simply full" in n for n in r["notes"])


@pytest.mark.parametrize("language", ["en", "es", "EN", "Es", "fr", "not-a-language", ""])
def test_english_spanish_and_junk_never_filter(monkeypatch, language):
    # Only asking for Catalan, Basque or Galician should ever narrow the doctors: everything
    # else (including the language the call happens to be in) is a no-op, not a filter that can
    # empty a search (languages defect 1: an English caller must not lose PR07-PR10).
    r, _ = search(monkeypatch, language=language)
    assert [x["provider_id"] for x in r["earliest_slots"]] == ["PR06", "PR10"]
    assert r["slots_found"] == 2


def test_a_language_no_doctor_speaks_is_not_used_to_hide_everyone(monkeypatch):
    # No provider speaks Basque or Galician: filtering would return nothing at all.
    r, _ = search(monkeypatch, language="eu")
    assert r["slots_found"] == 2
    assert any("No doctor at the clinic speaks Basque" in n for n in r["notes"])


def test_without_the_catalogue_nothing_is_filtered(monkeypatch):
    monkeypatch.setattr(clinic, "_catalogue", None)
    r, _ = search(monkeypatch, language="ca")
    assert r["slots_found"] == 2


def test_the_tool_and_the_rules_expose_the_doctor_language():
    spec = next(t for t in TOOLS if t["name"] == "search_availability")
    assert "ca" in spec["parameters"]["properties"]["language"]["enum"]
    assert "pass language on every search_availability" in RULES
    assert "Don't pass language just because the caller speaks one" in RULES


def test_identification_never_asks_for_part_of_an_id():
    # languages-5fec: asked for "the last three characters", the (LLM) caller sliced its own
    # NIE wrongly twice and hung up before the brain, which had carried on, could book.
    assert "Never ask for part of an ID" in RULES
    assert "end of their DNI/NIE" not in RULES
