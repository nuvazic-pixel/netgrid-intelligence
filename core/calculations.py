import numpy as np
import pandas as pd

PHASE_MULTIPLIERS = {'greenfield': 1.25, 'brownfield': 1.00, 'upgrade': 0.70}
RISK_ADJUSTMENTS  = {'low': 0.90, 'mid': 1.00, 'high': 1.15}


def calc_scenario(homes, take_rate, arpu, capex_per_home, phase, risk):
    phase_multi  = PHASE_MULTIPLIERS.get(phase, 1.0)
    risk_adj     = RISK_ADJUSTMENTS.get(risk, 1.0)
    total_capex  = homes * capex_per_home * phase_multi * risk_adj
    subs         = round(homes * take_rate)
    annual_rev   = subs * arpu * 12
    annual_opex  = annual_rev * 0.30
    ebitda       = annual_rev - annual_opex
    ebitda_margin= (ebitda / annual_rev * 100) if annual_rev > 0 else 0
    payback      = (total_capex / ebitda) if ebitda > 0 else 99
    irr          = max(2.0, min(35.0, 18 - payback * 1.2))
    return dict(total_capex=total_capex, phase_multi=phase_multi, risk_adj=risk_adj,
                subs=subs, annual_rev=annual_rev, annual_opex=annual_opex,
                ebitda=ebitda, ebitda_margin=ebitda_margin, payback=payback, irr=irr)


def calc_roi(homes, take_rate, arpu, capex_per_home, discount_rate, opex_pct, churn_rate):
    total_capex     = homes * capex_per_home
    base_rev_annual = homes * take_rate * arpu * 12
    npv = -total_capex
    for y in range(1, 11):
        subs_y = homes * take_rate * ((1 - churn_rate) ** y)
        fcf_y  = subs_y * arpu * 12 * (1 - opex_pct)
        npv   += fcf_y / ((1 + discount_rate) ** y)
    payback = (total_capex / (base_rev_annual * (1 - opex_pct))) if base_rev_annual > 0 else 99
    irr     = max(2.0, min(35.0, (npv / total_capex) * 8 + 10)) if total_capex > 0 else 0
    return dict(npv=npv, irr=irr, payback=payback)


def calc_cashflow(homes, take_rate, arpu, capex_per_home, phase, risk):
    phase_multi = PHASE_MULTIPLIERS.get(phase, 1.0)
    risk_adj    = RISK_ADJUSTMENTS.get(risk, 1.0)
    total_capex = homes * capex_per_home * phase_multi * risk_adj
    annual_rev  = homes * take_rate * arpu * 12
    years, annual_cfs, cumulative = [], [], []
    cum = -total_capex
    for y in range(11):
        years.append(f'Y{y}')
        cf = (-total_capex) if y == 0 else (annual_rev * (0.97 ** y) * 0.70)
        if y > 0:
            cum += cf
        annual_cfs.append(round(cf / 1000, 1))
        cumulative.append(round(cum / 1000, 1))
    return pd.DataFrame({'year': years, 'annual_cf_k': annual_cfs, 'cumulative_k': cumulative})


def calc_npv_sensitivity(homes, take_rate, arpu, capex_per_home, opex_pct, churn_rate):
    total_capex = homes * capex_per_home
    disc_rates  = np.arange(1, 15.5, 0.5)
    npv_values  = []
    for dr in disc_rates:
        npv = -total_capex
        for y in range(1, 11):
            subs_y = homes * take_rate * ((1 - churn_rate) ** y)
            npv   += subs_y * arpu * 12 * (1 - opex_pct) / ((1 + dr / 100) ** y)
        npv_values.append(round(npv / 1000, 1))
    return pd.DataFrame({'discount_rate': disc_rates, 'npv_k': npv_values})


def calc_breakeven(homes, take_rate, arpu, capex_per_home, opex_pct, churn_rate):
    total_capex = homes * capex_per_home
    years, cumulative = [], []
    cum = -total_capex
    for y in range(11):
        years.append(f'Y{y}')
        if y > 0:
            subs_y = homes * take_rate * ((1 - churn_rate) ** y)
            cum   += subs_y * arpu * 12 * (1 - opex_pct)
        cumulative.append(round(cum / 1000, 1))
    return pd.DataFrame({'year': years, 'cumulative_k': cumulative})
