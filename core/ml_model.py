"""
ml_model.py
===========
Real ML pipeline for FTTH adoption rate prediction.

Model      : RandomForestRegressor (primary) + XGBoost (secondary)
Features   : spatial + demographic + infrastructure + competition
Target     : adoption_rate_pct (continuous, 0–100)
Persistence: joblib .pkl with versioning
Evaluation : MAE, RMSE, R², cross-validation

Part of: FTTH/FTTx Intelligence Platform
"""

import os
import json
import joblib
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime

from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.model_selection import train_test_split, cross_val_score, KFold
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline

try:
    import xgboost as xgb
    XGB_AVAILABLE = True
except ImportError:
    XGB_AVAILABLE = False

MODELS_DIR = Path(__file__).parent / 'models'
MODELS_DIR.mkdir(exist_ok=True)

FEATURE_COLS = [
    'density_num',
    'competition_num',
    'avg_distance_norm',
    'capex_norm',
    'income_norm',
    'coverage_gap',
    'terrain_slope',
    'road_length_norm',
]

RANDOM_SEED = 42


# ── 1. FEATURE ENGINEERING ───────────────────────────────────────────────────

def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Transform raw zone/building DataFrame into ML-ready features.
    Handles both zone_df columns and planning_df columns.
    """
    df = df.copy()

    # Density → ordinal
    density_map = {'Rural': 0, 'Low': 1, 'Medium': 2, 'High': 3}
    if 'density' in df.columns:
        df['density_num'] = df['density'].map(density_map).fillna(1).astype(int)
    else:
        df['density_num'] = 1

    # Competition → ordinal
    comp_map = {'Low': 0, 'Medium': 1, 'High': 2}
    if 'competition' in df.columns:
        df['competition_num'] = df['competition'].map(comp_map).fillna(1).astype(int)
    else:
        df['competition_num'] = 1

    # Distance → normalised 0–1
    dist_col = 'avg_dist_m' if 'avg_dist_m' in df.columns else 'avg_distance'
    if dist_col in df.columns:
        df['avg_distance_norm'] = (df[dist_col].clip(0, 3000) / 3000).round(4)
    else:
        df['avg_distance_norm'] = 0.3

    # CAPEX → normalised
    if 'Est. CAPEX (€K)' in df.columns:
        df['capex_norm'] = (df['Est. CAPEX (€K)'].clip(0, 5000) / 5000).round(4)
    elif 'capex' in df.columns:
        df['capex_norm'] = (pd.to_numeric(df['capex'], errors='coerce').fillna(900).clip(0, 5000) / 5000).round(4)
    else:
        df['capex_norm'] = 0.18

    # Income → normalised
    if 'avg_household_income' in df.columns:
        df['income_norm'] = (df['avg_household_income'].clip(15000, 80000) - 15000) / 65000
    else:
        df['income_norm'] = 0.35

    # Coverage gap
    if 'coverage_gap_pct' in df.columns:
        df['coverage_gap'] = (df['coverage_gap_pct'].clip(0, 100) / 100).round(4)
    else:
        df['coverage_gap'] = 0.50

    # Terrain slope (0 if not available)
    if 'terrain_slope_deg' in df.columns:
        df['terrain_slope'] = (df['terrain_slope_deg'].clip(0, 35) / 35).round(4)
    else:
        df['terrain_slope'] = 0.10

    # Road length → normalised
    if 'road_length_km' in df.columns:
        df['road_length_norm'] = (df['road_length_km'].clip(0, 200) / 200).round(4)
    else:
        df['road_length_norm'] = 0.15

    return df


def get_feature_matrix(df: pd.DataFrame) -> pd.DataFrame:
    df = engineer_features(df)
    available = [c for c in FEATURE_COLS if c in df.columns]
    return df[available].fillna(0)


# ── 2. SYNTHETIC TRAINING DATA ───────────────────────────────────────────────

def generate_training_data(n: int = 600, seed: int = RANDOM_SEED) -> pd.DataFrame:
    """
    Generate realistic synthetic training data calibrated to Bavarian municipalities.
    Used when real historical adoption data is not yet available.
    """
    rng = np.random.default_rng(seed)

    density_labels = rng.choice(['Rural', 'Low', 'Medium', 'High'],
                                  size=n, p=[0.15, 0.25, 0.40, 0.20])
    comp_labels    = rng.choice(['Low', 'Medium', 'High'],
                                  size=n, p=[0.35, 0.45, 0.20])

    density_map = {'Rural': 0, 'Low': 1, 'Medium': 2, 'High': 3}
    comp_map    = {'Low': 0, 'Medium': 1, 'High': 2}

    density_num  = np.array([density_map[d] for d in density_labels])
    comp_num     = np.array([comp_map[c] for c in comp_labels])
    dist_norm    = rng.beta(2, 3, n).round(4)
    capex_norm   = rng.beta(2, 4, n).round(4)
    income_norm  = rng.beta(3, 3, n).round(4)
    coverage_gap = rng.beta(3, 2, n).round(4)
    terrain      = rng.beta(1, 4, n).round(4)
    road_norm    = rng.beta(2, 3, n).round(4)

    # Ground truth adoption rate (with realistic noise)
    adoption = (
        0.30 +
        density_num  * 0.08 +
        income_norm  * 0.12 +
        (1 - dist_norm) * 0.10 +
        coverage_gap * 0.08 +
        (1 - comp_num / 2) * 0.10 +
        (1 - terrain)      * 0.04 +
        road_norm          * 0.03 +
        rng.normal(0, 0.04, n)
    ) * 100

    adoption = np.clip(adoption, 8, 88)

    return pd.DataFrame({
        'density':              density_labels,
        'competition':          comp_labels,
        'density_num':          density_num,
        'competition_num':      comp_num,
        'avg_distance_norm':    dist_norm,
        'capex_norm':           capex_norm,
        'income_norm':          income_norm,
        'coverage_gap':         coverage_gap,
        'terrain_slope':        terrain,
        'road_length_norm':     road_norm,
        'adoption_rate_pct':    adoption.round(2),
    })


# ── 3. TRAIN MODEL ────────────────────────────────────────────────────────────

def train_model(df: pd.DataFrame | None = None,
                model_type: str = 'rf') -> dict:
    """
    Train RandomForest or XGBoost on provided df or synthetic data.

    Returns dict with keys:
        model, scaler, mae, rmse, r2, cv_r2, feature_importance, trained_at
    """
    if df is None or len(df) < 20:
        print(f'Using synthetic training data (provided: {len(df) if df is not None else 0} rows)')
        train_df = generate_training_data(n=600)
    else:
        train_df = engineer_features(df)

    available_feats = [c for c in FEATURE_COLS if c in train_df.columns]
    X = train_df[available_feats].fillna(0).values

    target_col = 'adoption_rate_pct' if 'adoption_rate_pct' in train_df.columns else 'predicted_take_rate'
    if target_col not in train_df.columns:
        raise ValueError(f'Target column not found. Expected: adoption_rate_pct or predicted_take_rate')

    y = train_df[target_col].values

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.20, random_state=RANDOM_SEED
    )

    # Select model
    if model_type == 'xgb' and XGB_AVAILABLE:
        model = xgb.XGBRegressor(
            n_estimators=300,
            max_depth=4,
            learning_rate=0.05,
            subsample=0.8,
            colsample_bytree=0.7,
            random_state=RANDOM_SEED,
            verbosity=0,
        )
    else:
        model = RandomForestRegressor(
            n_estimators=300,
            max_depth=8,
            min_samples_leaf=4,
            max_features=0.6,
            random_state=RANDOM_SEED,
            n_jobs=-1,
        )

    model.fit(X_train, y_train)
    y_pred = model.predict(X_test)

    mae  = mean_absolute_error(y_test, y_pred)
    rmse = np.sqrt(mean_squared_error(y_test, y_pred))
    r2   = r2_score(y_test, y_pred)

    # 5-fold cross-validation
    cv    = KFold(n_splits=5, shuffle=True, random_state=RANDOM_SEED)
    cv_r2 = cross_val_score(model, X, y, cv=cv, scoring='r2', n_jobs=-1)

    # Feature importance
    if hasattr(model, 'feature_importances_'):
        fi = dict(zip(available_feats, model.feature_importances_.round(4)))
    else:
        fi = {}

    result = {
        'model':              model,
        'feature_cols':       available_feats,
        'mae':                round(mae, 3),
        'rmse':               round(rmse, 3),
        'r2':                 round(r2, 4),
        'cv_r2_mean':         round(cv_r2.mean(), 4),
        'cv_r2_std':          round(cv_r2.std(), 4),
        'feature_importance': fi,
        'model_type':         model_type if (model_type == 'xgb' and XGB_AVAILABLE) else 'rf',
        'n_train':            len(X_train),
        'trained_at':         datetime.now().isoformat(),
    }

    return result


# ── 4. PREDICT ────────────────────────────────────────────────────────────────

def predict_with_model(df: pd.DataFrame, model_result: dict) -> pd.DataFrame:
    """
    Run predictions on df using trained model.
    Adds columns: ml_adoption_pct, ml_take_rate
    """
    df    = engineer_features(df.copy())
    feats = model_result['feature_cols']
    X     = df[[c for c in feats if c in df.columns]].fillna(0).values

    preds = model_result['model'].predict(X)
    preds = np.clip(preds, 5, 90)

    df['ml_adoption_pct'] = preds.round(2)
    df['ml_take_rate']    = (preds / 100).round(4)

    return df


# ── 5. SAVE & LOAD ────────────────────────────────────────────────────────────

def save_model(model_result: dict, name: str = 'ftth_model') -> Path:
    """Save model + metadata to models/ directory."""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    pkl_path  = MODELS_DIR / f'{name}_{timestamp}.pkl'
    meta_path = MODELS_DIR / f'{name}_{timestamp}_meta.json'

    joblib.dump(model_result['model'], pkl_path)

    meta = {k: v for k, v in model_result.items() if k != 'model'}
    with open(meta_path, 'w') as f:
        json.dump(meta, f, indent=2)

    # Save pointer to latest
    latest_path = MODELS_DIR / f'{name}_latest.pkl'
    joblib.dump(model_result['model'], latest_path)

    print(f'Model saved → {pkl_path}')
    print(f'Meta  saved → {meta_path}')
    return pkl_path


def load_latest_model(name: str = 'ftth_model') -> dict | None:
    """Load the most recent saved model."""
    latest_path = MODELS_DIR / f'{name}_latest.pkl'
    if not latest_path.exists():
        return None

    model = joblib.load(latest_path)

    # Find matching meta file
    meta_files = sorted(MODELS_DIR.glob(f'{name}_*_meta.json'), reverse=True)
    meta = {}
    if meta_files:
        with open(meta_files[0]) as f:
            meta = json.load(f)

    meta['model'] = model
    return meta


# ── 6. FULL PIPELINE SHORTCUT ─────────────────────────────────────────────────

def run_ml_pipeline(df: pd.DataFrame,
                    model_type: str = 'rf',
                    save: bool = True) -> tuple[pd.DataFrame, dict]:
    """
    Train → Predict → (optionally Save).
    Returns (enriched_df, model_result).
    """
    model_result = train_model(df, model_type=model_type)
    df_pred      = predict_with_model(df, model_result)

    if save:
        save_model(model_result)

    return df_pred, model_result


# ── 7. FEATURE IMPORTANCE SUMMARY ────────────────────────────────────────────

def feature_importance_df(model_result: dict) -> pd.DataFrame:
    """Return feature importance as sorted DataFrame for display."""
    fi   = model_result.get('feature_importance', {})
    if not fi:
        return pd.DataFrame()

    df_fi = pd.DataFrame(
        list(fi.items()), columns=['feature', 'importance']
    ).sort_values('importance', ascending=False)

    df_fi['importance_pct'] = (df_fi['importance'] / df_fi['importance'].sum() * 100).round(1)
    df_fi['cumulative_pct'] = df_fi['importance_pct'].cumsum().round(1)
    df_fi['vital']          = df_fi['cumulative_pct'] <= 80

    return df_fi.reset_index(drop=True)
