"""
zone_data.py — Zone data generation for FTTH Expansion Platform
Generates synthetic zone data for Landsberg am Lech area
"""

import pandas as pd
import numpy as np

np.random.seed(42)


def get_zone_df() -> pd.DataFrame:
    """
    Returns a DataFrame with synthetic zone data for Landsberg am Lech region.
    Each zone represents a district/Ortsteil with FTTH deployment metrics.
    """
    
    # Real Ortsteile around Landsberg am Lech
    zones = [
        # name, lat, lon, base_homes, density_class
        ("Landsberg Zentrum",     48.0520, 10.8700, 2200, "high"),
        ("Landsberg West",        48.0500, 10.8550, 1400, "medium"),
        ("Landsberg Ost",         48.0540, 10.8900, 1100, "medium"),
        ("Kaufering",             48.0900, 10.8550, 1800, "medium"),
        ("Penzing",               48.0750, 10.9200, 650,  "low"),
        ("Igling",                48.0350, 10.8100, 420,  "low"),
        ("Hurlach",               48.1100, 10.8100, 380,  "low"),
        ("Scheuring",             48.1500, 10.8300, 340,  "low"),
        ("Prittriching",          48.1950, 10.9000, 450,  "low"),
        ("Pürgen",                48.0150, 10.9600, 520,  "low"),
        ("Weil",                  47.9800, 10.9100, 600,  "low"),
        ("Denklingen",            47.9200, 10.8500, 480,  "low"),
        ("Reichling",             47.9000, 10.9200, 350,  "low"),
        ("Vilgertshofen",         47.9400, 10.9700, 280,  "low"),
        ("Schwifting",            48.0100, 10.7800, 220,  "low"),
    ]
    
    records = []
    for name, lat, lon, homes, density in zones:
        # Randomize slightly for realism
        homes_actual = int(homes * np.random.uniform(0.9, 1.1))
        
        # Status based on location (center = deployed, further = less)
        dist_from_center = np.sqrt((lat - 48.052)**2 + (lon - 10.87)**2) * 111  # rough km
        if dist_from_center < 5:
            status = np.random.choice(["deployed", "partial"], p=[0.7, 0.3])
        elif dist_from_center < 12:
            status = np.random.choice(["partial", "planned", "deployed"], p=[0.4, 0.4, 0.2])
        else:
            status = np.random.choice(["planned", "unplanned"], p=[0.4, 0.6])
        
        # Adoption rate: higher in deployed areas, varies by density
        base_adoption = {
            "deployed": np.random.uniform(45, 65),
            "partial": np.random.uniform(30, 50),
            "planned": np.random.uniform(20, 40),
            "unplanned": np.random.uniform(15, 30),
        }[status]
        
        # Density bonus
        density_bonus = {"high": 10, "medium": 5, "low": 0}[density]
        adoption = min(80, base_adoption + density_bonus + np.random.uniform(-5, 5))
        
        # Average distance to infrastructure
        avg_dist_m = int(dist_from_center * 80 + np.random.uniform(100, 400))
        
        records.append({
            "name": name,
            "lat": lat,
            "lon": lon,
            "homes": homes_actual,
            "density": density,
            "status": status,
            "adoption": round(adoption, 1),
            "avg_dist_m": avg_dist_m,
        })
    
    return pd.DataFrame(records)


def get_gemeinden_df() -> pd.DataFrame:
    """
    Returns the full Gemeinden dataset for ML pipeline.
    Generates synthetic data matching the notebooks' structure.
    """
    N = 500
    np.random.seed(42)
    
    # Bavaria bounding box
    lats = np.random.uniform(47.3, 50.6, N)
    lons = np.random.uniform(9.9, 13.9, N)
    
    # Demographic features
    population = np.random.lognormal(mean=7.5, sigma=1.2, size=N).astype(int).clip(200, 80000)
    pop_density = np.random.lognormal(mean=4.5, sigma=1.0, size=N).clip(20, 3000)
    avg_household_income = np.random.normal(38000, 8000, N).clip(22000, 70000)
    share_over_65 = np.random.beta(3, 7, N) * 40
    share_under_18 = np.random.beta(4, 8, N) * 30
    unemployment_rate = np.random.beta(2, 20, N) * 10
    
    # Infrastructure features
    existing_coverage_pct = np.random.beta(4, 2, N) * 100
    dist_to_pop_node_m = np.random.lognormal(mean=6.0, sigma=0.8, size=N).clip(50, 8000)
    dist_to_cabinet_m = np.random.lognormal(mean=5.2, sigma=0.7, size=N).clip(30, 2000)
    homes_passed = (population * np.random.uniform(0.3, 0.45, N)).astype(int)
    
    # Geospatial features
    building_density = pop_density * np.random.uniform(0.2, 0.5, N)
    terrain_slope_deg = np.random.lognormal(mean=1.5, sigma=0.8, size=N).clip(0, 35)
    road_length_km = np.random.lognormal(mean=4.0, sigma=0.7, size=N).clip(1, 200)
    
    # Competition
    competitor_coverage = np.random.beta(2, 3, N) * 80
    
    # Target: FTTH adoption rate
    adoption_rate = (
        0.25 * (pop_density / pop_density.max()) +
        0.20 * (avg_household_income / avg_household_income.max()) +
        0.15 * (1 - dist_to_pop_node_m / dist_to_pop_node_m.max()) +
        0.12 * (building_density / building_density.max()) +
        0.10 * (1 - existing_coverage_pct / 100) +
        0.08 * (1 - competitor_coverage / 80) +
        0.10 * np.random.normal(0, 0.05, N)
    ) * 100
    adoption_rate = adoption_rate.clip(5, 85)
    
    return pd.DataFrame({
        'gemeinde_id': range(N),
        'name': [f'Gemeinde_{i:04d}' for i in range(N)],
        'lat': lats,
        'lon': lons,
        'population': population,
        'pop_density_km2': pop_density.round(1),
        'avg_household_income': avg_household_income.round(0).astype(int),
        'share_over_65_pct': share_over_65.round(1),
        'share_under_18_pct': share_under_18.round(1),
        'unemployment_rate_pct': unemployment_rate.round(2),
        'existing_coverage_pct': existing_coverage_pct.round(1),
        'dist_to_pop_node_m': dist_to_pop_node_m.round(0).astype(int),
        'dist_to_cabinet_m': dist_to_cabinet_m.round(0).astype(int),
        'homes_passed': homes_passed,
        'building_density': building_density.round(1),
        'terrain_slope_deg': terrain_slope_deg.round(2),
        'road_length_km': road_length_km.round(2),
        'competitor_coverage_pct': competitor_coverage.round(1),
        'adoption_rate_pct': adoption_rate.round(2),
    })


if __name__ == "__main__":
    zone_df = get_zone_df()
    print("Zone DataFrame:")
    print(zone_df.to_string())
    print(f"\nShape: {zone_df.shape}")
