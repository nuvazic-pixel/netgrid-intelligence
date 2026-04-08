import pandas as pd

ZONES = [
    {'name': 'Landsberg Innenstadt', 'homes': 2100, 'density': 'High',   'adoption': 62, 'avg_dist_m': 180,  'status': 'deployed',  'lat': 48.0529, 'lon': 10.8727},
    {'name': 'Kaufering Nord',       'homes': 1450, 'density': 'Medium', 'adoption': 51, 'avg_dist_m': 320,  'status': 'partial',   'lat': 48.0872, 'lon': 10.8801},
    {'name': 'Kaufering Süd',        'homes': 980,  'density': 'Medium', 'adoption': 44, 'avg_dist_m': 410,  'status': 'planned',   'lat': 48.0741, 'lon': 10.8780},
    {'name': 'Penzing',              'homes': 620,  'density': 'Low',    'adoption': 38, 'avg_dist_m': 680,  'status': 'unplanned', 'lat': 48.0631, 'lon': 10.9102},
    {'name': 'Igling',               'homes': 390,  'density': 'Low',    'adoption': 31, 'avg_dist_m': 920,  'status': 'unplanned', 'lat': 48.0412, 'lon': 10.8543},
    {'name': 'Obermühlhausen',       'homes': 280,  'density': 'Rural',  'adoption': 22, 'avg_dist_m': 1240, 'status': 'unplanned', 'lat': 48.0198, 'lon': 10.9015},
]


def get_zone_df() -> pd.DataFrame:
    return pd.DataFrame(ZONES)
