import sys
import os

BASE_DIR = r"C:\ftth_simulator"

if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
import pydeck as pdk
from plotly.subplots import make_subplots

st.write("APP STARTED")

st.write("STEP 1")
# ── CORE
from core.calculations import (
    calc_scenario, calc_roi, calc_cashflow,
    calc_npv_sensitivity, calc_breakeven
)
from core.final_boss_ai import optimize_ftth_plan
from core.ai_predictor import run_ai_pipeline
from core.ml_model import run_ml_pipeline, feature_importance_df

st.write("STEP 2")
# ── DATA
from data.data import get_zone_df
from data.live_api import (
    get_live_city_context, decision_context_suffix, score_label
)
from data.market_intelligence import (
    apply_market_overlay, fetch_osm_telecom,
    enrich_competition_from_telecom, get_coverage_summary
)
st.write("STEP 3")
# ── GEO
from geo.geo_utils import geocode_address
from geo.fttx_utils import generate_cabinets, aggregate_buildings

# ── CONFIG
from config.saas_config import (
    get_current_user, feature_gate, check_building_limit,
    check_scenario_limit, render_account_widget,
    render_pricing_page, log_usage, TIERS
)