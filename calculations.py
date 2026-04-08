"""
calculations.py — Financial modeling for FTTH Expansion Platform
CAPEX/OPEX, ROI, NPV, IRR, Cashflow, Break-even
"""

import pandas as pd
import numpy as np


# Phase multipliers for CAPEX
PHASE_MULTIPLIERS = {
    "greenfield": 1.25,   # New area, full build
    "brownfield": 1.00,   # Partial infrastructure exists
    "upgrade": 0.70,      # DSL → FTTH upgrade
}

# Risk adjustments
RISK_ADJUSTMENTS = {
    "low": {"take_rate_adj": 1.05, "churn_adj": 0.85},
    "mid": {"take_rate_adj": 1.00, "churn_adj": 1.00},
    "high": {"take_rate_adj": 0.90, "churn_adj": 1.20},
}


def calc_scenario(
    homes: int,
    take_rate: float,  # 0-1
    arpu: float,       # €/month
    capex_per_home: float,
    phase: str = "brownfield",
    risk: str = "mid"
) -> dict:
    """
    Calculate scenario metrics: CAPEX, subscribers, revenue, EBITDA.
    """
    phase_multi = PHASE_MULTIPLIERS.get(phase, 1.0)
    risk_adj = RISK_ADJUSTMENTS.get(risk, RISK_ADJUSTMENTS["mid"])
    
    # Adjusted take rate
    adj_take_rate = take_rate * risk_adj["take_rate_adj"]
    
    # Calculations
    total_capex = homes * capex_per_home * phase_multi
    subs = int(homes * adj_take_rate)
    annual_rev = subs * arpu * 12
    
    # EBITDA (assume 60% margin on revenue minus OPEX)
    opex_rate = 0.30  # default 30%
    ebitda = annual_rev * (1 - opex_rate)
    ebitda_margin = (ebitda / annual_rev * 100) if annual_rev > 0 else 0
    
    return {
        "total_capex": total_capex,
        "subs": subs,
        "annual_rev": annual_rev,
        "ebitda": ebitda,
        "ebitda_margin": ebitda_margin,
        "phase_multi": phase_multi,
        "adj_take_rate": adj_take_rate,
    }


def calc_roi(
    homes: int,
    take_rate: float,
    arpu: float,
    capex_per_home: float,
    discount_rate: float = 0.06,
    opex_pct: float = 0.30,
    churn_rate: float = 0.08,
    years: int = 10
) -> dict:
    """
    Calculate ROI metrics: NPV, IRR, Payback period.
    """
    total_capex = homes * capex_per_home
    subs_base = homes * take_rate
    
    # Annual cashflows
    cashflows = [-total_capex]
    cumulative = -total_capex
    payback_year = years  # default to end if never breaks even
    
    for year in range(1, years + 1):
        # Subscribers decay with churn
        subs = subs_base * ((1 - churn_rate) ** (year - 1))
        revenue = subs * arpu * 12
        opex = revenue * opex_pct
        net_cf = revenue - opex
        cashflows.append(net_cf)
        
        cumulative += net_cf
        if cumulative >= 0 and payback_year == years:
            # Interpolate exact payback
            prev_cum = cumulative - net_cf
            if net_cf > 0:
                payback_year = year - 1 + (-prev_cum / net_cf)
    
    # NPV calculation
    npv = sum(cf / ((1 + discount_rate) ** i) for i, cf in enumerate(cashflows))
    
    # IRR approximation (Newton-Raphson)
    irr = _calc_irr(cashflows)
    
    return {
        "npv": npv,
        "irr": irr * 100,  # as percentage
        "payback": payback_year,
        "total_capex": total_capex,
        "cashflows": cashflows,
    }


def _calc_irr(cashflows: list, guess: float = 0.1, max_iter: int = 100, tol: float = 1e-6) -> float:
    """Calculate IRR using Newton-Raphson method."""
    rate = guess
    for _ in range(max_iter):
        npv = sum(cf / ((1 + rate) ** i) for i, cf in enumerate(cashflows))
        npv_deriv = sum(-i * cf / ((1 + rate) ** (i + 1)) for i, cf in enumerate(cashflows))
        
        if abs(npv_deriv) < 1e-10:
            break
            
        new_rate = rate - npv / npv_deriv
        
        if abs(new_rate - rate) < tol:
            return new_rate
        
        rate = new_rate
    
    return max(min(rate, 1.0), -0.99)  # bound IRR


def calc_cashflow(
    homes: int,
    take_rate: float,
    arpu: float,
    capex_per_home: float,
    phase: str = "brownfield",
    risk: str = "mid",
    years: int = 10
) -> pd.DataFrame:
    """
    Generate cashflow projection DataFrame for visualization.
    """
    phase_multi = PHASE_MULTIPLIERS.get(phase, 1.0)
    total_capex = homes * capex_per_home * phase_multi
    subs_base = homes * take_rate
    
    churn_rate = 0.08
    opex_pct = 0.30
    
    records = []
    cumulative = 0
    
    for year in range(years + 1):
        if year == 0:
            annual_cf = -total_capex
            revenue = 0
            opex = 0
            subs = 0
        else:
            subs = subs_base * ((1 - churn_rate) ** (year - 1))
            revenue = subs * arpu * 12
            opex = revenue * opex_pct
            annual_cf = revenue - opex
        
        cumulative += annual_cf
        
        records.append({
            "year": year,
            "subs": int(subs) if year > 0 else 0,
            "revenue_k": round(revenue / 1000, 1),
            "opex_k": round(opex / 1000, 1),
            "annual_cf_k": round(annual_cf / 1000, 1),
            "cumulative_k": round(cumulative / 1000, 1),
        })
    
    return pd.DataFrame(records)


def calc_npv_sensitivity(
    homes: int,
    take_rate: float,
    arpu: float,
    capex_per_home: float,
    opex_pct: float = 0.30,
    churn_rate: float = 0.08,
    years: int = 10
) -> pd.DataFrame:
    """
    NPV sensitivity across different discount rates.
    """
    discount_rates = np.arange(2, 18, 1)  # 2% to 17%
    
    total_capex = homes * capex_per_home
    subs_base = homes * take_rate
    
    records = []
    for dr in discount_rates:
        dr_decimal = dr / 100
        
        # Build cashflows
        cashflows = [-total_capex]
        for year in range(1, years + 1):
            subs = subs_base * ((1 - churn_rate) ** (year - 1))
            revenue = subs * arpu * 12
            opex = revenue * opex_pct
            net_cf = revenue - opex
            cashflows.append(net_cf)
        
        # NPV
        npv = sum(cf / ((1 + dr_decimal) ** i) for i, cf in enumerate(cashflows))
        
        records.append({
            "discount_rate": dr,
            "npv_k": round(npv / 1000, 1),
        })
    
    return pd.DataFrame(records)


def calc_breakeven(
    homes: int,
    take_rate: float,
    arpu: float,
    capex_per_home: float,
    opex_pct: float = 0.30,
    churn_rate: float = 0.08,
    years: int = 15
) -> pd.DataFrame:
    """
    Break-even analysis over extended time horizon.
    """
    total_capex = homes * capex_per_home
    subs_base = homes * take_rate
    
    records = []
    cumulative = 0
    
    for year in range(years + 1):
        if year == 0:
            annual_cf = -total_capex
        else:
            subs = subs_base * ((1 - churn_rate) ** (year - 1))
            revenue = subs * arpu * 12
            opex = revenue * opex_pct
            annual_cf = revenue - opex
        
        cumulative += annual_cf
        
        records.append({
            "year": year,
            "annual_cf_k": round(annual_cf / 1000, 1),
            "cumulative_k": round(cumulative / 1000, 1),
        })
    
    return pd.DataFrame(records)


if __name__ == "__main__":
    # Test calculations
    scenario = calc_scenario(3000, 0.45, 40, 900, "brownfield", "mid")
    print("Scenario:", scenario)
    
    roi = calc_roi(3000, 0.45, 40, 900)
    print("ROI:", roi)
