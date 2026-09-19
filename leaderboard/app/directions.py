"""A short, live driving route from an approximate caller location to a clinic site."""

import asyncio
from math import isfinite
from urllib.parse import urlencode

import httpx


def valid_coordinates(latitude: object, longitude: object) -> bool:
    return all(
        not isinstance(value, bool)
        and isinstance(value, (int, float))
        and isfinite(value)
        and -limit <= value <= limit
        for value, limit in ((latitude, 90), (longitude, 180))
    )


async def get_site_directions(latitude: float, longitude: float, location: dict) -> dict:
    """Send coordinates only; a routing outage never changes a booked appointment."""
    destination_latitude = location.get("latitude")
    destination_longitude = location.get("longitude")
    if not valid_coordinates(latitude, longitude):
        return {"error": "Give finite latitude (-90 to 90) and longitude (-180 to 180)."}
    if not valid_coordinates(destination_latitude, destination_longitude):
        return {"error": "Site coordinates are missing or invalid in the clinic catalogue."}

    result = {
        "location_id": location["id"],
        "destination_name": location["name"],
        "destination_address": location["address"],
        "mode": "driving",
        "origin_is_approximate": True,
        "directions_url": "https://www.google.com/maps/dir/?"
        + urlencode(
            {
                "api": 1,
                "origin": f"{latitude},{longitude}",
                "destination": f"{destination_latitude},{destination_longitude}",
                "travelmode": "driving",
            }
        ),
        "limitation": (
            "Approximate origin estimated from the caller's place description. Driving/car or "
            "taxi estimate only, without live traffic; not walking or public transport. "
            "No verified entrance, floor or parking information."
        ),
    }
    url = (
        "https://router.project-osrm.org/route/v1/driving/"
        f"{longitude},{latitude};{destination_longitude},{destination_latitude}"
    )
    try:
        async with asyncio.timeout(4.0):
            async with httpx.AsyncClient(timeout=4.0) as client:
                response = await client.get(url, params={"overview": "false", "steps": "true"})
                response.raise_for_status()
                payload = response.json()
        if payload.get("code") != "Ok":
            raise ValueError("No route available")
        route = payload["routes"][0]
        distance, duration = route["distance"], route["duration"]
        if not all(
            not isinstance(value, bool)
            and isinstance(value, (int, float))
            and isfinite(value)
            and value >= 0
            for value in (distance, duration)
        ):
            raise ValueError("Invalid route estimates")
        segments: list[dict] = []
        for leg in route.get("legs", []):
            for step in leg.get("steps", []):
                name, reference = step.get("name", ""), step.get("ref", "")
                road = " / ".join(part for part in (name, reference) if part)
                maneuver = step.get("maneuver", {})
                if not road:
                    continue
                if segments and segments[-1]["road"] == road:
                    segments[-1]["distance"] += step.get("distance", 0)
                else:
                    segments.append(
                        {
                            "road": road,
                            "distance": step.get("distance", 0),
                            "type": maneuver.get("type", ""),
                            "modifier": maneuver.get("modifier", ""),
                        }
                    )
        # Keep the four main roads in journey order for a short spoken overview.
        selected = sorted(
            sorted(range(len(segments)), key=lambda i: segments[i]["distance"], reverse=True)[:4]
        )
        roads = [segments[i]["road"] for i in selected]
        maneuvers = [
            {key: value for key, value in segments[i].items() if key != "distance"}
            for i in selected
        ]
        return {
            **result,
            "source": "OSRM",
            "route_available": True,
            "distance_km": round(distance / 1000, 1),
            "duration_minutes": max(1, round(duration / 60)),
            "roads": roads,
            "road_segments_omitted": max(0, len(segments) - len(selected)),
            "maneuvers": maneuvers,
        }
    except (
        httpx.HTTPError,
        TimeoutError,
        ValueError,
        KeyError,
        IndexError,
        TypeError,
        AttributeError,
    ):
        return {
            **result,
            "source": "maps_link",
            "route_available": False,
            "message": (
                "Live directions are unavailable. Give the verified destination address and "
                "suggest entering that address in maps or giving it to a taxi driver. "
                "Do not read the URL aloud or claim to send a link. "
                "Do not invent a route or travel time. "
                "Keep any recorded appointment."
            ),
        }
