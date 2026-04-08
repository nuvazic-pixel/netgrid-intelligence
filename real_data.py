"""
real_data.py — Real building data fetching for FTTH Expansion Platform
Uses OSMnx for building footprints (optional, with fallback to synthetic)
"""

import pandas as pd
import numpy as np
from typing import Optional

# Flag to control real data fetching (set to False for demo mode)
USE_REAL_OSM = False


def get_real_buildings(
    address: str = "Landsberg am Lech, Bavaria, Germany",
    radius_m: int = 3000,
    use_cache: bool = True
) -> pd.DataFrame:
    """
    Fetch building footprints from OpenStreetMap via OSMnx.
    Falls back to synthetic data if OSMnx is unavailable or fails.
    
    Returns DataFrame with columns: lat, lon, building_type, area_m2
    """
    
    if USE_REAL_OSM:
        try:
            return _fetch_osm_buildings(address, radius_m)
        except Exception as e:
            print(f"OSMnx fetch failed: {e}")
            print("Falling back to synthetic buildings.")
    
    # Synthetic fallback
    return _generate_synthetic_buildings(address, radius_m)


def _fetch_osm_buildings(address: str, radius_m: int) -> pd.DataFrame:
    """
    Real OSMnx building fetch — requires network and osmnx installed.
    """
    import osmnx as ox
    
    # Get buildings
    buildings = ox.geometries_from_address(
        address,
        tags={"building": True},
        dist=radius_m
    )
    
    if buildings.empty:
        raise ValueError("No buildings found in area")
    
    # Extract centroids
    buildings = buildings.to_crs("EPSG:4326")
    centroids = buildings.geometry.centroid
    
    # Build DataFrame
    df = pd.DataFrame({
        "lat": centroids.y,
        "lon": centroids.x,
        "building_type": buildings.get("building", "unknown"),
        "area_m2": buildings.geometry.area if "area" in buildings.columns else np.nan,
    })
    
    return df.reset_index(drop=True)


def _generate_synthetic_buildings(address: str, radius_m: int) -> pd.DataFrame:
    """
    Generate synthetic building data for demo/testing.
    Clustered around Landsberg am Lech center.
    """
    np.random.seed(42)
    
    # Center coordinates (Landsberg)
    center_lat = 48.0520
    center_lon = 10.8700
    
    # Generate ~500 buildings in clusters
    n_buildings = 500
    
    # Create clusters (representing neighborhoods)
    cluster_centers = [
        (center_lat, center_lon),                    # Zentrum
        (center_lat - 0.015, center_lon - 0.012),    # Southwest
        (center_lat + 0.018, center_lon - 0.008),    # North (Kaufering direction)
        (center_lat - 0.008, center_lon + 0.015),    # East
        (center_lat + 0.008, center_lon + 0.005),    # Northeast
    ]
    
    # Building types with probabilities
    building_types = ["residential", "residential", "residential", "residential",
                      "commercial", "industrial", "retail", "apartment"]
    
    records = []
    for i in range(n_buildings):
        # Pick a cluster
        cluster_idx = np.random.choice(len(cluster_centers), p=[0.35, 0.2, 0.2, 0.15, 0.1])
        c_lat, c_lon = cluster_centers[cluster_idx]
        
        # Add noise within cluster
        lat = c_lat + np.random.normal(0, 0.008)
        lon = c_lon + np.random.normal(0, 0.010)
        
        # Random building type and area
        btype = np.random.choice(building_types)
        if btype == "residential":
            area = np.random.uniform(80, 200)
        elif btype == "apartment":
            area = np.random.uniform(300, 1500)
        elif btype == "commercial":
            area = np.random.uniform(200, 800)
        else:
            area = np.random.uniform(500, 3000)
        
        records.append({
            "lat": round(lat, 6),
            "lon": round(lon, 6),
            "building_type": btype,
            "area_m2": round(area, 1),
        })
    
    return pd.DataFrame(records)


def get_road_network(
    address: str = "Landsberg am Lech, Bavaria, Germany",
    network_type: str = "drive"
) -> Optional[object]:
    """
    Fetch road network graph from OSMnx.
    Returns NetworkX graph or None if unavailable.
    """
    if not USE_REAL_OSM:
        return None
    
    try:
        import osmnx as ox
        G = ox.graph_from_address(address, network_type=network_type, dist=5000)
        return G
    except Exception as e:
        print(f"Road network fetch failed: {e}")
        return None


def road_distance(
    G,  # NetworkX graph
    lat1: float, lon1: float,
    lat2: float, lon2: float
) -> Optional[float]:
    """
    Calculate road network distance between two points.
    Returns distance in meters, or None if no path found.
    """
    if G is None:
        return None
    
    try:
        import osmnx as ox
        
        # Find nearest nodes
        node1 = ox.nearest_nodes(G, lon1, lat1)
        node2 = ox.nearest_nodes(G, lon2, lat2)
        
        # Shortest path length
        import networkx as nx
        length = nx.shortest_path_length(G, node1, node2, weight="length")
        return length
    except Exception:
        return None


if __name__ == "__main__":
    # Test synthetic buildings
    df = get_real_buildings()
    print(f"Buildings: {len(df)}")
    print(df.head())
    print(f"\nBuilding types:\n{df['building_type'].value_counts()}")
