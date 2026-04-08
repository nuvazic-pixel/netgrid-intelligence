"""
national_data.py
================
National-scale real data loaders for Germany.
No API keys required for any source.

Sources:
  1. BKG Verwaltungsgebiete (vg250) — official Gemeinde boundaries, all Germany
  2. Gigabit-Grundbuch WFS — broadband coverage per Gemeinde, all Germany
  3. Destatis Genesis-Online API — population/demographics per Gemeinde
  4. Geofabrik OSM extracts — buildings per Bundesland (no OSMnx timeout)

Usage:
    from national_data import build_national_dataset
    gdf = build_national_dataset(bundesland="Bayern")

Part of: FTTH/FTTx Intelligence Platform
"""

from __future__ import annotations
import io
import time
import zipfile
import requests
import pandas as pd
import numpy as np
from pathlib import Path

try:
    import geopandas as gpd
    HAS_GPD = True
except ImportError:
    HAS_GPD = False

RAW_DIR = Path(__file__).parent.parent / 'data' / 'raw'
RAW_DIR.mkdir(parents=True, exist_ok=True)

BUNDESLAND_KEYS = {
    'Bayern':                  '09',
    'Baden-Württemberg':       '08',
    'Berlin':                  '11',
    'Brandenburg':             '12',
    'Bremen':                  '04',
    'Hamburg':                 '02',
    'Hessen':                  '06',
    'Mecklenburg-Vorpommern':  '13',
    'Niedersachsen':           '03',
    'Nordrhein-Westfalen':     '05',
    'Rheinland-Pfalz':         '07',
    'Saarland':                '10',
    'Sachsen':                 '14',
    'Sachsen-Anhalt':          '15',
    'Schleswig-Holstein':      '01',
    'Thüringen':               '16',
}

GEOFABRIK_SLUGS = {
    'Bayern': 'bavaria',
    'Baden-Württemberg': 'baden-wuerttemberg',
    'Berlin': 'berlin',
    'Brandenburg': 'brandenburg',
    'Bremen': 'bremen',
    'Hamburg': 'hamburg',
    'Hessen': 'hessen',
    'Mecklenburg-Vorpommern': 'mecklenburg-vorpommern',
    'Niedersachsen': 'niedersachsen',
    'Nordrhein-Westfalen': 'nordrhein-westfalen',
    'Rheinland-Pfalz': 'rheinland-pfalz',
    'Saarland': 'saarland',
    'Sachsen': 'sachsen',
    'Sachsen-Anhalt': 'sachsen-anhalt',
    'Schleswig-Holstein': 'schleswig-holstein',
    'Thüringen': 'thueringen',
}


# ── 1. BKG VERWALTUNGSGEBIETE (vg250) ────────────────────────────────────────
#  Official administrative boundaries — Gemeinden, Landkreise, Bundesländer
#  License: CC BY 4.0, © GeoBasis-DE / BKG 2024
#  Direct download URL (no login required):

VG250_URL = (
    'https://daten.gdz.bkg.bund.de/produkte/vg/vg250_ebenen_0101'
    '/aktuell/vg250_01-01.utm32s.gpkg.zip'
)


def download_vg250(force: bool = False) -> Path | None:
    """Download vg250 GeoPackage zip from BKG. Cached locally."""
    if not HAS_GPD:
        print('[national_data] geopandas not installed — pip install geopandas')
        return None

    out_zip  = RAW_DIR / 'vg250.gpkg.zip'
    out_gpkg = RAW_DIR / 'vg250.gpkg'

    if out_gpkg.exists() and not force:
        print(f'[national_data] vg250.gpkg already cached at {out_gpkg}')
        return out_gpkg

    print('[national_data] Downloading vg250 from BKG (~80 MB)...')
    try:
        r = requests.get(VG250_URL, stream=True, timeout=120)
        r.raise_for_status()
        with open(out_zip, 'wb') as f:
            for chunk in r.iter_content(chunk_size=1024 * 256):
                f.write(chunk)

        with zipfile.ZipFile(out_zip) as z:
            gpkg_name = next(n for n in z.namelist() if n.endswith('.gpkg'))
            with z.open(gpkg_name) as src, open(out_gpkg, 'wb') as dst:
                dst.write(src.read())

        out_zip.unlink(missing_ok=True)
        print(f'[national_data] vg250.gpkg saved → {out_gpkg}')
        return out_gpkg

    except Exception as e:
        print(f'[national_data] vg250 download error: {e}')
        return None


def load_gemeinden(bundesland: str | None = None) -> 'gpd.GeoDataFrame | None':
    """
    Load Gemeinden from vg250 GeoPackage.
    Optionally filter to one Bundesland.
    Returns GeoDataFrame in EPSG:4326 with lat/lon centroids.
    """
    if not HAS_GPD:
        return None

    gpkg_path = RAW_DIR / 'vg250.gpkg'
    if not gpkg_path.exists():
        gpkg_path = download_vg250()
    if gpkg_path is None:
        return None

    try:
        gdf = gpd.read_file(str(gpkg_path), layer='vg250_gem')
        gdf = gdf.to_crs('EPSG:4326')

        if bundesland and bundesland in BUNDESLAND_KEYS:
            key = BUNDESLAND_KEYS[bundesland]
            # AGS (Amtlicher Gemeindeschlüssel) starts with Bundesland key
            if 'AGS' in gdf.columns:
                gdf = gdf[gdf['AGS'].str.startswith(key, na=False)]
            elif 'ARS' in gdf.columns:
                gdf = gdf[gdf['ARS'].str.startswith(key, na=False)]

        gdf['lat'] = gdf.geometry.centroid.y.round(6)
        gdf['lon'] = gdf.geometry.centroid.x.round(6)
        gdf['area_km2'] = (gdf.to_crs('EPSG:25832').geometry.area / 1e6).round(2)

        print(f'[national_data] vg250: {len(gdf)} Gemeinden loaded'
              + (f' ({bundesland})' if bundesland else ' (all Germany)'))
        return gdf

    except Exception as e:
        print(f'[national_data] vg250 load error: {e}')
        return None


# ── 2. GIGABIT-GRUNDBUCH WFS ─────────────────────────────────────────────────
#  Broadband coverage per Gemeinde. No key required. CC BY 4.0.

WFS_BASE = 'https://geodienste.bkg.bund.de/gdz_frame'


def fetch_breitband_wfs(bundesland: str | None = None,
                        max_features: int = 5000) -> pd.DataFrame:
    """
    Fetch broadband coverage from Gigabit-Grundbuch WFS.
    Returns DataFrame with coverage stats per Gemeinde.

    Columns: gemeinde_name, ags, ftth_pct, gbit_pct, coverage_100mbit,
             households, lat, lon
    """
    params = {
        'SERVICE':      'WFS',
        'VERSION':      '2.0.0',
        'REQUEST':      'GetFeature',
        'TYPENAMES':    'gdz:breitband_gemeinde',
        'OUTPUTFORMAT': 'application/json',
        'COUNT':        max_features,
    }
    if bundesland and bundesland in BUNDESLAND_KEYS:
        key = BUNDESLAND_KEYS[bundesland]
        params['CQL_FILTER'] = f"AGS LIKE '{key}%'"

    try:
        r = requests.get(WFS_BASE, params=params, timeout=30)
        r.raise_for_status()
        data = r.json()
        features = data.get('features', [])

        rows = []
        for f in features:
            props = f.get('properties', {})
            geom  = f.get('geometry', {})
            coords = geom.get('coordinates', [None, None]) if geom else [None, None]
            if geom and geom.get('type') == 'Point':
                lon, lat = coords[0], coords[1]
            elif geom and geom.get('type') in ('Polygon', 'MultiPolygon'):
                # centroid approximation from first ring
                lon, lat = None, None
            else:
                lon, lat = None, None

            rows.append({
                'gemeinde_name':   props.get('GEN') or props.get('gen', ''),
                'ags':             props.get('AGS') or props.get('ags', ''),
                'ftth_pct':        props.get('ant_ftth') or props.get('ANT_FTTH', 0),
                'gbit_pct':        props.get('ant_gbit') or props.get('ANT_GBIT', 0),
                'coverage_100mbit':props.get('ant_100')  or props.get('ANT_100', 0),
                'households':      props.get('hh_ges')   or props.get('HH_GES', 0),
                'lat':             lat,
                'lon':             lon,
            })

        df = pd.DataFrame(rows)
        if 'ftth_pct' in df.columns:
            df['coverage_gap_pct'] = (100 - pd.to_numeric(df['ftth_pct'], errors='coerce').fillna(0)).clip(0, 100)

        print(f'[national_data] WFS: {len(df)} Gemeinden broadband data fetched')
        return df

    except Exception as e:
        print(f'[national_data] WFS fetch error: {e}')
        return pd.DataFrame()


# ── 3. DESTATIS GENESIS-ONLINE API ───────────────────────────────────────────
#  Free, GUEST credentials work without registration.
#  Table 12411-0017: Bevölkerung nach Gemeinden

DESTATIS_API = 'https://www-genesis.destatis.de/genesisWS/rest/2020/data/tablefile'


def fetch_destatis_population(bundesland: str | None = None) -> pd.DataFrame:
    """
    Fetch population per Gemeinde from Destatis Genesis-Online API.
    Uses GUEST credentials — no registration needed.
    Returns DataFrame with gemeinde_key, gemeinde_name, population columns.
    """
    bl_key = BUNDESLAND_KEYS.get(bundesland, '') if bundesland else ''
    regional_key = f'{bl_key}*' if bl_key else '*'

    params = {
        'username':        'GUEST',
        'password':        'GUEST',
        'name':            '12411-0017',
        'area':            'all',
        'compress':        'false',
        'transpose':       'false',
        'startyear':       '2022',
        'endyear':         '2022',
        'regionalvariable':'GEMEIN',
        'regionalkey':     regional_key,
        'format':          'csv',
    }

    try:
        r = requests.get(DESTATIS_API, params=params, timeout=30)
        r.raise_for_status()

        # Destatis CSV has metadata header rows — skip until data
        lines = r.text.splitlines()
        header_idx = next(
            (i for i, l in enumerate(lines) if 'Gemeinde' in l or 'gemeinde' in l.lower()),
            0
        )
        df = pd.read_csv(io.StringIO('\n'.join(lines[header_idx:])),
                         sep=';', encoding='utf-8', dtype=str, on_bad_lines='skip')

        # Standardise columns
        rename = {}
        for col in df.columns:
            cl = col.lower()
            if 'schlüssel' in cl or 'key' in cl or cl == 'id': rename[col] = 'gemeinde_key'
            elif 'name' in cl and 'gemeinde' in cl:             rename[col] = 'gemeinde_name'
            elif 'bevölkerung' in cl or 'insgesamt' in cl:      rename[col] = 'population'
        df = df.rename(columns=rename)

        for col in ['population']:
            if col in df.columns:
                df[col] = pd.to_numeric(
                    df[col].str.replace('.', '').str.replace(',', '.'), errors='coerce'
                )

        print(f'[national_data] Destatis: {len(df)} Gemeinden population loaded')
        return df

    except Exception as e:
        print(f'[national_data] Destatis API error: {e}')
        return pd.DataFrame()


# ── 4. GEOFABRIK OSM BUILDINGS (national scale) ───────────────────────────────
#  Downloads pre-compiled OSM extract per Bundesland.
#  Much faster than OSMnx for large areas.

GEOFABRIK_BASE = 'https://download.geofabrik.de/europe/germany'


def download_osm_extract(bundesland: str = 'Bayern',
                          force: bool = False) -> Path | None:
    """
    Download pre-compiled OSM .pbf extract from Geofabrik.
    Bayern ~700 MB. For demo use a Landkreis subset instead.
    """
    slug     = GEOFABRIK_SLUGS.get(bundesland, bundesland.lower())
    filename = f'{slug}-latest.osm.pbf'
    out_path = RAW_DIR / filename

    if out_path.exists() and not force:
        print(f'[national_data] {filename} already cached')
        return out_path

    url = f'{GEOFABRIK_BASE}/{filename}'
    print(f'[national_data] Downloading {filename} from Geofabrik...')
    print(f'  URL: {url}')
    print(f'  This can be large (Bayern ~700 MB). '
          f'Use load_osm_buildings_from_pbf() after download.')

    try:
        r = requests.get(url, stream=True, timeout=300)
        r.raise_for_status()
        with open(out_path, 'wb') as f:
            for chunk in r.iter_content(chunk_size=1024 * 512):
                f.write(chunk)
        print(f'[national_data] Saved → {out_path}')
        return out_path
    except Exception as e:
        print(f'[national_data] Geofabrik download error: {e}')
        return None


def load_osm_buildings_from_pbf(pbf_path: str | Path,
                                 limit: int = 50000) -> pd.DataFrame:
    """
    Extract building centroids from a .pbf file using pyrosm.
    Install: pip install pyrosm
    """
    try:
        from pyrosm import OSM
        osm       = OSM(str(pbf_path))
        buildings = osm.get_buildings()
        buildings = buildings[buildings.geometry.notnull()].head(limit)
        buildings['lat'] = buildings.geometry.centroid.y.round(6)
        buildings['lon'] = buildings.geometry.centroid.x.round(6)
        df = pd.DataFrame({'lat': buildings['lat'], 'lon': buildings['lon']})
        print(f'[national_data] pbf: {len(df)} buildings extracted')
        return df
    except ImportError:
        print('[national_data] pyrosm not installed — pip install pyrosm')
        return pd.DataFrame(columns=['lat', 'lon'])
    except Exception as e:
        print(f'[national_data] pbf load error: {e}')
        return pd.DataFrame(columns=['lat', 'lon'])


# ── 5. MASTER PIPELINE ────────────────────────────────────────────────────────

def build_national_dataset(bundesland: str = 'Bayern',
                            include_broadband: bool = True,
                            include_population: bool = True) -> pd.DataFrame:
    """
    Build a merged Gemeinde-level dataset for analysis.

    Merges:
      - BKG vg250 boundaries (geometry + area)
      - Gigabit-Grundbuch WFS (broadband coverage)
      - Destatis (population)

    Returns flat DataFrame with lat/lon centroids — ready for ML pipeline.
    """
    print(f'[national_data] Building dataset for {bundesland}...')

    # Base: Gemeinde boundaries
    gdf = load_gemeinden(bundesland)
    if gdf is None or gdf.empty:
        print('[national_data] No boundary data — using fallback synthetic')
        return pd.DataFrame()

    df = pd.DataFrame({
        'gemeinde_name': gdf.get('GEN', gdf.get('gen', pd.Series())),
        'ags':           gdf.get('AGS', gdf.get('ars', pd.Series())),
        'lat':           gdf['lat'],
        'lon':           gdf['lon'],
        'area_km2':      gdf['area_km2'],
    })

    # Merge broadband coverage
    if include_broadband:
        bb = fetch_breitband_wfs(bundesland=bundesland)
        if not bb.empty and 'ags' in bb.columns and 'ags' in df.columns:
            bb_merge = bb[['ags','ftth_pct','gbit_pct','coverage_100mbit',
                           'households','coverage_gap_pct']].copy()
            df = df.merge(bb_merge, on='ags', how='left')
            print(f'[national_data] Broadband data merged: '
                  f'{bb_merge["ags"].isin(df["ags"]).sum()} matches')
        time.sleep(0.5)  # be polite to WFS server

    # Merge population
    if include_population:
        pop = fetch_destatis_population(bundesland=bundesland)
        if not pop.empty:
            key_col = 'gemeinde_key' if 'gemeinde_key' in pop.columns else None
            if key_col and 'ags' in df.columns:
                pop_merge = pop[[key_col, 'population']].rename(
                    columns={key_col: 'ags'})
                df = df.merge(pop_merge, on='ags', how='left')
            time.sleep(0.5)

    # Derived features
    if 'population' in df.columns and 'area_km2' in df.columns:
        df['pop_density_km2'] = (
            pd.to_numeric(df['population'], errors='coerce') /
            df['area_km2'].replace(0, np.nan)
        ).round(1)

    if 'ftth_pct' not in df.columns:
        df['ftth_pct']         = np.nan
        df['coverage_gap_pct'] = np.nan

    df['coverage_gap_pct'] = df['coverage_gap_pct'].fillna(
        100 - pd.to_numeric(df.get('ftth_pct', pd.Series()), errors='coerce').fillna(0)
    ).clip(0, 100)

    print(f'[national_data] Final dataset: {len(df)} Gemeinden × {len(df.columns)} columns')
    return df


def list_bundeslaender() -> list[str]:
    """Return sorted list of all Bundesländer names."""
    return sorted(BUNDESLAND_KEYS.keys())
