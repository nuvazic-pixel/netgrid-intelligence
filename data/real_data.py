from numpy import place
import osmnx as ox
import pandas as pd
from shapely.geometry import point


def get_real_buildings(place: str = 'Landsberg am Lech, Germany', limit: int = 1500) -> pd.DataFrame:
    """Fetch real building footprints from OpenStreetMap via OSMnx."""
    tags = {'building': True}
    try:
        gdf = ox.features_from_place(place, tags=tags)
    except Exception:
        point = (lat, lon)
        gdf = ox.features_from_point(point, tags=tags, dist=2000)    
        gdf = gdf[gdf.geometry.notnull()]
        gdf = gdf.head(limit)
        gdf['lat'] = gdf.geometry.centroid.y
        gdf['lon'] = gdf.geometry.centroid.x
        return pd.DataFrame({'lat': gdf['lat'], 'lon': gdf['lon']})
    except Exception as e:
        print(f'OSM fetch error: {e}')
        return pd.DataFrame(columns=['lat', 'lon'])

def get_road_network(place: str = 'Landsberg am Lech, Germany'):
    """Fetch drive network for a place. Returns OSMnx graph."""
    try:
        G = ox.graph_from_place(place, network_type='drive')
        return G
    except Exception as e:
        print(f'OSM road network error: {e}')
        return None
