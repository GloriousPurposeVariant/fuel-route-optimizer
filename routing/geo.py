import numpy as np

EARTH_RADIUS_MILES = 3958.8


def to_unit_xyz(latitudes, longitudes):
    """Convert lat/lon in degrees to 3D points on a unit sphere, so straight-line distance matches ground distance."""
    lat = np.radians(np.asarray(latitudes, dtype=float))
    lon = np.radians(np.asarray(longitudes, dtype=float))
    return np.column_stack((np.cos(lat) * np.cos(lon), np.cos(lat) * np.sin(lon), np.sin(lat)))


def miles_to_chord(miles):
    """Straight-line distance through the unit sphere for a ground distance in miles."""
    return 2 * np.sin(np.asarray(miles, dtype=float) / (2 * EARTH_RADIUS_MILES))


def chord_to_miles(chord):
    return 2 * EARTH_RADIUS_MILES * np.arcsin(np.clip(np.asarray(chord, dtype=float) / 2, 0, 1))


def segment_lengths_miles(longitudes, latitudes):
    """Haversine length of each segment of a polyline."""
    lon = np.radians(np.asarray(longitudes, dtype=float))
    lat = np.radians(np.asarray(latitudes, dtype=float))
    dlat = np.diff(lat)
    dlon = np.diff(lon)
    a = np.sin(dlat / 2) ** 2 + np.cos(lat[:-1]) * np.cos(lat[1:]) * np.sin(dlon / 2) ** 2
    return 2 * EARTH_RADIUS_MILES * np.arcsin(np.sqrt(a))
