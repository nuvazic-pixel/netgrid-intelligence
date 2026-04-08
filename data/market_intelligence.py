"""
market_intelligence.py
=======================
Competitor overlay + real telecom data layer.

Real data sources (all free / open):
  1. Bundesnetzagentur Breitbandatlas API  — official German broadband coverage
  2. OpenStreetMap telecom infrastructure  — existing masts, cabinets
  3. Density-based competition proxy       — fallback when APIs are unavailable

Bundesnetzagentur Breitbandatlas API docs:
  https://gigabitgrundbuch.bund.de/GIGA/DE/MobilesBreitband/start.html
  WFS endpoint (no key required):
  https://geodienste.bkg.bund.de/gdz_frame?SERVICE=WFS&...
"""

import math
import requests
import pandas as pd
import numpy as np


# ── 1. DENSITY-BASED COMPETITION PROXY (always available, instant) ────────────

def classify_competition(lat: float, lon: float,
                         center_lat: float, center_lon: float) -> str:
    dist = math.sqrt((lat - center_lat) ** 2 + (lon - center_lon) ** 2)
    if dist < 0.02:
        return 'High'
    elif dist < 0.06:
        return 'Medium'
    return 'Low'


def competition_impact(level: str) -> float:
    return {'High': 0.60, 'Medium': 0.80, 'Low': 1.00}.get(level, 1.0)


def apply_market_overlay(df: pd.DataFrame,
                         center_lat: float, center_lon: float) -> pd.DataFrame:
    """Add competition level + factor columns to building DataFrame."""
    df = df.copy()
    df['competition'] = df.apply(
        lambda r: classify_competition(r['lat'], r['lon'], center_lat, center_lon),
        axis=1
    )
    df['competition_factor'] = df['competition'].apply(competition_impact)
    return df


# ── 2. BUNDESNETZAGENTUR BREITBANDATLAS (real German broadband data) ──────────
#
#  WFS service — returns broadband availability per Gemeinde (100 Mbit/s+).
#  No API key required. Rate-limit friendly (cache results).
#
BREITBAND_WFS = (
    'https://geodienste.bkg.bund.de/gdz_frame'
    '?SERVICE=WFS&VERSION=2.0.0&REQUEST=GetFeature'
    '&TYPENAMES=gdz:breitband_gemeinde'
    '&OUTPUTFORMAT=application/json'
    '&COUNT=200'
    '&CQL_FILTER=INTERSECTS(geom,POINT({lon}+{lat}))'
)


def fetch_breitband_coverage(lat: float, lon: float,
                              timeout: int = 8) -> dict | None:
    """
    Query Breitbandatlas WFS for broadband coverage at a location.
    Returns dict with coverage info or None on failure.
    """
    url = BREITBAND_WFS.format(lat=lat, lon=lon)
    try:
        resp = requests.get(url, timeout=timeout)
        if resp.status_code == 200:
            data = resp.json()
            features = data.get('features', [])
            if features:
                props = features[0].get('properties', {})
                return {
                    'gemeinde':           props.get('gen', 'Unknown'),
                    'coverage_100mbit':   props.get('ant_100', 0),
                    'coverage_gigabit':   props.get('ant_gbit', 0),
                    'coverage_ftth':      props.get('ant_ftth', 0),
                    'households':         props.get('hh_ges', 0),
                    'source':             'Bundesnetzagentur Breitbandatlas',
                }
    except Exception as e:
        print(f'Breitbandatlas fetch error: {e}')
    return None


# ── 3. ALTERNATIVE: Bundesnetzagentur Gigabit-Grundbuch REST API ──────────────
#
#  Newer REST endpoint — returns per-address gigabit availability.
#  https://gigabitgrundbuch.bund.de/  (no key, CORS-open)
#
GIGABIT_API = 'https://gigabitgrundbuch.bund.de/GIGA/DE/Rest/GigabitAtlas/json'


def fetch_gigabit_atlas(lat: float, lon: float,
                        radius_m: int = 1000, timeout: int = 8) -> dict | None:
    """
    Query Gigabit-Grundbuch for fiber/gigabit availability around a point.
    Returns summary dict or None.
    """
    params = {
        'lat': lat, 'lon': lon,
        'radius': radius_m,
        'format': 'json'
    }
    try:
        resp = requests.get(GIGABIT_API, params=params, timeout=timeout)
        if resp.status_code == 200:
            return resp.json()
    except Exception as e:
        print(f'Gigabit-Grundbuch fetch error: {e}')
    return None


# ── 4. OSM TELECOM INFRASTRUCTURE ─────────────────────────────────────────────

def fetch_osm_telecom(lat: float, lon: float,
                      radius_m: int = 2000, timeout: int = 10) -> pd.DataFrame:
    """
    Fetch existing telecom infrastructure (cabinets, masts, exchanges)
    from OpenStreetMap Overpass API. Free, no key required.
    """
    overpass_url = 'https://overpass-api.de/api/interpreter'
    query = f"""
    [out:json][timeout:{timeout}];
    (
      node["telecom"](around:{radius_m},{lat},{lon});
      node["man_made"="mast"]["operator"](around:{radius_m},{lat},{lon});
      node["building"="service"]["telecom"](around:{radius_m},{lat},{lon});
      way["telecom"="cable_distribution_cabinet"](around:{radius_m},{lat},{lon});
    );
    out center;
    """
    try:
        resp = requests.post(overpass_url, data={'data': query}, timeout=timeout + 5)
        if resp.status_code == 200:
            elements = resp.json().get('elements', [])
            rows = []
            for el in elements:
                lat_e  = el.get('lat') or el.get('center', {}).get('lat')
                lon_e  = el.get('lon') or el.get('center', {}).get('lon')
                tags   = el.get('tags', {})
                if lat_e and lon_e:
                    rows.append({
                        'lat':      lat_e,
                        'lon':      lon_e,
                        'type':     tags.get('telecom', tags.get('man_made', 'unknown')),
                        'operator': tags.get('operator', 'Unknown'),
                        'name':     tags.get('name', ''),
                    })
            return pd.DataFrame(rows)
    except Exception as e:
        print(f'OSM telecom fetch error: {e}')
    return pd.DataFrame(columns=['lat', 'lon', 'type', 'operator', 'name'])


# ── 5. COMPETITION SCORE ENRICHMENT ──────────────────────────────────────────

def enrich_competition_from_telecom(df: pd.DataFrame,
                                    telecom_df: pd.DataFrame,
                                    radius_deg: float = 0.01) -> pd.DataFrame:
    """
    For each building, count how many OSM telecom nodes are within radius_deg.
    High count → existing infrastructure → higher competition.
    """
    df = df.copy()
    if telecom_df.empty:
        df['telecom_infra_count'] = 0
        return df

    counts = []
    t_lat = telecom_df['lat'].values
    t_lon = telecom_df['lon'].values

    for _, row in df.iterrows():
        dists = np.sqrt((t_lat - row['lat']) ** 2 + (t_lon - row['lon']) ** 2)
        counts.append(int((dists < radius_deg).sum()))

    df['telecom_infra_count'] = counts

    # Upgrade competition level if real infra found nearby
    def upgrade_competition(row):
        if row.get('telecom_infra_count', 0) >= 3:
            return 'High'
        elif row.get('telecom_infra_count', 0) >= 1:
            return max(row.get('competition', 'Low'),
                       'Medium',
                       key=lambda x: ['Low', 'Medium', 'High'].index(x))
        return row.get('competition', 'Low')

    df['competition'] = df.apply(upgrade_competition, axis=1)
    df['competition_factor'] = df['competition'].apply(competition_impact)
    return df


# ── 6. BUNDESNETZAGENTUR COVERAGE SUMMARY FOR SIDEBAR ─────────────────────────

def get_coverage_summary(lat: float, lon: float) -> dict:
    """
    Try real Breitbandatlas first, fall back to synthetic estimate.
    Always returns a dict safe to display in the UI.
    """
    real = fetch_breitband_coverage(lat, lon)
    if real:
        return {
            'source':           real['source'],
            'gemeinde':         real['gemeinde'],
            'ftth_coverage':    f"{real['coverage_ftth']:.0f}%",
            'gbit_coverage':    f"{real['coverage_gigabit']:.0f}%",
            'broadband_100':    f"{real['coverage_100mbit']:.0f}%",
            'households':       real['households'],
            'is_real':          True,
        }
    # Synthetic fallback
    return {
        'source':        'Estimated (Breitbandatlas unavailable)',
        'gemeinde':      'Unknown',
        'ftth_coverage': 'N/A',
        'gbit_coverage': 'N/A',
        'broadband_100': 'N/A',
        'households':    0,
        'is_real':       False,
    }
