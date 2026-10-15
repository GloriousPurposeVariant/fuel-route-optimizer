from dataclasses import dataclass
from functools import lru_cache

import numpy as np
from django.conf import settings
from scipy.spatial import cKDTree

from stations.models import FuelStation

from .geo import chord_to_miles, miles_to_chord, segment_lengths_miles, to_unit_xyz

SAMPLE_SPACING_MILES = 1.0


@dataclass(frozen=True)
class StationIndex:
    """Station coordinates and prices as numpy arrays, built once and reused for every request."""

    ids: np.ndarray
    prices: np.ndarray
    xyz: np.ndarray

    @classmethod
    def from_rows(cls, rows):
        """Build from (id, price, latitude, longitude) tuples."""
        if not rows:
            return cls(np.empty(0, dtype=int), np.empty(0), np.empty((0, 3)))
        ids, prices, lats, lons = zip(*rows, strict=True)
        return cls(np.array(ids), np.array(prices, dtype=float), to_unit_xyz(lats, lons))


@dataclass(frozen=True)
class CorridorStation:
    station_id: int
    mile_marker: float
    distance_from_route_miles: float
    price: float


@lru_cache(maxsize=1)
def get_station_index():
    rows = list(FuelStation.objects.values_list("id", "price", "latitude", "longitude"))
    return StationIndex.from_rows(rows)


def resample_route(coordinates, total_miles=None):
    """Return (longitudes, latitudes, mile_markers) with one point per mile along the route."""
    points = np.asarray(coordinates, dtype=float)
    lon, lat = points[:, 0], points[:, 1]

    segments = segment_lengths_miles(lon, lat)
    keep = np.concatenate(([True], segments > 0))
    lon, lat = lon[keep], lat[keep]
    cumulative = np.concatenate(([0.0], np.cumsum(segments[segments > 0])))

    measured = cumulative[-1]
    if measured == 0:
        return lon[:1], lat[:1], np.zeros(1)
    if total_miles:
        cumulative *= total_miles / measured

    markers = np.arange(0.0, cumulative[-1], SAMPLE_SPACING_MILES)
    markers = np.append(markers, cumulative[-1])
    return np.interp(markers, cumulative, lon), np.interp(markers, cumulative, lat), markers


def find_corridor_stations(route, radius_miles=None, index=None):
    """Stations within radius_miles of the route, each with its mile marker, sorted by mile marker."""
    radius_miles = settings.CORRIDOR_RADIUS_MILES if radius_miles is None else radius_miles
    index = get_station_index() if index is None else index
    if len(index.ids) == 0:
        return []

    lon, lat, markers = resample_route(route.coordinates, route.distance_miles)
    tree = cKDTree(to_unit_xyz(lat, lon))
    chord, nearest = tree.query(index.xyz, distance_upper_bound=miles_to_chord(radius_miles))

    hit = np.isfinite(chord)
    station_markers = markers[nearest[hit]]
    order = np.argsort(station_markers, kind="stable")
    distances = chord_to_miles(chord[hit])

    return [
        CorridorStation(
            station_id=int(station_id),
            mile_marker=float(marker),
            distance_from_route_miles=float(distance),
            price=float(price),
        )
        for station_id, marker, distance, price in zip(
            index.ids[hit][order],
            station_markers[order],
            distances[order],
            index.prices[hit][order],
            strict=True,
        )
    ]
