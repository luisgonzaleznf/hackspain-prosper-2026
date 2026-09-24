import asyncio
import json
from pathlib import Path

import pytest
from app import clinic, config
from app.prompt import RULES
from app.session import CallSession
from app.tools import TOOLS, call_tool


@pytest.fixture
def catalogue(monkeypatch, tmp_path):
    cat = json.loads(Path("seed/catalogue.json").read_text())
    monkeypatch.setattr(clinic, "_catalogue", cat)
    monkeypatch.setattr(config, "CALLS_DIR", tmp_path)
    return cat


@pytest.mark.parametrize(
    ("specialty", "winner"), [("general_practice", "sur"), ("gynaecology", "centro")]
)
def test_nearest_site_must_offer_specialty(catalogue, specialty, winner):
    result = asyncio.run(
        call_tool(
            CallSession(call_id="nearest"),
            "rank_sites_by_distance",
            {
                "latitude": 40.305,
                "longitude": -3.7327,
                "specialty_id": specialty,
            },
        )
    )
    assert result["sites"][0]["location_id"] == winner
    if specialty == "general_practice":
        assert result["sites"][0]["distance_km"] == 0
        assert [s["location_id"] for s in result["sites"]] == ["sur", "centro", "norte"]
    assert "Check real availability and coverage" in result["note"]


@pytest.mark.parametrize("latitude", [float("nan"), 91, "Puerta del Sol", True])
def test_invalid_coordinates_are_not_guessed(catalogue, latitude):
    result = asyncio.run(
        call_tool(
            CallSession(call_id="invalid-origin"),
            "rank_sites_by_distance",
            {
                "latitude": latitude,
                "longitude": -3.7,
                "specialty_id": "general_practice",
            },
        )
    )
    assert "error" in result


def test_catalogue_exposes_source_coordinates(catalogue):
    rendered = clinic.render_catalogue(catalogue)
    for site in catalogue["locations"]:
        assert f"Coordinates: {site['latitude']}, {site['longitude']}" in rendered


@pytest.mark.parametrize(
    ("latitude", "longitude", "specialty", "winner"),
    [
        (40.417, -3.703, "general_practice", "centro"),  # Puerta del Sol
        (40.466, -3.689, "orthopaedics", "norte"),  # Plaza de Castilla
        (40.308, -3.733, "general_practice", "sur"),  # Calle de Madrid, Getafe
        (40.308, -3.733, "gynaecology", "centro"),
    ],
)
def test_approximate_landmarks_rank_nearest_capable_site(
    catalogue, latitude, longitude, specialty, winner
):
    result = asyncio.run(
        call_tool(
            CallSession(call_id="approximate-origin"),
            "rank_sites_by_distance",
            {"latitude": latitude, "longitude": longitude, "specialty_id": specialty},
        )
    )
    assert result["sites"][0]["location_id"] == winner
    if specialty == "gynaecology":
        assert [site["location_id"] for site in result["sites"]] == ["centro"]


def test_estimated_origins_do_not_require_caller_coordinates():
    assert "Estimate the caller's approximate coordinates from your knowledge of Madrid" in RULES
    assert "ONLY if the place named is unknown or ambiguous" in RULES
    assert "Use a landmark already supplied rather than asking for it again" in RULES
    assert "never claim a measured" in RULES
    spec = next(tool for tool in TOOLS if tool["name"] == "rank_sites_by_distance")
    assert "coordinates you estimate" in spec["description"]
    assert "Never ask the caller for numeric coordinates" in spec["description"]
