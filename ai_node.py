import pandas as pd
import numpy as np


def find_optimal_node(real_df):
    """
    Simple AI logic:
    - Finds centroid of all buildings
    - Minimizes average distance
    """

    if real_df.empty:
        return None

    center_lat = real_df['lat'].mean()
    center_lon = real_df['lon'].mean()

    return {
        'lat': center_lat,
        'lon': center_lon
    }


def calculate_coverage(real_df, node, radius_m=500):
    """
    Calculates how many buildings are covered within radius
    """

    if real_df.empty or node is None:
        return 0, 0

    def haversine(lat1, lon1, lat2, lon2):
        import math
        R = 6371000
        phi1, phi2 = math.radians(lat1), math.radians(lat2)
        dphi = math.radians(lat2 - lat1)
        dlambda = math.radians(lon2 - lon1)

        a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
        return R * 2 * math.atan2(np.sqrt(a), np.sqrt(1-a))

    distances = real_df.apply(
        lambda r: haversine(r['lat'], r['lon'], node['lat'], node['lon']),
        axis=1
    )

    covered = (distances <= radius_m).sum()
    total = len(real_df)

    return covered, total