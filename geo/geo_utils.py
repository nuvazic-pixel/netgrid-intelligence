import requests
from geopy.geocoders import Nominatim

_geolocator = Nominatim(user_agent='ftth_intelligence_platform')


def geocode_address(address: str) -> dict | None:
    """Convert address string to lat/lon dict. Returns None if not found."""
    try:
        location = _geolocator.geocode(address)
        if location:
            return {'lat': location.latitude, 'lon': location.longitude, 'display': location.address}
    except Exception as e:
        print(f'Geocoding error: {e}')
    return None


def check_company(name: str) -> dict | None:
    """Basic company existence check via OpenCorporates (no API key needed)."""
    try:
        url = f'https://api.opencorporates.com/v0.4/companies/search?q={name}&jurisdiction_code=de'
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        print(f'Company check error: {e}')
    return None


def estimate_pop_node_distance(building_lat: float, building_lon: float,
                                node_lat: float, node_lon: float) -> float:
    """Haversine distance in metres between two lat/lon points."""
    import math
    R = 6_371_000
    phi1, phi2 = math.radians(building_lat), math.radians(node_lat)
    dphi = math.radians(node_lat - building_lat)
    dlam = math.radians(node_lon - building_lon)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    return round(R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a)), 0)
