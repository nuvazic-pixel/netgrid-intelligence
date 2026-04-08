"""
live_api.py
===========
Live external API integrations for FTTH/FTTx Intelligence Platform.

All APIs used are FREE, no key required:
  - Nominatim (OSM)    — geocoding
  - Open-Meteo         — live weather
  - Overpass API       — already in market_intelligence.py
  - ip-api.com         — optional IP-based location fallback

Part of: FTTH/FTTx Intelligence Platform
"""

from __future__ import annotations
import requests
from functools import lru_cache
from datetime import datetime


# ── SHARED HTTP HELPER ────────────────────────────────────────────────────────

def safe_get(url: str, params: dict | None = None,
             headers: dict | None = None, timeout: int = 12) -> dict | None:
    try:
        r = requests.get(url, params=params, headers=headers, timeout=timeout)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(f'[live_api] {url[:60]} → {e}')
        return None


# ── 1. LIVE GEOCODING — Nominatim ─────────────────────────────────────────────

@lru_cache(maxsize=64)
def geocode_live(query: str) -> dict | None:
    """
    Forward geocode a place name or address.
    Cached per session — same query won't hit API twice.
    Returns: {lat, lon, display_name, city, country} or None.
    """
    data = safe_get(
        'https://nominatim.openstreetmap.org/search',
        params={'q': query, 'format': 'json', 'limit': 1,
                'addressdetails': 1},
        headers={'User-Agent': 'fttx-intelligence-platform/1.0 (demo)'}
    )
    if not data:
        return None

    first = data[0]
    addr  = first.get('address', {})
    return {
        'lat':          float(first['lat']),
        'lon':          float(first['lon']),
        'display_name': first.get('display_name', query),
        'city':         addr.get('city') or addr.get('town') or addr.get('village', ''),
        'state':        addr.get('state', ''),
        'country':      addr.get('country', ''),
        'postcode':     addr.get('postcode', ''),
    }


def reverse_geocode(lat: float, lon: float) -> dict | None:
    """Reverse geocode lat/lon to address."""
    data = safe_get(
        'https://nominatim.openstreetmap.org/reverse',
        params={'lat': lat, 'lon': lon, 'format': 'json', 'addressdetails': 1},
        headers={'User-Agent': 'fttx-intelligence-platform/1.0 (demo)'}
    )
    if not data:
        return None
    addr = data.get('address', {})
    return {
        'display_name': data.get('display_name', ''),
        'city':  addr.get('city') or addr.get('town') or addr.get('village', ''),
        'state': addr.get('state', ''),
        'postcode': addr.get('postcode', ''),
    }


# ── 2. LIVE WEATHER — Open-Meteo (free, no key) ───────────────────────────────

def get_weather_live(lat: float, lon: float) -> dict | None:
    """
    Fetch current weather from Open-Meteo.
    Returns: {temperature_c, precipitation, wind_speed, description, timestamp}
    """
    data = safe_get(
        'https://api.open-meteo.com/v1/forecast',
        params={
            'latitude':  lat,
            'longitude': lon,
            'current':   'temperature_2m,precipitation,wind_speed_10m,weathercode',
            'timezone':  'auto',
        }
    )
    if not data or 'current' not in data:
        return None

    cur = data['current']
    wcode = cur.get('weathercode', 0)

    return {
        'temperature_c': cur.get('temperature_2m'),
        'precipitation':  cur.get('precipitation', 0),
        'wind_speed':     cur.get('wind_speed_10m', 0),
        'weather_code':   wcode,
        'description':    _weather_description(wcode),
        'timestamp':      cur.get('time', datetime.now().isoformat()),
    }


def _weather_description(code: int) -> str:
    """Map WMO weather code to human-readable label."""
    if code == 0:             return 'Clear sky'
    elif code <= 3:           return 'Partly cloudy'
    elif code <= 9:           return 'Fog'
    elif code <= 19:          return 'Drizzle'
    elif code <= 29:          return 'Rain'
    elif code <= 39:          return 'Snow'
    elif code <= 49:          return 'Fog'
    elif code <= 59:          return 'Drizzle'
    elif code <= 69:          return 'Rain'
    elif code <= 79:          return 'Snow / sleet'
    elif code <= 84:          return 'Rain showers'
    elif code <= 94:          return 'Thunderstorm'
    return 'Severe weather'


# ── 3. DEPLOYMENT CONDITION SCORE ─────────────────────────────────────────────

def deployment_condition_score(weather: dict | None) -> int | None:
    """
    Score 0–100 for field deployment conditions.
    Factors: temperature, precipitation, wind.
    100 = ideal conditions for outdoor fiber trenching.
    """
    if weather is None:
        return None

    score = 100
    temp  = weather.get('temperature_c', 15) or 15
    rain  = weather.get('precipitation', 0) or 0
    wind  = weather.get('wind_speed', 0) or 0
    code  = weather.get('weather_code', 0) or 0

    # Temperature impact
    if temp < -5:    score -= 30
    elif temp < 0:   score -= 20
    elif temp < 5:   score -= 10
    elif temp > 35:  score -= 15
    elif temp > 30:  score -= 8

    # Precipitation impact
    if rain > 5:     score -= 25
    elif rain > 1:   score -= 15
    elif rain > 0:   score -= 8

    # Wind impact
    if wind > 50:    score -= 25
    elif wind > 30:  score -= 15
    elif wind > 20:  score -= 8

    # Severe weather codes
    if code >= 80:   score -= 20
    elif code >= 60: score -= 10

    return max(0, int(score))


def score_label(score: int | None) -> tuple[str, str]:
    """Returns (label, emoji) for deployment score."""
    if score is None:
        return 'Unknown', '⚪'
    if score >= 80:
        return 'Excellent', '🟢'
    elif score >= 60:
        return 'Good', '🟡'
    elif score >= 40:
        return 'Moderate', '🟠'
    return 'Poor', '🔴'


# ── 4. LIVE CITY CONTEXT ─────────────────────────────────────────────────────

def get_live_city_context(query: str) -> dict | None:
    """
    Full context for a city/address:
    - geo coordinates
    - live weather
    - deployment condition score
    - AI deployment recommendation
    Returns None if geocoding fails.
    """
    geo = geocode_live(query)
    if geo is None:
        return None

    weather      = get_weather_live(geo['lat'], geo['lon'])
    deploy_score = deployment_condition_score(weather)
    label, emoji = score_label(deploy_score)

    return {
        'geo':              geo,
        'weather':          weather,
        'deployment_score': deploy_score,
        'score_label':      label,
        'score_emoji':      emoji,
        'fetched_at':       datetime.now().strftime('%H:%M:%S'),
    }


# ── 5. POPULATION DENSITY — Overpass proxy ────────────────────────────────────

def get_place_population(city: str) -> int | None:
    """
    Fetch population tag from OSM via Overpass.
    Returns integer population or None.
    """
    query = f"""
    [out:json][timeout:10];
    (
      node["name"~"{city}"]["place"~"city|town|village"]["population"];
      way["name"~"{city}"]["place"~"city|town|village"]["population"];
      relation["name"~"{city}"]["place"~"city|town|village"]["population"];
    );
    out 1;
    """
    data = safe_get(
        'https://overpass-api.de/api/interpreter',
        params={'data': query}
    )
    if not data:
        return None
    elements = data.get('elements', [])
    for el in elements:
        pop = el.get('tags', {}).get('population')
        if pop:
            try:
                return int(pop.replace('.', '').replace(',', ''))
            except ValueError:
                pass
    return None


# ── 6. DECISION CONTEXT SUFFIX ───────────────────────────────────────────────

def decision_context_suffix(deploy_score: int | None) -> str:
    """Return a short suffix to append to AI decision text."""
    if deploy_score is None:
        return ''
    if deploy_score < 40:
        return ' · ⚠️ Poor field conditions today'
    elif deploy_score < 65:
        return ' · 🟡 Moderate field conditions'
    return ' · 🟢 Good field conditions'
