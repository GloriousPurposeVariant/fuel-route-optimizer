from dataclasses import dataclass

from stations.constants import SUPPORTED_STATES, US_STATES
from stations.geocoding import find_city

from .exceptions import InvalidLocation, LocationNotFound, LocationNotInUSA, UnsupportedRegion

UNSUPPORTED_REGION_MESSAGES = {
    "AK": "Alaska can only be reached by road through Canada, and routes are limited to the USA.",
    "HI": "Hawaii has no road connection to the mainland United States.",
}


@dataclass(frozen=True)
class Location:
    query: str
    name: str
    latitude: float
    longitude: float


def resolve_location(query):
    """Turn 'Dallas, TX' into a Location using the local City table. No network call."""
    query = (query or "").strip()
    city, separator, state = query.rpartition(",")
    city, state = city.strip(), state.strip().upper()

    if not separator or not city or len(state) != 2 or not state.isalpha():
        raise InvalidLocation(f"'{query}' is not in 'City, ST' format, e.g. 'Dallas, TX'.")
    if state not in US_STATES:
        raise LocationNotInUSA(
            f"'{query}' is not in the USA. Use a US state code, e.g. 'Dallas, TX'."
        )
    if state not in SUPPORTED_STATES:
        raise UnsupportedRegion(f"'{query}': {UNSUPPORTED_REGION_MESSAGES[state]}")

    match = find_city(city, state)
    if match is None:
        raise LocationNotFound(
            f"Could not find '{city}, {state}'. Check the spelling or try a nearby city."
        )

    name, latitude, longitude = match
    return Location(query=query, name=f"{name}, {state}", latitude=latitude, longitude=longitude)
