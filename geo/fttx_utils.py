from sklearn.cluster import KMeans
import pandas as pd


def generate_cabinets(real_df, k=10):
    coords = real_df[['lat', 'lon']].values

    model = KMeans(n_clusters=k, random_state=42, n_init=10)
    model.fit(coords)

    centers = model.cluster_centers_

    return [{'lat': float(c[0]), 'lon': float(c[1])} for c in centers]


def aggregate_buildings(real_df, k=50):
    '''
    For FTTB: group buildings into blocks
    '''
    coords = real_df[['lat', 'lon']].values

    model = KMeans(n_clusters=min(k, len(real_df)), random_state=42)
    model.fit(coords)

    real_df = real_df.copy()
    real_df['cluster'] = model.labels_

    grouped = real_df.groupby('cluster').agg({
        'lat': 'mean',
        'lon': 'mean'
    }).reset_index(drop=True)

    return grouped