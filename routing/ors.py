from dataclasses import dataclass

import requests
from django.conf import settings

from .exceptions import NoRouteFound, RouteTooLong, RoutingUnavailable

ORS_DIRECTIONS_URL = "https://api.openrouteservice.org/v2/directions/{profile}/geojson"
SNAP_RADIUS_METERS = 5000
NO_ROUTE_ERROR_CODES = {2009, 2010}  # 2009: no route between points, 2010: no road near a point
LIMIT_EXCEEDED_ERROR_CODE = 2004  # a request value (here, route distance) exceeds the server limit


@dataclass(frozen=True)
class Route:
    coordinates: list
    distance_miles: float
    duration_hours: float


def get_route(start, finish):
    """Make the single OpenRouteService call and return the route line and its length."""
    if not settings.ORS_API_KEY:
        raise RoutingUnavailable("Routing is not configured: ORS_API_KEY is missing.")

    body = {
        "coordinates": [[start.longitude, start.latitude], [finish.longitude, finish.latitude]],
        "units": "mi",
        "instructions": False,
        "radiuses": [SNAP_RADIUS_METERS, SNAP_RADIUS_METERS],
        "options": {"avoid_borders": "all"},
    }
    try:
        response = requests.post(
            ORS_DIRECTIONS_URL.format(profile=settings.ORS_PROFILE),
            json=body,
            headers={"Authorization": settings.ORS_API_KEY},
            timeout=settings.ORS_TIMEOUT_SECONDS,
        )
    except requests.RequestException as exc:
        raise RoutingUnavailable("Could not reach the routing service.") from exc

    if response.status_code == 200:
        feature = response.json()["features"][0]
        summary = feature["properties"].get("summary", {})
        return Route(
            coordinates=feature["geometry"]["coordinates"],
            distance_miles=summary.get("distance", 0.0),
            duration_hours=summary.get("duration", 0.0) / 3600,
        )

    error = _error_body(response)
    if error.get("code") in NO_ROUTE_ERROR_CODES:
        raise NoRouteFound(error.get("message") or NoRouteFound.default_detail)
    if error.get("code") == LIMIT_EXCEEDED_ERROR_CODE:
        raise RouteTooLong()
    raise RoutingUnavailable(f"Routing service error (HTTP {response.status_code}).")


def _error_body(response):
    try:
        error = response.json().get("error", {})
    except ValueError:
        return {}
    return error if isinstance(error, dict) else {"message": str(error)}
