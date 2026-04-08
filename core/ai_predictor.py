"""
ai_predictor.py
===============
Heuristic adoption model + risk engine + decision layer.
Used as baseline before ML model kicks in, and as fallback
when training data is insufficient.

Part of: FTTH/FTTx Intelligence Platform
"""

import pandas as pd
import numpy as np


# ── 1. ADOPTION MODEL ─────────────────────────────────────────────────────────

def predict_adoption(row: dict) -> float:
    """
    Rule-based adoption rate estimator.
    Returns float between 0.1 and 0.9.
    """
    base = 0.40  # Bavarian market baseline

    # Density impact
    density_delta = {'High': +0.20, 'Medium': +0.10, 'Low': -0.10, 'Rural': -0.15}
    base += density_delta.get(row.get('density', 'Medium'), 0.0)

    # Competition impact
    comp_delta = {'High': -0.20, 'Medium': -0.10, 'Low': +0.10}
    base += comp_delta.get(row.get('competition', 'Medium'), 0.0)

    # Infrastructure distance proxy (cost / friction)
    dist = row.get('avg_distance', row.get('avg_dist_m', 500))
    if dist > 800:
        base -= 0.10
    elif dist > 400:
        base -= 0.05
    elif dist < 200:
        base += 0.08

    # Income signal
    income = row.get('avg_household_income', 38000)
    if income > 50000:
        base += 0.05
    elif income < 28000:
        base -= 0.05

    # Existing coverage gap (more gap = more opportunity)
    gap = row.get('coverage_gap_pct', 50)
    base += (gap - 50) * 0.001

    return float(np.clip(base, 0.10, 0.90))


def apply_adoption_model(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df['predicted_take_rate'] = df.apply(predict_adoption, axis=1)
    return df


# ── 2. RISK MODEL ─────────────────────────────────────────────────────────────

def calculate_risk(row: dict) -> int:
    """
    Composite risk score 0–8.
    Higher = riskier investment.
    """
    risk = 0

    # Adoption risk
    take = row.get('predicted_take_rate', 0.4)
    if take < 0.30:
        risk += 2
    elif take < 0.45:
        risk += 1

    # Competition risk
    comp_risk = {'High': 2, 'Medium': 1, 'Low': 0}
    risk += comp_risk.get(row.get('competition', 'Medium'), 1)

    # Infrastructure distance risk
    dist = row.get('avg_distance', row.get('avg_dist_m', 500))
    if dist > 800:
        risk += 2
    elif dist > 400:
        risk += 1

    # CAPEX risk
    capex = row.get('capex', row.get('Est. CAPEX (€K)', 0))
    if isinstance(capex, (int, float)):
        if capex > 1200:
            risk += 2
        elif capex > 800:
            risk += 1

    # Churn risk proxy (low adoption + high competition = high churn)
    if take < 0.35 and row.get('competition') == 'High':
        risk += 1

    return int(risk)


def _risk_label(score: int) -> str:
    if score >= 5:
        return 'High Risk'
    elif score >= 3:
        return 'Medium Risk'
    return 'Low Risk'


def apply_risk_model(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df['risk_score'] = df.apply(calculate_risk, axis=1)
    df['risk_label'] = df['risk_score'].apply(_risk_label)
    return df


# ── 3. DECISION ENGINE ────────────────────────────────────────────────────────

def ai_decision(df: pd.DataFrame) -> tuple[str, str]:
    """
    Returns (decision_string, css_class) based on portfolio metrics.
    """
    avg_adoption = df['predicted_take_rate'].mean()
    avg_risk     = df['risk_score'].mean()
    high_risk_pct= (df['risk_label'] == 'High Risk').mean()

    if avg_adoption > 0.50 and avg_risk < 3.0 and high_risk_pct < 0.20:
        return '🟢 GO — Strong business case. Recommend Phase 1 rollout.', 'success'
    elif avg_adoption > 0.40 and avg_risk < 5.0:
        return '🟡 CONDITIONAL — Viable with optimization. Review CAPEX and competition zones.', 'warning'
    return '🔴 NO-GO — Not commercially viable under current assumptions.', 'error'


# ── 4. INVESTMENT PRIORITY SCORE ─────────────────────────────────────────────

def investment_priority_score(row: dict) -> float:
    """
    Composite score combining adoption, risk, and distance.
    Higher = better investment candidate.
    Range: 0.0 – 1.0
    """
    adoption = row.get('predicted_take_rate', 0.4)
    risk     = row.get('risk_score', 3)
    dist     = row.get('avg_distance', row.get('avg_dist_m', 500))

    score = (
        adoption * 0.50 +
        (1 - risk / 8) * 0.30 +
        (1 - min(dist, 1500) / 1500) * 0.20
    )
    return round(float(np.clip(score, 0.0, 1.0)), 4)


def apply_priority_scores(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df['investment_priority'] = df.apply(investment_priority_score, axis=1)
    df['priority_rank'] = df['investment_priority'].rank(ascending=False).astype(int)
    return df


# ── 5. FULL PIPELINE SHORTCUT ────────────────────────────────────────────────

def run_ai_pipeline(df: pd.DataFrame) -> tuple[pd.DataFrame, str, str]:
    """
    Run full heuristic AI pipeline in one call.
    Returns: (enriched_df, decision_text, css_class)
    """
    df = apply_adoption_model(df)
    df = apply_risk_model(df)
    df = apply_priority_scores(df)
    decision_text, css_class = ai_decision(df)
    return df, decision_text, css_class
