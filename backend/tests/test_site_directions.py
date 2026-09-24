"""Nearest-site regressions: grounded travel help must leave booking available.

Routing and clinic HTTP responses are mocked; the real tool dispatch, site ranking,
lookup state, slot validation and booking staging run end to end.
"""

import asyncio
import json
from copy import deepcopy
from datetime import datetime
from pathlib import Path

import httpx
import pytest
from app import clinic, config
from app.session import CallSession
from app.tools import call_tool
from integrations import local_clinic

NOW = datetime(2026, 9, 19, 9, 0, tzinfo=config.TZ)
PATIENT = {
    "patient_id": "P00001",
    "given_name": "Josefa",
    "first_surname": "Domínguez",
    "second_surname": "Navarro",
    "national_id": "48064716Y",
    "date_of_birth": "2001-09-19",
    "phone": "711330529",
    "has_visited_before": True,
    "insurer": "mapfre",
    "referrals": [],
    "note": "",
}
ROUTE = {
    "code": "Ok",
    "routes": [
        {
            "distance": 12500,
            "duration": 1080,
            "legs": [
                {
                    "steps": [
                        {
                            "name": "Calle de la Estación",
                            "distance": 300,
                            "duration": 45,
                            "maneuver": {"type": "depart", "modifier": "straight"},
                        },
                        {
                            "name": "",
                            "ref": "M-50",
                            "distance": 11500,
                            "duration": 960,
                            "maneuver": {"type": "on ramp", "modifier": "right"},
                        },
                        {
                            "name": "Avenida de las Ciudades",
                            "distance": 700,
                            "duration": 75,
                            "maneuver": {"type": "turn", "modifier": "left"},
                        },
                        {
                            "name": "Avenida de las Ciudades",
                            "distance": 0,
                            "duration": 0,
                            "maneuver": {"type": "arrive", "modifier": "right"},
                        },
                    ]
                }
            ],
        }
    ],
}


@pytest.fixture(autouse=True)
def catalogue(monkeypatch, tmp_path):
    cat = json.loads(Path("seed/catalogue.json").read_text())
    monkeypatch.setattr(clinic, "_catalogue", cat)
    monkeypatch.setattr(config, "CALLS_DIR", tmp_path)
    return cat


def mock_routing(monkeypatch, handler):
    original = httpx.AsyncClient
    requests = []

    def respond(request):
        requests.append(request)
        return handler(request)

    monkeypatch.setattr(
        httpx,
        "AsyncClient",
        lambda *args, **kwargs: original(*args, **kwargs, transport=httpx.MockTransport(respond)),
    )
    return requests


def directions(session, **overrides):
    return call_tool(
        session,
        "get_site_directions",
        {
            "latitude": 40.283,
            "longitude": -3.8,
            "location_id": "sur",
            **overrides,
        },
    )


@pytest.mark.parametrize(
    ("latitude", "longitude", "specialty", "site", "provider", "appointment_type", "start"),
    [
        (
            40.283,
            -3.8,
            "physiotherapy",
            "sur",
            "PR09",
            "physio_session",
            "2026-09-21T10:00:00+02:00",
        ),
        (
            40.283,
            -3.8,
            "orthopaedics",
            "sur",
            "PR10",
            "orthopaedic_review",
            "2026-09-21T09:00:00+02:00",
        ),
        (
            40.474,
            -3.641,
            "orthopaedics",
            "norte",
            "PR10",
            "orthopaedic_review",
            "2026-09-25T10:00:00+02:00",
        ),
    ],
    ids=["fuenlabrada-physio", "fuenlabrada-orthopaedics", "hortaleza-orthopaedics"],
)
def test_failed_origins_get_route_then_book_looked_up_slot(
    monkeypatch,
    catalogue,
    latitude,
    longitude,
    specialty,
    site,
    provider,
    appointment_type,
    start,
):
    requests = mock_routing(monkeypatch, lambda request: httpx.Response(200, json=ROUTE))
    slot = {
        "provider_id": provider,
        "provider_name": provider,
        "specialty_id": specialty,
        "location_id": site,
        "appointment_type_id": appointment_type,
        "start_time": start,
        "payable_with": ["mapfre"],
    }

    class ClinicAPI:
        async def directory(self, **query):
            assert query == {"national_id": PATIENT["national_id"]}
            return [dict(PATIENT)]

        async def availability(self, date_from, date_to, **filters):
            assert filters["specialty_id"] == specialty
            assert filters["location_id"] == site
            assert filters["patient_id"] == PATIENT["patient_id"]
            return {
                "slots": [slot],
                "blocked": [],
                "appointment_type": {"id": appointment_type, "name": "Review", "guidance": ""},
            }

    monkeypatch.setattr(local_clinic, "client", lambda *_, **__: ClinicAPI())
    session = CallSession(call_id=f"nearest-{specialty}-{site}", started_at=NOW)

    async def run():
        patient = await call_tool(session, "find_patient", {"national_id": PATIENT["national_id"]})
        assert patient["count"] == 1
        ranked = await call_tool(
            session,
            "rank_sites_by_distance",
            {
                "latitude": latitude,
                "longitude": longitude,
                "specialty_id": specialty,
            },
        )
        assert ranked["sites"][0]["location_id"] == site
        found = await call_tool(
            session,
            "search_availability",
            {
                "specialty_id": specialty,
                "location_id": site,
                "patient_id": PATIENT["patient_id"],
                "date_from": "2026-09-20",
                "date_to": "2026-10-02",
            },
        )
        offered = found["earliest_slots"][0]
        route = await directions(session, latitude=latitude, longitude=longitude, location_id=site)
        assert route["route_available"] is True
        assert route["mode"] == "driving"
        assert route["origin_is_approximate"] is True
        assert route["distance_km"] == 12.5
        assert route["duration_minutes"] == 18
        assert "M-50" in route["roads"]
        assert "Avenida de las Ciudades" in route["roads"]
        assert session.actions == []
        recorded = await call_tool(
            session,
            "record_booking",
            {
                "patient_id": PATIENT["patient_id"],
                "provider_id": offered["provider_id"],
                "location_id": offered["location_id"],
                "appointment_type_id": offered["appointment_type_id"],
                "slot": offered["slot"],
                "policy_id": "mapfre",
            },
        )
        assert recorded["recorded"]["action"] == "BOOK"
        assert session.actions == [recorded["recorded"]]
        return route

    route = asyncio.run(run())
    destination = next(loc for loc in catalogue["locations"] if loc["id"] == site)
    assert route["destination_address"] == destination["address"]
    assert len(requests) == 1
    assert requests[0].url.path.endswith(
        f"/route/v1/driving/{longitude},{latitude};{destination['longitude']},{destination['latitude']}"
    )
    assert requests[0].url.params["steps"] == "true"
    assert requests[0].url.params["overview"] == "false"
    # Explicit mode and limits prevent car estimates becoming claims about a metro,
    # walking route, or an undocumented building entrance/floor.
    limitations = route["limitation"].lower()
    assert "traffic" in limitations
    assert "transit" in limitations or "public transport" in limitations
    assert "walk" in limitations
    assert "entrance" in limitations and "floor" in limitations


@pytest.mark.parametrize(
    "overrides",
    [
        {"latitude": float("nan")},
        {"longitude": float("inf")},
        {"latitude": 91},
        {"longitude": -181},
        {"latitude": True},
        {"longitude": "Madrid"},
        {"location_id": "invented"},
    ],
)
def test_invalid_origin_or_unknown_site_never_reaches_network(monkeypatch, overrides):
    requests = mock_routing(monkeypatch, lambda request: pytest.fail("Unexpected network request"))
    result = asyncio.run(directions(CallSession(call_id="invalid-route"), **overrides))
    assert "error" in result
    assert requests == []


@pytest.mark.parametrize("failure", ["timeout", "http", "no_route", "bad_json", "bad_shape"])
def test_route_failure_retains_catalogue_address_and_existing_booking(
    monkeypatch, catalogue, failure
):
    def response(request):
        if failure == "timeout":
            raise httpx.ReadTimeout("Route service timed out", request=request)
        if failure == "http":
            return httpx.Response(503)
        if failure == "no_route":
            return httpx.Response(200, json={"code": "NoRoute", "routes": []})
        if failure == "bad_shape":
            return httpx.Response(200, json=["unexpected response"])
        return httpx.Response(200, text="not JSON")

    requests = mock_routing(monkeypatch, response)
    session = CallSession(call_id=f"route-{failure}", started_at=NOW)
    session.stage({"action": "BOOK", "patient_id": "P00001", "slot": "confirmed"})
    before = deepcopy(session.actions)
    result = asyncio.run(directions(session))
    assert result["route_available"] is False
    assert result["destination_address"] == catalogue["locations"][2]["address"]
    assert result["directions_url"].startswith("https://")
    assert "distance_km" not in result and "duration_minutes" not in result
    assert session.actions == before
    assert len(requests) == 1
