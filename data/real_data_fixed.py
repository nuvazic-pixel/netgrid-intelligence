
import osmnx as ox
import pandas as pd
import numpy as np
from pathlib import Path

RAW_DIR = Path(__file__).parent.parent / 'data' / 'raw'


def get_real_buildings(place='Landsberg am Lech, Germany', limit=1500):
    tags = {'building': True}
    try:
        gdf = ox.features_from_place(place, tags=tags)
        gdf = gdf[gdf.geometry.notnull()].head(limit)
        gdf['lat'] = gdf.geometry.centroid.y
        gdf['lon'] = gdf.geometry.centroid.x
        df = pd.DataFrame({'lat': gdf['lat'].values, 'lon': gdf['lon'].values})
        print(f'[real_data] OSMnx: {len(df)} buildings loaded for "{place}"')
        return df
    except Exception as e:
        print(f'[real_data] features_from_place failed: {e} — trying geocode fallback')
    try:
        from geo_utils import geocode_address
        geo = geocode_address(place)
        if geo:
            lat, lon = geo['lat'], geo['lon']
            gdf = ox.features_from_point((lat, lon), tags=tags, dist=2000)
            gdf = gdf[gdf.geometry.notnull()].head(limit)
            gdf['lat'] = gdf.geometry.centroid.y
            gdf['lon'] = gdf.geometry.centroid.x
            df = pd.DataFrame({'lat': gdf['lat'].values, 'lon': gdf['lon'].values})
            print(f'[real_data] fallback point query: {len(df)} buildings')
            return df
    except Exception as e2:
        print(f'[real_data] fallback also failed: {e2}')
    return pd.DataFrame(columns=['lat', 'lon'])


def get_road_network(place='Landsberg am Lech, Germany'):
    try:
        G = ox.graph_from_place(place, network_type='drive')
        print(f'[real_data] Road graph loaded for "{place}"')
        return G
    except Exception as e:
        print(f'[real_data] Road network error: {e}')
        return None


def load_breitbandatlas(filepath=None, bundesland='Bayern'):
    try:
        import geopandas as gpd
        if filepath is None:
            candidates = list(RAW_DIR.glob('breitband*.gpkg')) + list(RAW_DIR.glob('breitband*.shp'))
            if not candidates:
                print('[real_data] Breitbandatlas not in data/raw/ — download from bundesnetzagentur.de')
                return pd.DataFrame()
            filepath = str(candidates[0])
        gdf = gpd.read_file(filepath)
        if 'bundesland' in gdf.columns:
            gdf = gdf[gdf['bundesland'].str.contains(bundesland, na=False)]
        elif 'bl_name' in gdf.columns:
            gdf = gdf[gdf['bl_name'].str.contains(bundesland, na=False)]
        gdf = gdf.to_crs('EPSG:4326')
        gdf['lat'] = gdf.geometry.centroid.y
        gdf['lon'] = gdf.geometry.centroid.x
        col_map = {}
        for col in gdf.columns:
            cl = col.lower()
            if 'ftth' in cl or 'glasfaser' in cl:     col_map[col] = 'ftth_pct'
            elif 'gbit' in cl or 'gigabit' in cl:     col_map[col] = 'gbit_pct'
            elif '100' in cl and 'ant' in cl:          col_map[col] = 'coverage_100mbit'
            elif 'hh_ges' in cl or 'haushalte' in cl: col_map[col] = 'households'
            elif 'gen' == cl or 'gemeinde' in cl:     col_map[col] = 'gemeinde_name'
        gdf = gdf.rename(columns=col_map)
        keep = ['lat', 'lon'] + [c for c in ['gemeinde_name','ftth_pct','gbit_pct','coverage_100mbit','households'] if c in gdf.columns]
        df = pd.DataFrame(gdf[keep])
        if 'ftth_pct' in df.columns:
            df['coverage_gap_pct'] = (100 - df['ftth_pct'].fillna(0)).clip(0, 100)
        print(f'[real_data] Breitbandatlas: {len(df)} Gemeinden loaded')
        return df
    except Exception as e:
        print(f'[real_data] Breitbandatlas error: {e}')
        return pd.DataFrame()


def load_destatis_gemeinden(filepath=None, bundesland='Bayern'):
    try:
        if filepath is None:
            candidates = (list(RAW_DIR.glob('destatis*.xlsx')) +
                          list(RAW_DIR.glob('AuszugGV*.xlsx')) +
                          list(RAW_DIR.glob('gemeinden*.xlsx')))
            if not candidates:
                print('[real_data] Destatis file not found. Download AuszugGV.xlsx from destatis.de')
                return pd.DataFrame()
            filepath = str(candidates[0])
        df = pd.read_excel(filepath, skiprows=5, dtype=str)
        rename = {}
        for col in df.columns:
            cl = str(col).lower()
            if 'bevölkerung' in cl or 'einwohner' in cl: rename[col] = 'population'
            elif 'fläche' in cl:                          rename[col] = 'area_km2'
            elif 'gemeinde' in cl and 'name' in cl:       rename[col] = 'gemeinde_name'
            elif 'schlüssel' in cl or cl == 'rs':         rename[col] = 'gemeinde_key'
        df = df.rename(columns=rename)
        if 'gemeinde_key' in df.columns:
            df = df[df['gemeinde_key'].str.startswith('09', na=False)]
        for col in ['population', 'area_km2']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col].str.replace('.','').str.replace(',','.'), errors='coerce')
        if 'population' in df.columns and 'area_km2' in df.columns:
            df['pop_density_km2'] = (df['population'] / df['area_km2'].replace(0, np.nan)).round(1)
        print(f'[real_data] Destatis: {len(df)} Gemeinden loaded')
        return df
    except Exception as e:
        print(f'[real_data] Destatis error: {e}')
        return pd.DataFrame()


def check_data_availability():
    status = {}
    breitband = list(RAW_DIR.glob('breitband*.gpkg')) + list(RAW_DIR.glob('breitband*.shp'))
    status['breitbandatlas'] = {
        'available': bool(breitband),
        'files': [f.name for f in breitband],
        'download': 'https://bundesnetzagentur.de/breitbandatlas',
    }
    destatis = list(RAW_DIR.glob('destatis*.xlsx')) + list(RAW_DIR.glob('AuszugGV*.xlsx'))
    status['destatis'] = {
        'available': bool(destatis),
        'files': [f.name for f in destatis],
        'download': 'https://www.destatis.de/DE/Themen/Laender-Regionen/Regionales/Gemeindeverzeichnis/',
    }
    osmnx_ok = True
    try:
        import osmnx as _ox
    except ImportError:
        osmnx_ok = False
    status['osmnx'] = {'available': osmnx_ok}
    return status
