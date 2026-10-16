import logging
import time
from contextlib import contextmanager
from dataclasses import dataclass, field

from django.conf import settings
from django.core.cache import cache

from stations.models import FuelStation

from .corridor import find_corridor_stations, resample_route
from .locations import Location, resolve_location
from .optimizer import plan_fuel_stops
from .ors import get_route

logger = logging.getLogger(__name__)


@contextmanager
def _timed(timings, name):
    started = time.perf_counter()
    yield
    timings[name] = round((time.perf_counter() - started) * 1000, 2)


def _route_cache_key(start, finish):
    return (
        f"route:v1:{settings.ORS_PROFILE}:"
        f"{start.latitude:.5f},{start.longitude:.5f}:{finish.latitude:.5f},{finish.longitude:.5f}"
    )


def _get_route_cached(start, finish):
    """Return (route, cache_hit). Only successful routes are cached."""
    key = _route_cache_key(start, finish)
    route = cache.get(key)
    if route is not None:
        return route, True
    route = get_route(start, finish)
    cache.set(key, route, settings.ROUTE_CACHE_SECONDS)
    return route, False


@dataclass(frozen=True)
class PlannedStop:
    opis_id: int
    name: str
    address: str
    city: str
    state: str
    latitude: float
    longitude: float
    mile_marker: float
    distance_from_route_miles: float
    price_per_gallon: float
    gallons: float
    cost: float


@dataclass(frozen=True)
class TripPlan:
    start: Location
    finish: Location
    distance_miles: float
    duration_hours: float
    geometry: list
    stations_considered: int
    stops: list
    total_gallons: float
    total_cost: float
    route_cache_hit: bool = False
    timings_ms: dict = field(default_factory=dict)


def plan_trip(start_query, finish_query):
    """Resolve both locations, fetch the route (one ORS call, or none if cached) and plan fuel stops."""
    timings = {}
    with _timed(timings, "geocode"):
        start = resolve_location(start_query)
        finish = resolve_location(finish_query)

    if (start.latitude, start.longitude) == (finish.latitude, finish.longitude):
        return TripPlan(
            start=start,
            finish=finish,
            distance_miles=0.0,
            duration_hours=0.0,
            geometry=[[start.longitude, start.latitude]],
            stations_considered=0,
            stops=[],
            total_gallons=0.0,
            total_cost=0.0,
            timings_ms=timings,
        )

    with _timed(timings, "route"):
        route, cache_hit = _get_route_cached(start, finish)
    with _timed(timings, "corridor"):
        corridor = find_corridor_stations(route)
    with _timed(timings, "optimize"):
        fuel_plan = plan_fuel_stops(
            corridor, route.distance_miles, settings.VEHICLE_RANGE_MILES, settings.VEHICLE_MPG
        )
    with _timed(timings, "details"):
        stations = FuelStation.objects.in_bulk([stop.station_id for stop in fuel_plan.stops])
        corridor_by_id = {candidate.station_id: candidate for candidate in corridor}
        stops = [
            _planned_stop(stop, stations[stop.station_id], corridor_by_id[stop.station_id])
            for stop in fuel_plan.stops
        ]
        lon, lat, _ = resample_route(route.coordinates, route.distance_miles)
        geometry = [[round(x, 5), round(y, 5)] for x, y in zip(lon, lat, strict=True)]

    logger.info(
        "Trip %s -> %s: %.1f mi, %d stops, $%.2f, route cache %s, timings %s",
        start.name,
        finish.name,
        route.distance_miles,
        len(stops),
        fuel_plan.total_cost,
        "hit" if cache_hit else "miss",
        timings,
    )
    return TripPlan(
        start=start,
        finish=finish,
        distance_miles=round(route.distance_miles, 1),
        duration_hours=round(route.duration_hours, 2),
        geometry=geometry,
        stations_considered=len(corridor),
        stops=stops,
        total_gallons=fuel_plan.total_gallons,
        total_cost=fuel_plan.total_cost,
        route_cache_hit=cache_hit,
        timings_ms=timings,
    )


def _planned_stop(stop, station, candidate):
    return PlannedStop(
        opis_id=station.opis_id,
        name=station.name,
        address=station.address,
        city=station.city,
        state=station.state,
        latitude=station.latitude,
        longitude=station.longitude,
        mile_marker=round(stop.mile_marker, 1),
        distance_from_route_miles=round(candidate.distance_from_route_miles, 1),
        price_per_gallon=round(stop.price, 3),
        gallons=stop.gallons,
        cost=stop.cost,
    )
