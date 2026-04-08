"""
db_layer.py — SQLite + GeoPackage database layer for FTTH Platform
Realistic Bavaria Gemeinden data with proper names and coordinates
"""

import sqlite3
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Optional
import json

DB_PATH = Path(__file__).parent / "data" / "ftth_demo.db"

# ============================================================
# REALISTIC BAVARIA GEMEINDEN DATA
# Real names, real coordinates, simulated FTTH metrics
# ============================================================

BAVARIA_GEMEINDEN = [
    # Landkreis Landsberg am Lech
    {"name": "Landsberg am Lech", "lat": 48.0516, "lon": 10.8718, "landkreis": "Landsberg am Lech", "population": 29710, "area_km2": 38.41},
    {"name": "Kaufering", "lat": 48.0892, "lon": 10.8781, "landkreis": "Landsberg am Lech", "population": 10520, "area_km2": 17.89},
    {"name": "Penzing", "lat": 48.0747, "lon": 10.9314, "landkreis": "Landsberg am Lech", "population": 3890, "area_km2": 26.71},
    {"name": "Scheuring", "lat": 48.1522, "lon": 10.9142, "landkreis": "Landsberg am Lech", "population": 2180, "area_km2": 15.23},
    {"name": "Prittriching", "lat": 48.1978, "lon": 10.9289, "landkreis": "Landsberg am Lech", "population": 2640, "area_km2": 20.15},
    {"name": "Hurlach", "lat": 48.1156, "lon": 10.8247, "landkreis": "Landsberg am Lech", "population": 1920, "area_km2": 11.87},
    {"name": "Igling", "lat": 48.0389, "lon": 10.8122, "landkreis": "Landsberg am Lech", "population": 2450, "area_km2": 18.42},
    {"name": "Obermeitingen", "lat": 48.1447, "lon": 10.7889, "landkreis": "Landsberg am Lech", "population": 2210, "area_km2": 12.56},
    {"name": "Untermeitingen", "lat": 48.1614, "lon": 10.8056, "landkreis": "Landsberg am Lech", "population": 3150, "area_km2": 14.78},
    {"name": "Schwabmünchen", "lat": 48.1797, "lon": 10.7567, "landkreis": "Augsburg", "population": 14230, "area_km2": 45.23},
    {"name": "Königsbrunn", "lat": 48.2678, "lon": 10.8889, "landkreis": "Augsburg", "population": 28450, "area_km2": 17.12},
    {"name": "Gersthofen", "lat": 48.4247, "lon": 10.8722, "landkreis": "Augsburg", "population": 22890, "area_km2": 33.56},
    {"name": "Denklingen", "lat": 47.9172, "lon": 10.8514, "landkreis": "Landsberg am Lech", "population": 2870, "area_km2": 35.67},
    {"name": "Fuchstal", "lat": 47.9342, "lon": 10.8156, "landkreis": "Landsberg am Lech", "population": 3420, "area_km2": 42.13},
    {"name": "Weil", "lat": 47.9856, "lon": 10.9178, "landkreis": "Landsberg am Lech", "population": 3780, "area_km2": 29.45},
    {"name": "Reichling", "lat": 47.9014, "lon": 10.9256, "landkreis": "Landsberg am Lech", "population": 1650, "area_km2": 22.34},
    {"name": "Vilgertshofen", "lat": 47.9478, "lon": 10.9678, "landkreis": "Landsberg am Lech", "population": 1280, "area_km2": 18.92},
    {"name": "Pürgen", "lat": 48.0189, "lon": 10.9623, "landkreis": "Landsberg am Lech", "population": 3120, "area_km2": 27.81},
    {"name": "Egling an der Paar", "lat": 48.0856, "lon": 10.9789, "landkreis": "Landsberg am Lech", "population": 2340, "area_km2": 24.15},
    {"name": "Finning", "lat": 47.9889, "lon": 10.9934, "landkreis": "Landsberg am Lech", "population": 1870, "area_km2": 16.78},
    # Landkreis Weilheim-Schongau
    {"name": "Weilheim in Oberbayern", "lat": 47.8397, "lon": 11.1422, "landkreis": "Weilheim-Schongau", "population": 22450, "area_km2": 36.78},
    {"name": "Schongau", "lat": 47.8114, "lon": 10.8964, "landkreis": "Weilheim-Schongau", "population": 12340, "area_km2": 21.45},
    {"name": "Peiting", "lat": 47.7956, "lon": 10.9278, "landkreis": "Weilheim-Schongau", "population": 11780, "area_km2": 44.23},
    {"name": "Peißenberg", "lat": 47.8028, "lon": 11.0678, "landkreis": "Weilheim-Schongau", "population": 13120, "area_km2": 28.92},
    {"name": "Polling", "lat": 47.8142, "lon": 11.1567, "landkreis": "Weilheim-Schongau", "population": 3450, "area_km2": 19.34},
    # München Region (for context/comparison)
    {"name": "Starnberg", "lat": 47.9972, "lon": 11.3406, "landkreis": "Starnberg", "population": 23450, "area_km2": 25.67},
    {"name": "Gauting", "lat": 48.0692, "lon": 11.3778, "landkreis": "Starnberg", "population": 21230, "area_km2": 28.45},
    {"name": "Germering", "lat": 48.1333, "lon": 11.3667, "landkreis": "Fürstenfeldbruck", "population": 41230, "area_km2": 21.89},
    {"name": "Fürstenfeldbruck", "lat": 48.1789, "lon": 11.2553, "landkreis": "Fürstenfeldbruck", "population": 36780, "area_km2": 32.45},
    {"name": "Buchloe", "lat": 48.0364, "lon": 10.7253, "landkreis": "Ostallgäu", "population": 13450, "area_km2": 24.12},
]


def _generate_ftth_metrics(gemeinde: dict, seed_offset: int = 0) -> dict:
    """Generate realistic FTTH metrics based on gemeinde characteristics."""
    np.random.seed(hash(gemeinde["name"]) % 2**32 + seed_offset)
    
    pop = gemeinde["population"]
    area = gemeinde["area_km2"]
    pop_density = pop / area
    
    # Larger cities → better existing coverage
    if pop > 20000:
        existing_coverage = np.random.uniform(60, 85)
        status = np.random.choice(["deployed", "partial"], p=[0.7, 0.3])
    elif pop > 10000:
        existing_coverage = np.random.uniform(40, 70)
        status = np.random.choice(["deployed", "partial", "planned"], p=[0.3, 0.5, 0.2])
    elif pop > 5000:
        existing_coverage = np.random.uniform(25, 55)
        status = np.random.choice(["partial", "planned"], p=[0.6, 0.4])
    else:
        existing_coverage = np.random.uniform(10, 40)
        status = np.random.choice(["planned", "unplanned", "partial"], p=[0.4, 0.4, 0.2])
    
    # Homes estimate (~2.3 persons per household in Bavaria)
    homes = int(pop / 2.3)
    homes_passed = int(homes * existing_coverage / 100 * np.random.uniform(0.8, 1.0))
    
    # Adoption correlates with density and income proxy
    base_adoption = 25 + (pop_density / 50) * 10 + np.random.uniform(-5, 15)
    adoption = np.clip(base_adoption, 15, 75)
    
    # Distance to infrastructure
    if status == "deployed":
        avg_dist_m = int(np.random.uniform(100, 400))
    elif status == "partial":
        avg_dist_m = int(np.random.uniform(300, 800))
    else:
        avg_dist_m = int(np.random.uniform(600, 1500))
    
    # Income estimate (higher near Munich, Starnberg)
    if gemeinde["landkreis"] in ["Starnberg", "Fürstenfeldbruck"]:
        avg_income = int(np.random.uniform(52000, 72000))
    elif gemeinde["landkreis"] == "Augsburg":
        avg_income = int(np.random.uniform(42000, 55000))
    else:
        avg_income = int(np.random.uniform(36000, 48000))
    
    # Competitor presence
    if pop > 15000:
        competitor_coverage = np.random.uniform(30, 60)
    else:
        competitor_coverage = np.random.uniform(5, 35)
    
    return {
        "homes": homes,
        "homes_passed": homes_passed,
        "existing_coverage_pct": round(existing_coverage, 1),
        "adoption_pct": round(adoption, 1),
        "avg_dist_m": avg_dist_m,
        "avg_household_income": avg_income,
        "competitor_coverage_pct": round(competitor_coverage, 1),
        "pop_density_km2": round(pop_density, 1),
        "status": status,
    }


def init_database(force_recreate: bool = False) -> None:
    """Initialize SQLite database with realistic Bavaria data."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    
    if DB_PATH.exists() and not force_recreate:
        print(f"Database already exists: {DB_PATH}")
        return
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Create tables
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS gemeinden (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            lat REAL NOT NULL,
            lon REAL NOT NULL,
            landkreis TEXT,
            population INTEGER,
            area_km2 REAL,
            homes INTEGER,
            homes_passed INTEGER,
            existing_coverage_pct REAL,
            adoption_pct REAL,
            avg_dist_m INTEGER,
            avg_household_income INTEGER,
            competitor_coverage_pct REAL,
            pop_density_km2 REAL,
            status TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ai_recommendations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            gemeinde_id INTEGER,
            agent_name TEXT,
            vote TEXT,
            confidence REAL,
            reasoning TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (gemeinde_id) REFERENCES gemeinden(id)
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS swarm_decisions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            gemeinde_id INTEGER,
            final_decision TEXT,
            consensus_score REAL,
            votes_json TEXT,
            reasoning TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (gemeinde_id) REFERENCES gemeinden(id)
        )
    """)
    
    # Insert realistic data
    for gemeinde in BAVARIA_GEMEINDEN:
        metrics = _generate_ftth_metrics(gemeinde)
        cursor.execute("""
            INSERT INTO gemeinden (
                name, lat, lon, landkreis, population, area_km2,
                homes, homes_passed, existing_coverage_pct, adoption_pct,
                avg_dist_m, avg_household_income, competitor_coverage_pct,
                pop_density_km2, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            gemeinde["name"], gemeinde["lat"], gemeinde["lon"],
            gemeinde["landkreis"], gemeinde["population"], gemeinde["area_km2"],
            metrics["homes"], metrics["homes_passed"], metrics["existing_coverage_pct"],
            metrics["adoption_pct"], metrics["avg_dist_m"], metrics["avg_household_income"],
            metrics["competitor_coverage_pct"], metrics["pop_density_km2"], metrics["status"]
        ))
    
    conn.commit()
    conn.close()
    print(f"Database initialized with {len(BAVARIA_GEMEINDEN)} Gemeinden: {DB_PATH}")


def get_all_gemeinden() -> pd.DataFrame:
    """Load all Gemeinden from database."""
    init_database()
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("SELECT * FROM gemeinden ORDER BY population DESC", conn)
    conn.close()
    return df


def get_gemeinde_by_id(gemeinde_id: int) -> Optional[dict]:
    """Get single Gemeinde by ID."""
    init_database()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM gemeinden WHERE id = ?", (gemeinde_id,))
    row = cursor.fetchone()
    conn.close()
    
    if row:
        columns = [desc[0] for desc in cursor.description]
        return dict(zip(columns, row))
    return None


def save_swarm_decision(gemeinde_id: int, decision: str, consensus: float, 
                        votes: dict, reasoning: str) -> int:
    """Save AI swarm decision to database."""
    init_database()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO swarm_decisions (gemeinde_id, final_decision, consensus_score, votes_json, reasoning)
        VALUES (?, ?, ?, ?, ?)
    """, (gemeinde_id, decision, consensus, json.dumps(votes), reasoning))
    conn.commit()
    decision_id = cursor.lastrowid
    conn.close()
    return decision_id


def get_swarm_decisions(gemeinde_id: Optional[int] = None) -> pd.DataFrame:
    """Get AI swarm decisions, optionally filtered by Gemeinde."""
    init_database()
    conn = sqlite3.connect(DB_PATH)
    
    if gemeinde_id:
        df = pd.read_sql_query(
            "SELECT * FROM swarm_decisions WHERE gemeinde_id = ? ORDER BY created_at DESC",
            conn, params=(gemeinde_id,)
        )
    else:
        df = pd.read_sql_query(
            "SELECT * FROM swarm_decisions ORDER BY created_at DESC", conn
        )
    conn.close()
    return df


# ============================================================
# ZONE DATA (for compatibility with existing app)
# ============================================================

def get_zone_df() -> pd.DataFrame:
    """Get zone data for Streamlit app (compatibility layer)."""
    df = get_all_gemeinden()
    
    # Map to expected column names
    zone_df = pd.DataFrame({
        "id": df["id"],
        "name": df["name"],
        "lat": df["lat"],
        "lon": df["lon"],
        "landkreis": df["landkreis"],
        "homes": df["homes"],
        "density": df["pop_density_km2"].apply(
            lambda x: "high" if x > 500 else "medium" if x > 200 else "low"
        ),
        "status": df["status"],
        "adoption": df["adoption_pct"],
        "avg_dist_m": df["avg_dist_m"],
        "population": df["population"],
        "avg_household_income": df["avg_household_income"],
        "existing_coverage_pct": df["existing_coverage_pct"],
        "competitor_coverage_pct": df["competitor_coverage_pct"],
    })
    
    return zone_df


if __name__ == "__main__":
    # Test database initialization
    init_database(force_recreate=True)
    
    df = get_all_gemeinden()
    print(f"\nLoaded {len(df)} Gemeinden:")
    print(df[["name", "landkreis", "population", "status", "adoption_pct"]].head(15))
    
    print(f"\nZone data shape: {get_zone_df().shape}")
