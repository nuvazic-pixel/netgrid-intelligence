from sklearn.cluster import KMeans
import pandas as pd


def kmeans_nodes(real_df: pd.DataFrame, k: int = 3) -> list[dict]:
    """Return k cluster centroids as candidate POP/splice-box nodes."""
    coords = real_df[['lat', 'lon']].values
    model = KMeans(n_clusters=k, random_state=42, n_init=10)
    model.fit(coords)
    return [{'lat': float(c[0]), 'lon': float(c[1])} for c in model.cluster_centers_]


def multi_node_coverage(road_distance_fn, G, real_df: pd.DataFrame,
                        nodes: list[dict], radius_m: float = 500) -> tuple[int, int]:
    """Count buildings reachable from ANY node within radius_m road distance."""
    covered = set()
    for i, row in real_df.iterrows():
        for node in nodes:
            dist = road_distance_fn(G, node['lat'], node['lon'], row['lat'], row['lon'])
            if dist is not None and dist <= radius_m:
                covered.add(i)
                break
    return len(covered), len(real_df)
