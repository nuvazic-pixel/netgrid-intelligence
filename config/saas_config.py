"""
saas_config.py
==============
SaaS configuration layer for FTTH/FTTx Intelligence Platform.

Handles:
  - User session management (Streamlit session_state based)
  - Subscription tiers: Free / Pro / Enterprise
  - Feature flags per tier
  - Usage tracking + soft limits
  - Tenant isolation (per-user data namespace)
  - Upgrade prompts

Architecture note:
  This module is designed to be drop-in ready for a real auth backend.
  Currently uses Streamlit session_state as the identity layer.
  To connect real auth: replace _get_current_user() with your JWT/OAuth handler.

Part of: FTTH/FTTx Intelligence Platform
"""

from __future__ import annotations
import hashlib
import json
from datetime import datetime, date
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Any

import streamlit as st

# ── TIER DEFINITIONS ──────────────────────────────────────────────────────────

TIERS = {
    'free': {
        'label':           'Free',
        'price_eur_month': 0,
        'color':           '#94a3b8',
        'limits': {
            'max_buildings_osm':        200,
            'max_scenarios_per_day':    3,
            'max_nodes_optimizer':      2,
            'max_report_exports':       1,
            'history_days':             7,
        },
        'features': {
            'osm_real_data':            True,
            'road_network':             False,   # straight-line only
            'final_boss_optimizer':     False,
            'ml_model':                 False,
            'ai_predictor':             True,
            'market_intelligence':      False,
            'fttx_modes':               ['FTTH'],
            'breitbandatlas':           False,
            'csv_export':               True,
            'pdf_report':               False,
            'api_access':               False,
            'white_label':              False,
            'priority_support':         False,
        },
    },
    'pro': {
        'label':           'Pro',
        'price_eur_month': 49,
        'color':           '#60a5fa',
        'limits': {
            'max_buildings_osm':        2000,
            'max_scenarios_per_day':    50,
            'max_nodes_optimizer':      5,
            'max_report_exports':       999,
            'history_days':             90,
        },
        'features': {
            'osm_real_data':            True,
            'road_network':             True,
            'final_boss_optimizer':     True,
            'ml_model':                 True,
            'ai_predictor':             True,
            'market_intelligence':      True,
            'fttx_modes':               ['FTTH', 'FTTB', 'FTTC'],
            'breitbandatlas':           True,
            'csv_export':               True,
            'pdf_report':               True,
            'api_access':               False,
            'white_label':              False,
            'priority_support':         True,
        },
    },
    'enterprise': {
        'label':           'Enterprise',
        'price_eur_month': 299,
        'color':           '#a78bfa',
        'limits': {
            'max_buildings_osm':        10000,
            'max_scenarios_per_day':    999,
            'max_nodes_optimizer':      10,
            'max_report_exports':       999,
            'history_days':             365,
        },
        'features': {
            'osm_real_data':            True,
            'road_network':             True,
            'final_boss_optimizer':     True,
            'ml_model':                 True,
            'ai_predictor':             True,
            'market_intelligence':      True,
            'fttx_modes':               ['FTTH', 'FTTB', 'FTTC'],
            'breitbandatlas':           True,
            'csv_export':               True,
            'pdf_report':               True,
            'api_access':               True,
            'white_label':              True,
            'priority_support':         True,
        },
    },
}


# ── USER / TENANT DATACLASS ───────────────────────────────────────────────────

@dataclass
class User:
    user_id:        str
    email:          str
    name:           str
    tier:           str                     = 'free'
    company:        str                     = ''
    created_at:     str                     = field(default_factory=lambda: datetime.now().isoformat())
    last_active:    str                     = field(default_factory=lambda: datetime.now().isoformat())
    usage:          dict[str, Any]          = field(default_factory=dict)

    def __post_init__(self):
        if not self.usage:
            self.usage = {
                'scenarios_today':   0,
                'exports_total':     0,
                'last_reset_date':   str(date.today()),
                'total_api_calls':   0,
            }

    @property
    def tier_config(self) -> dict:
        return TIERS.get(self.tier, TIERS['free'])

    @property
    def limits(self) -> dict:
        return self.tier_config['limits']

    @property
    def features(self) -> dict:
        return self.tier_config['features']

    def can_use(self, feature: str) -> bool:
        return bool(self.features.get(feature, False))

    def reset_daily_usage_if_needed(self):
        today = str(date.today())
        if self.usage.get('last_reset_date') != today:
            self.usage['scenarios_today'] = 0
            self.usage['last_reset_date'] = today

    def increment_scenario(self):
        self.reset_daily_usage_if_needed()
        self.usage['scenarios_today'] = self.usage.get('scenarios_today', 0) + 1

    def scenarios_remaining(self) -> int:
        self.reset_daily_usage_if_needed()
        limit = self.limits['max_scenarios_per_day']
        used  = self.usage.get('scenarios_today', 0)
        return max(0, limit - used)

    def to_dict(self) -> dict:
        return asdict(self)


# ── SESSION MANAGEMENT ────────────────────────────────────────────────────────

def _make_user_id(email: str) -> str:
    return hashlib.sha256(email.encode()).hexdigest()[:16]


def get_current_user() -> User:
    """
    Get current user from Streamlit session state.
    In production: replace this with JWT decode / OAuth token validation.
    """
    if 'saas_user' not in st.session_state:
        # Demo / portfolio mode: auto-login as Pro user
        st.session_state['saas_user'] = User(
            user_id  = 'demo_user_01',
            email    = 'demo@ftth-platform.de',
            name     = 'Demo User',
            tier     = 'pro',
            company  = 'Demo GmbH',
        )
    return st.session_state['saas_user']


def set_user(email: str, name: str, tier: str = 'free', company: str = '') -> User:
    """Create or update user in session. Call after login."""
    user = User(
        user_id = _make_user_id(email),
        email   = email,
        name    = name,
        tier    = tier,
        company = company,
    )
    st.session_state['saas_user'] = user
    return user


def logout():
    """Clear user session."""
    for key in ['saas_user', 'real_df', 'road_graph', 'telecom_df', 'last_address']:
        st.session_state.pop(key, None)


# ── FEATURE GATE ──────────────────────────────────────────────────────────────

def feature_gate(feature: str, show_upgrade: bool = True) -> bool:
    """
    Check if current user can access a feature.
    If not, optionally show upgrade prompt.
    Returns True if access granted.
    """
    user = get_current_user()
    if user.can_use(feature):
        return True

    if show_upgrade:
        _show_upgrade_prompt(feature, user.tier)

    return False


def _show_upgrade_prompt(feature: str, current_tier: str):
    """Show inline upgrade CTA when a feature is locked."""
    feature_labels = {
        'road_network':         'Road-network distance calculation',
        'final_boss_optimizer': 'Final Boss cost-aware optimizer',
        'ml_model':             'ML adoption prediction model',
        'market_intelligence':  'Market intelligence & competitor overlay',
        'breitbandatlas':       'Bundesnetzagentur Breitbandatlas integration',
        'pdf_report':           'PDF executive report export',
        'api_access':           'REST API access',
        'white_label':          'White-label & custom branding',
    }
    label = feature_labels.get(feature, feature.replace('_', ' ').title())
    next_tier = 'pro' if current_tier == 'free' else 'enterprise'
    next_price = TIERS[next_tier]['price_eur_month']

    st.markdown(f"""
<div style="background:rgba(245,158,11,.12);border:1px solid rgba(245,158,11,.35);
     border-radius:12px;padding:14px 18px;margin:8px 0">
  <b>🔒 {label}</b> requires <b>{next_tier.title()}</b> (€{next_price}/month)<br>
  <span style="font-size:.85rem;color:#94a3b8">
    Upgrade to unlock this feature and {
        "road-network optimization, ML models, and market intelligence"
        if next_tier == "pro" else
        "API access, white-label, and unlimited usage"
    }.
  </span>
</div>""", unsafe_allow_html=True)


# ── LIMIT GUARDS ──────────────────────────────────────────────────────────────

def check_building_limit(n_buildings: int) -> tuple[bool, int]:
    """
    Returns (allowed, capped_count).
    Free tier: cap at 200. Pro: 2000. Enterprise: 10000.
    """
    user  = get_current_user()
    limit = user.limits['max_buildings_osm']
    if n_buildings <= limit:
        return True, n_buildings
    return False, limit


def check_scenario_limit() -> bool:
    """Returns True if user can run another scenario today."""
    user = get_current_user()
    remaining = user.scenarios_remaining()
    if remaining <= 0:
        st.warning(
            f'⚠️ Daily scenario limit reached ({user.limits["max_scenarios_per_day"]}/day on {user.tier.title()} plan). '
            f'Upgrade for more runs.'
        )
        return False
    return True


# ── TENANT DATA NAMESPACE ─────────────────────────────────────────────────────

def get_tenant_data_dir() -> Path:
    """
    Returns a per-user data directory for storing models, exports, history.
    In production this maps to S3 prefix or DB tenant_id.
    """
    user     = get_current_user()
    data_dir = Path('data') / 'tenants' / user.user_id
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


# ── SIDEBAR ACCOUNT WIDGET ────────────────────────────────────────────────────

def render_account_widget():
    """
    Render a compact account status widget in the Streamlit sidebar.
    Call this inside `with st.sidebar:` block.
    """
    user   = get_current_user()
    tier_c = TIERS[user.tier]
    color  = tier_c['color']
    label  = tier_c['label']
    price  = tier_c['price_eur_month']

    st.markdown(f"""
<div style="background:rgba(255,255,255,.04);border:1px solid rgba(255,255,255,.08);
     border-radius:14px;padding:12px 14px;margin-bottom:8px">
  <div style="font-size:.78rem;color:#94a3b8;margin-bottom:4px">ACCOUNT</div>
  <div style="font-weight:600;color:#f8fafc;font-size:.95rem">{user.name}</div>
  <div style="font-size:.8rem;color:#94a3b8">{user.company or user.email}</div>
  <div style="margin-top:8px">
    <span style="background:{color}22;color:{color};font-size:.75rem;
                 padding:3px 10px;border-radius:20px;font-weight:600">
      {label} {'· Free' if price == 0 else f'· €{price}/mo'}
    </span>
  </div>
  <div style="font-size:.75rem;color:#64748b;margin-top:6px">
    {user.scenarios_remaining()} scenarios remaining today
  </div>
</div>""", unsafe_allow_html=True)

    if user.tier == 'free':
        st.markdown("""
<div style="background:rgba(96,165,250,.10);border:1px solid rgba(96,165,250,.25);
     border-radius:10px;padding:10px 12px;font-size:.8rem;color:#93c5fd;margin-bottom:4px">
  ⬆️ <b>Upgrade to Pro</b> for road-network optimization, ML models, and Breitbandatlas.
  <br>€49/month · Cancel anytime.
</div>""", unsafe_allow_html=True)


# ── PRICING PAGE CONTENT ──────────────────────────────────────────────────────

def render_pricing_page():
    """Render a full pricing comparison page as a Streamlit section."""
    st.markdown('## 💳 Pricing')
    st.markdown("<div style='color:#94a3b8;margin-bottom:1.5rem'>Choose the plan that fits your rollout planning needs.</div>",
                unsafe_allow_html=True)

    cols = st.columns(3)
    for col, (tier_key, tier) in zip(cols, TIERS.items()):
        with col:
            price_str = 'Free' if tier['price_eur_month'] == 0 else f"€{tier['price_eur_month']}/mo"
            color     = tier['color']
            st.markdown(f"""
<div style="background:rgba(255,255,255,.04);border:1px solid {color}44;
     border-radius:18px;padding:20px;text-align:center;min-height:420px">
  <div style="font-size:1.1rem;font-weight:700;color:{color};margin-bottom:4px">{tier['label']}</div>
  <div style="font-size:1.8rem;font-weight:800;color:#f8fafc;margin-bottom:12px">{price_str}</div>
  <hr style="border-color:rgba(255,255,255,.08);margin-bottom:12px">
  <div style="text-align:left;font-size:.82rem;color:#d1d5db;line-height:2">
    {'✅' if tier['features']['osm_real_data']        else '❌'} Real OSM building data<br>
    {'✅' if tier['features']['road_network']          else '❌'} Road-network distance<br>
    {'✅' if tier['features']['final_boss_optimizer']  else '❌'} Cost-aware optimizer<br>
    {'✅' if tier['features']['ml_model']              else '❌'} ML adoption model<br>
    {'✅' if tier['features']['market_intelligence']   else '❌'} Market intelligence<br>
    {'✅' if tier['features']['breitbandatlas']        else '❌'} Breitbandatlas data<br>
    {'✅' if tier['features']['pdf_report']            else '❌'} PDF report export<br>
    {'✅' if tier['features']['api_access']            else '❌'} API access<br>
    {'✅' if tier['features']['white_label']           else '❌'} White-label<br>
    📊 {tier['limits']['max_buildings_osm']:,} buildings / run<br>
    🔄 {tier['limits']['max_scenarios_per_day']} scenarios / day
  </div>
</div>""", unsafe_allow_html=True)


# ── USAGE ANALYTICS (lightweight) ────────────────────────────────────────────

def log_usage(action: str, metadata: dict | None = None):
    """
    Log a user action. In production: send to analytics backend (Mixpanel, PostHog, etc.)
    Currently: prints to console + stores in session state.
    """
    user  = get_current_user()
    event = {
        'user_id':   user.user_id,
        'tier':      user.tier,
        'action':    action,
        'timestamp': datetime.now().isoformat(),
        'metadata':  metadata or {},
    }

    # In-session log
    if 'usage_log' not in st.session_state:
        st.session_state['usage_log'] = []
    st.session_state['usage_log'].append(event)

    # Console output (replace with real analytics in production)
    print(f'[USAGE] {event["timestamp"][:19]} | {user.tier:10} | {action}')
