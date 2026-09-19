"""Doctor and site name resolution for misheard voice transcripts."""

import asyncio

import pytest
from app import clinic, config
from app.prompt import RULES
from app.session import CallSession
from app.tools import TOOLS, call_tool

CATALOGUE = {
    "providers": [
        {"id": "PR01", "name": "Dra. Carmen Ortiz Vidal"},
        {"id": "PR02", "name": "Dr. Pablo Requena"},
        {"id": "PR03", "name": "Dr. Martín Sáez", "specialty_name": "General Practice"},
        {"id": "PR04", "name": "Dra. Marta Sáenz", "specialty_name": "Paediatrics"},
        {"id": "PR05", "name": "Dra. Elena Iglesias"},
        {"id": "PR06", "name": "Dr. Emilio Iglesia"},
        {"id": "PR07", "name": "Dra. Laura Benítez Roca"},
        {"id": "PR08", "name": "Dr. Javier Ocaña"},
    ],
    "locations": [
        {"id": "centro", "name": "Arenal Centro"},
        {"id": "norte", "name": "Arenal Norte"},
        {"id": "sur", "name": "Arenal Sur"},
    ],
}


@pytest.fixture(autouse=True)
def setup(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "CALLS_DIR", tmp_path)
    monkeypatch.setattr(clinic, "_catalogue", CATALOGUE)


def resolve(**args) -> dict:
    session = CallSession(call_id="00000000-0000-0000-0000-0000000000nn")
    return asyncio.run(call_tool(session, "resolve_names", args))


@pytest.mark.parametrize(
    ("heard", "provider_id"),
    [("Benitez Roca", "PR07"), ("Nort", "norte")],
)
def test_clear_fragment_resolves_confidently_and_returns_the_tool_id(heard, provider_id):
    args = {"doctor": heard} if provider_id.startswith("PR") else {"site": heard}
    group = resolve(**args)["doctor" if "doctor" in args else "site"]
    assert group["confident"] is True
    assert group["selected_id"] == provider_id
    assert group["provider_id" if "doctor" in args else "location_id"] == provider_id


@pytest.mark.parametrize(
    ("heard", "expected_ids"),
    [
        ("Oca Benitez Ro", {"PR07", "PR08"}),
        ("Saez", {"PR03", "PR04"}),
        ("Iglesia", {"PR05", "PR06"}),
    ],
)
def test_close_doctor_names_are_ambiguous_and_tell_the_brain_to_ask(heard, expected_ids):
    group = resolve(doctor=heard)["doctor"]
    assert group["confident"] is False
    assert "Did you mean" in group["question"]
    assert " or " in group["question"]
    assert {match["id"] for match in group["matches"][:2]} == expected_ids
    assert group["instruction"].endswith("do not guess.")


def test_a_shared_site_fragment_lists_all_sites_in_the_question():
    group = resolve(site="Arenal")["site"]
    assert group["confident"] is False
    assert group["question"] == "Did you mean Arenal Centro, Arenal Norte or Arenal Sur?"


def test_tool_can_resolve_doctor_and_site_in_one_call():
    result = resolve(doctor="Benitez Roca", site="Nort")
    assert result["doctor"]["provider_id"] == "PR07"
    assert result["site"]["location_id"] == "norte"


def test_tool_is_exposed_and_prompt_requires_confirmation_and_site_constraint():
    spec = next(tool for tool in TOOLS if tool["name"] == "resolve_names")
    assert set(spec["parameters"]["properties"]) == {"doctor", "site"}
    assert "confident" in spec["description"]
    assert "resolve_names first" in RULES
    assert "pass its resolved id as `location_id`" in RULES
    assert "Arenal Norte, Centro or Sur?" in RULES
    assert "must still match the slot's `location_id`" in RULES


def test_a_word_shared_by_every_site_does_not_hide_the_one_the_caller_named():
    # 3c61ec1c: the brain's input was cut at "...my usual clinic, Arenal"; a half-heard "Arenal Nort"
    # must still resolve, while "Arenal" alone must still ask which site.
    for heard in ("Arenal Nort", "Arenal Norte", "the Arenal Norte clinic"):
        group = resolve(site=heard)["site"]
        assert group["confident"] is True, heard
        assert group["location_id"] == "norte", heard
    assert resolve(site="Arenal")["site"]["confident"] is False


def test_lookalike_doctors_are_told_apart_by_specialty():
    # "Dr. Sáez, the GP": the question names what differs, and the brain may skip it when the
    # caller already said the specialty.
    group = resolve(doctor="Saez")["doctor"]
    assert group["confident"] is False
    assert group["question"] == (
        "Did you mean Dr. Martín Sáez, general practice, or Dra. Marta Sáenz, paediatrics?"
    )
    assert {m["specialty"] for m in group["matches"]} == {"General Practice", "Paediatrics"}
    assert "already said which specialty" in group["instruction"]
