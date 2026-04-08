"""
geo_utils.py — Geospatial utilities for FTTH Expansion Platform
Geocoding, distance calculations, coordinate handling
"""

import math
from typing import Optional


# Fallback coordinates for common Bavarian locations
KNOWN_LOCATIONS = {
    "landsberg am lech": {"lat": 48.0520, "lon": 10.8700, "name": "Landsberg am Lech"},
    "landsberg": {"lat": 48.0520, "lon": 10.8700, "name": "Landsberg am Lech"},
    "kaufering": {"lat": 48.0900, "lon": 10.8550, "name": "Kaufering"},
    "münchen": {"lat": 48.1351, "lon": 11.5820, "name": "München"},
    "munich": {"lat": 48.1351, "lon": 11.5820, "name": "München"},
    "augsburg": {"lat": 48.3668, "lon": 10.8986, "name": "Augsburg"},
    "penzing": {"lat": 48.0750, "lon": 10.9200, "name": "Penzing"},
    "igling": {"lat": 48.0350, "lon": 10.8100, "name": "Igling"},
    "denklingen": {"lat": 47.9200, "lon": 10.8500, "name": "Denklingen"},
    "weil": {"lat": 47.9800, "lon": 10.9100, "name": "Weil"},
}


def geocode_address(address: str) -> Optional[dict]:
    """
    Geocode an address to lat/lon coordinates.
    Uses local lookup first, then falls back to default location.
    
    In production, integrate with Nominatim or Google Geocoding API.
    """
    if not address:
        return None
    
    # Normalize address
    normalized = address.lower().strip()
    
    # Check known locations
    for key, coords in KNOWN_LOCATIONS.items():
        if key in normalized:
            return coords.copy()
    
    # Default: Landsberg am Lech
    return {
        "lat": 48.0520,
        "lon": 10.8700,
        "name": address
    }


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the great-circle distance between two points in meters.
    """
    R = 6371000  # Earth's radius in meters
    
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    
    a = (math.sin(delta_phi / 2) ** 2 +
         math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    return R * c


def get_bounding_box(lat: float, lon: float, radius_km: float = 10) -> dict:
    """
    Calculate a bounding box around a point.
    Returns dict with north, south, east, west coordinates.
    """
    # Approximate degrees per km
    lat_delta = radius_km / 111.0
    lon_delta = radius_km / (111.0 * math.cos(math.radians(lat)))
    
    return {
        "north": lat + lat_delta,
        "south": lat - lat_delta,
        "east": lon + lon_delta,
        "west": lon - lon_delta,
    }


def point_in_bbox(lat: float, lon: float, bbox: dict) -> bool:
    """Check if a point is within a bounding box."""
    return (bbox["south"] <= lat <= bbox["north"] and
            bbox["west"] <= lon <= bbox["east"])


def calculate_bearing(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the bearing (direction) from point 1 to point 2.
    Returns angle in degrees (0-360, where 0=North).
    """
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_lambda = math.radians(lon2 - lon1)
    
    x = math.sin(delta_lambda) * math.cos(phi2)
    y = (math.cos(phi1) * math.sin(phi2) -
         math.sin(phi1) * math.cos(phi2) * math.cos(delta_lambda))
    
    bearing = math.degrees(math.atan2(x, y))
    return (bearing + 360) % 360


if __name__ == "__main__":
    # Test geocoding
    loc = geocode_address("Landsberg am Lech")
    print(f"Geocoded: {loc}")
    
    # Test distance
    dist = haversine_distance(48.052, 10.87, 48.09, 10.855)
    print(f"Distance Landsberg→Kaufering: {dist:.0f}m")
