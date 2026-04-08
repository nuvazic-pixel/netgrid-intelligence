"""
FTTH Expansion Intelligence Platform
AI-powered infrastructure decision system with Swarm Voting
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
import pydeck as pdk
from plotly.subplots import make_subplots

from db_layer import get_zone_df, get_all_gemeinden, save_swarm_decision
from ai_swarm import SwarmCoordinator, Vote, get_swarm_recommendation
from ftth_tech_specs import (
    GPONSpecs, SPLITTER_SPECS, BUILDING_FIBER_CONFIG,
    DEPLOYMENT_CONFIGS, DeploymentType, TELEKOM_GLOSSARY,
    estimate_capex_per_home, get_bitrate_recommendation
)
from calculations import (
    calc_scenario,
    calc_roi,
    calc_cashflow,
    calc_npv_sensitivity,
    calc_breakeven
)
from geo_utils import geocode_address

# ============================================================
# PAGE CONFIG
# ============================================================
st.set_page_config(
    page_title='FTTH Expansion Intelligence Platform',
    page_icon='📡',
    layout='wide',
    initial_sidebar_state='expanded'
)

# ============================================================
# STYLING
# ============================================================
st.markdown("""
<style>
    .stApp {
        background: linear-gradient(180deg, #0b1220 0%, #111827 55%, #0f172a 100%);
        color: #e5e7eb;
    }

    section[data-testid='stSidebar'] {
        background: linear-gradient(180deg, #0f172a 0%, #111827 100%);
        border-right: 1px solid rgba(255,255,255,0.06);
    }

    .block-container {
        padding-top: 1.4rem;
        padding-bottom: 2rem;
        max-width: 1500px;
    }

    h1, h2, h3, h4 {
        color: #f8fafc !important;
        letter-spacing: -0.02em;
    }

    p, div, label, span {
        color: #d1d5db;
    }

    .hero {
        background: linear-gradient(135deg, rgba(37,99,235,0.20), rgba(16,185,129,0.12));
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 20px;
        padding: 26px 28px 18px 28px;
        margin-bottom: 18px;
        box-shadow: 0 10px 30px rgba(0,0,0,0.25);
    }

    .hero-title {
        font-size: 2rem;
        font-weight: 800;
        line-height: 1.1;
        margin-bottom: 0.35rem;
        color: #ffffff;
    }

    .hero-sub {
        font-size: 1rem;
        color: #cbd5e1;
        margin-bottom: 0;
    }

    .glass-card {
        background: rgba(255,255,255,0.04);
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 18px;
        padding: 18px 18px 14px 18px;
        box-shadow: 0 8px 24px rgba(0,0,0,0.18);
        margin-bottom: 12px;
    }

    .kpi-card {
        background: linear-gradient(180deg, rgba(255,255,255,0.05), rgba(255,255,255,0.03));
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 18px;
        padding: 16px 16px 14px 16px;
        min-height: 120px;
        box-shadow: 0 10px 25px rgba(0,0,0,0.18);
    }

    .kpi-label {
        font-size: 0.88rem;
        color: #93c5fd;
        margin-bottom: 8px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }

    .kpi-value {
        font-size: 1.8rem;
        font-weight: 800;
        color: #ffffff;
        line-height: 1.1;
        margin-bottom: 6px;
    }

    .kpi-delta {
        font-size: 0.88rem;
        color: #cbd5e1;
    }

    .swarm-card {
        background: linear-gradient(135deg, rgba(99,102,241,0.15), rgba(139,92,246,0.10));
        border: 1px solid rgba(139,92,246,0.30);
        border-radius: 16px;
        padding: 16px;
        margin-bottom: 12px;
    }

    .vote-strong-invest { color: #10b981; font-weight: 700; }
    .vote-invest { color: #34d399; font-weight: 600; }
    .vote-hold { color: #fbbf24; font-weight: 600; }
    .vote-delay { color: #f97316; font-weight: 600; }
    .vote-avoid { color: #ef4444; font-weight: 700; }

    .agent-sentinel { border-left: 3px solid #3b82f6; }
    .agent-vanguard { border-left: 3px solid #f59e0b; }
    .agent-oracle { border-left: 3px solid #8b5cf6; }

    .decision-good {
        background: rgba(16,185,129,0.14);
        border: 1px solid rgba(16,185,129,0.35);
        color: #d1fae5;
        padding: 14px 16px;
        border-radius: 14px;
        font-weight: 600;
        margin-bottom: 10px;
    }

    .decision-mid {
        background: rgba(245,158,11,0.14);
        border: 1px solid rgba(245,158,11,0.35);
        color: #fef3c7;
        padding: 14px 16px;
        border-radius: 14px;
        font-weight: 600;
        margin-bottom: 10px;
    }

    .decision-bad {
        background: rgba(239,68,68,0.14);
        border: 1px solid rgba(239,68,68,0.35);
        color: #fee2e2;
        padding: 14px 16px;
        border-radius: 14px;
        font-weight: 600;
        margin-bottom: 10px;
    }

    div[data-testid='stMetric'] {
        background: rgba(255,255,255,0.04);
        border: 1px solid rgba(255,255,255,0.08);
        padding: 12px 14px;
        border-radius: 16px;
    }

    .stTabs [data-baseweb='tab-list'] {
        gap: 8px;
    }

    .stTabs [data-baseweb='tab'] {
        background: rgba(255,255,255,0.04);
        border-radius: 12px;
        padding: 10px 18px;
        color: #d1d5db;
    }

    .stTabs [aria-selected='true'] {
        background: rgba(37,99,235,0.22) !important;
        color: #ffffff !important;
    }

    .small-note {
        font-size: 0.86rem;
        color: #94a3b8;
    }
</style>
""", unsafe_allow_html=True)


# ============================================================
# HELPERS
# ============================================================
def build_kpi_card(label: str, value: str, delta: str) -> str:
    return f"""
    <div class='kpi-card'>
        <div class='kpi-label'>{label}</div>
        <div class='kpi-value'>{value}</div>
        <div class='kpi-delta'>{delta}</div>
    </div>
    """


def get_vote_class(vote: Vote) -> str:
    return f"vote-{vote.value.replace('_', '-')}"


def get_vote_emoji(vote: Vote) -> str:
    return {
        Vote.STRONG_INVEST: "🟢",
        Vote.INVEST: "🟡",
        Vote.HOLD: "🟠",
        Vote.DELAY: "🔴",
        Vote.AVOID: "⛔",
    }.get(vote, "⚪")


def ai_decision_block(payback: float, npv: float, irr: float) -> tuple[str, str]:
    if payback < 5 and npv > 0 and irr >= 15:
        return (
            'decision-good',
            '🟢 AI Investment Decision: Strong investment case. '
            'Deploy now. Commercial fundamentals are solid and capital recovery is fast.'
        )
    elif payback < 8 and npv > 0:
        return (
            'decision-mid',
            '🟡 AI Investment Decision: Viable, but optimize CAPEX, adoption, or ARPU before scale-up.'
        )
    return (
        'decision-bad',
        '🔴 AI Investment Decision: High-risk scenario. '
        'Not recommended without subsidy, redesign, or stronger demand assumptions.'
    )


def investment_priority(row: pd.Series, capex_per_home: float, take_rate: float, arpu: float) -> pd.Series:
    est_revenue = row['homes'] * (take_rate / 100) * arpu * 12
    est_capex = row['homes'] * capex_per_home

    if row['avg_dist_m'] <= 400 and row['adoption'] >= 45:
        score = 'High'
    elif row['avg_dist_m'] <= 800 and row['adoption'] >= 35:
        score = 'Medium'
    else:
        score = 'Low'

    if score == 'High' and est_revenue > 0.20 * est_capex:
        recommendation = 'Expand now'
    elif score == 'Medium':
        recommendation = 'Pilot / phase 2'
    else:
        recommendation = 'Wait / subsidy needed'

    return pd.Series([score, round(est_capex / 1000), round(est_revenue / 1000), recommendation])


# ============================================================
# SIDEBAR
# ============================================================
with st.sidebar:
    st.markdown('## ⚙️ Simulation Controls')

    st.markdown('### Network')
    homes = st.slider('Homes Passed Target', 500, 8000, 3000, 100)
    take_rate = st.slider('Take Rate (%)', 10, 90, 45, 1)
    arpu = st.slider('ARPU (€/month)', 20, 80, 40, 1)
    capex_per_home = st.slider('CAPEX per Home (€)', 400, 2000, 900, 50)

    st.markdown('### Deployment')
    phase = st.selectbox(
        'Phase Type',
        ['Greenfield (new area)', 'Brownfield (partial infra)', 'Upgrade (DSL → FTTH)'],
        index=1
    )

    risk = st.selectbox(
        'Risk Level',
        ['Low (rural, low competition)', 'Medium (suburban)', 'High (urban, competitive)'],
        index=1
    )

    st.markdown('### Financial')
    discount_rate = st.slider('Discount Rate (%)', 1.0, 15.0, 6.0, 0.5)
    opex_pct = st.slider('OPEX % of Revenue', 10, 60, 30, 1)
    churn_rate = st.slider('Annual Churn Rate (%)', 1, 20, 8, 1)

    st.divider()
    
    st.markdown('### 📍 Region')
    region_filter = st.selectbox(
        'Landkreis Filter',
        ['All', 'Landsberg am Lech', 'Augsburg', 'Weilheim-Schongau', 'Fürstenfeldbruck', 'Starnberg']
    )
    
    st.markdown(
        "<div class='small-note'>Real Bavarian Gemeinden with simulated FTTH metrics. "
        "AI Swarm provides investment recommendations.</div>",
        unsafe_allow_html=True
    )


# ============================================================
# DATA + CALCULATIONS
# ============================================================
phase_key = 'greenfield' if 'Greenfield' in phase else 'upgrade' if 'Upgrade' in phase else 'brownfield'
risk_key = 'low' if 'Low' in risk else 'high' if 'High' in risk else 'mid'

# Load from database
zone_df = get_zone_df().copy()

# Apply region filter
if region_filter != 'All':
    zone_df = zone_df[zone_df['landkreis'] == region_filter].copy()

# Financial calculations
scenario = calc_scenario(homes, take_rate / 100, arpu, capex_per_home, phase_key, risk_key)
roi = calc_roi(homes, take_rate / 100, arpu, capex_per_home, discount_rate / 100, opex_pct / 100, churn_rate / 100)
cashflow_df = calc_cashflow(homes, take_rate / 100, arpu, capex_per_home, phase_key, risk_key)
npv_df = calc_npv_sensitivity(homes, take_rate / 100, arpu, capex_per_home, opex_pct / 100, churn_rate / 100)
breakeven_df = calc_breakeven(homes, take_rate / 100, arpu, capex_per_home, opex_pct / 100, churn_rate / 100)

# Metrics
total_homes = int(zone_df['homes'].sum())
deployed_df = zone_df[zone_df['status'] == 'deployed']
deployed_homes = int(deployed_df['homes'].sum()) if len(deployed_df) > 0 else 0
coverage_pct = deployed_homes / total_homes * 100 if total_homes > 0 else 0
avg_adoption = zone_df['adoption'].mean()
active_subs = int(deployed_homes * avg_adoption / 100)
monthly_rev = active_subs * arpu
expansion_homes = total_homes - deployed_homes
annual_churn_loss = homes * take_rate / 100 * arpu * 12 * churn_rate / 100

# Add priority scores
zone_df[['ROI Score', 'Est. CAPEX (€K)', 'Est. Revenue/yr (€K)', 'Action']] = zone_df.apply(
    lambda row: investment_priority(row, capex_per_home, take_rate, arpu), axis=1
)

decision_class, decision_text = ai_decision_block(roi['payback'], roi['npv'], roi['irr'])


# ============================================================
# AI SWARM ANALYSIS
# ============================================================
@st.cache_data(ttl=300)
def run_swarm_analysis(zones_json: str):
    """Run AI swarm on all zones (cached)."""
    zones = pd.read_json(zones_json).to_dict('records')
    coordinator = SwarmCoordinator()
    return coordinator.analyze_all_zones(zones)

swarm_decisions = run_swarm_analysis(zone_df.to_json())


# ============================================================
# HERO
# ============================================================
st.markdown("""
<div class='hero'>
    <div class='hero-title'>📡 FTTH Expansion Intelligence Platform</div>
    <p class='hero-sub'>
        AI Swarm-powered infrastructure decision system for rollout planning, ROI analysis,
        and investment prioritization across Bavaria.
    </p>
</div>
""", unsafe_allow_html=True)


# ============================================================
# TOP KPI ROW
# ============================================================
k1, k2, k3, k4, k5, k6 = st.columns(6)
with k1:
    st.markdown(build_kpi_card('Gemeinden', f'{len(zone_df)}', f'{region_filter} region'), unsafe_allow_html=True)
with k2:
    st.markdown(build_kpi_card('Total Homes', f'{total_homes:,}', 'Addressable market'), unsafe_allow_html=True)
with k3:
    st.markdown(build_kpi_card('Coverage', f'{coverage_pct:.0f}%', f'{deployed_homes:,} homes passed'), unsafe_allow_html=True)
with k4:
    st.markdown(build_kpi_card('Avg Adoption', f'{avg_adoption:.1f}%', 'Demand signal'), unsafe_allow_html=True)
with k5:
    st.markdown(build_kpi_card('Monthly Rev', f'€{monthly_rev/1000:.0f}K', f'ARPU €{arpu}/mo'), unsafe_allow_html=True)
with k6:
    invest_count = sum(1 for d in swarm_decisions if d.final_decision in [Vote.STRONG_INVEST, Vote.INVEST])
    st.markdown(build_kpi_card('AI: Invest', f'{invest_count}/{len(swarm_decisions)}', 'Swarm consensus'), unsafe_allow_html=True)

st.markdown(f"<div class='{decision_class}'>{decision_text}</div>", unsafe_allow_html=True)


# ============================================================
# TABS
# ============================================================
tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    '🤖 AI Swarm',
    '📊 Executive Overview',
    '💰 Financial Model',
    '🗺️ Geo Intelligence',
    '🏙️ 3D Command View',
    '📐 Tech Specs',
    '📄 Executive Report'
])


# ============================================================
# TAB 1: AI SWARM
# ============================================================
with tab1:
    st.markdown('### 🤖 AI Swarm Investment Analysis')
    st.markdown(
        "<div class='small-note'>Three AI agents with different investment strategies analyze each Gemeinde "
        "and vote on deployment priority. Consensus drives final recommendation.</div>",
        unsafe_allow_html=True
    )
    
    # Summary metrics
    strong_invest = sum(1 for d in swarm_decisions if d.final_decision == Vote.STRONG_INVEST)
    invest = sum(1 for d in swarm_decisions if d.final_decision == Vote.INVEST)
    hold = sum(1 for d in swarm_decisions if d.final_decision == Vote.HOLD)
    delay_avoid = sum(1 for d in swarm_decisions if d.final_decision in [Vote.DELAY, Vote.AVOID])
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("🟢 Strong Invest", strong_invest)
    col2.metric("🟡 Invest", invest)
    col3.metric("🟠 Hold", hold)
    col4.metric("🔴 Delay/Avoid", delay_avoid)
    
    st.markdown("---")
    
    # Agent legend
    st.markdown("""
    **AI Agents:**
    - 🛡️ **SENTINEL** (Conservative): Risk-averse, prioritizes proven markets and low infrastructure cost
    - ⚡ **VANGUARD** (Aggressive): Growth-focused, seeks first-mover advantage and large markets  
    - ⚖️ **ORACLE** (Balanced): ROI-optimized, analyzes unit economics and payback efficiency
    """)
    
    st.markdown("---")
    
    # Detailed analysis for each zone
    for decision in swarm_decisions[:15]:  # Top 15
        vote_color = {
            Vote.STRONG_INVEST: "#10b981",
            Vote.INVEST: "#34d399",
            Vote.HOLD: "#fbbf24",
            Vote.DELAY: "#f97316",
            Vote.AVOID: "#ef4444",
        }.get(decision.final_decision, "#6b7280")
        
        with st.expander(
            f"{get_vote_emoji(decision.final_decision)} **{decision.gemeinde_name}** — "
            f"{decision.final_decision.value.upper()} (Consensus: {decision.consensus_score:.0%})",
            expanded=(decision.final_decision == Vote.STRONG_INVEST)
        ):
            # Zone info
            zone_info = zone_df[zone_df['name'] == decision.gemeinde_name].iloc[0] if len(zone_df[zone_df['name'] == decision.gemeinde_name]) > 0 else None
            
            if zone_info is not None:
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Homes", f"{zone_info['homes']:,}")
                c2.metric("Adoption", f"{zone_info['adoption']:.1f}%")
                c3.metric("Avg Distance", f"{zone_info['avg_dist_m']}m")
                c4.metric("Status", zone_info['status'].capitalize())
            
            st.markdown(f"**Risk Level:** {decision.risk_level.upper()}")
            
            # Agent votes
            st.markdown("**Agent Analysis:**")
            for vote in decision.votes:
                agent_class = f"agent-{vote.agent_name.lower()}"
                icon = "🛡️" if vote.agent_name == "SENTINEL" else "⚡" if vote.agent_name == "VANGUARD" else "⚖️"
                
                st.markdown(f"""
                <div class='glass-card {agent_class}'>
                    <b>{icon} {vote.agent_name}</b> ({vote.agent_style})<br>
                    <span class='{get_vote_class(vote.vote)}'>{vote.vote.value.upper()}</span> — 
                    Confidence: {vote.confidence:.0%}<br>
                    <small>{vote.reasoning}</small><br>
                    <small>Key factors: {', '.join(vote.key_factors[:3])}</small>
                </div>
                """, unsafe_allow_html=True)
    
    # Portfolio summary
    st.markdown("---")
    st.markdown("### 📊 Portfolio Investment Matrix")
    
    portfolio_data = []
    for d in swarm_decisions:
        zone_match = zone_df[zone_df['name'] == d.gemeinde_name]
        if len(zone_match) > 0:
            z = zone_match.iloc[0]
            portfolio_data.append({
                "Gemeinde": d.gemeinde_name,
                "Decision": d.final_decision.value.upper(),
                "Consensus": f"{d.consensus_score:.0%}",
                "Risk": d.risk_level,
                "Homes": z['homes'],
                "Adoption %": z['adoption'],
                "Distance (m)": z['avg_dist_m'],
            })
    
    portfolio_df = pd.DataFrame(portfolio_data)
    st.dataframe(portfolio_df, use_container_width=True, hide_index=True)


# ============================================================
# TAB 2: Executive Overview
# ============================================================
with tab2:
    left, right = st.columns([1.2, 1])

    with left:
        st.markdown('### Strategic Snapshot')
        density_data = zone_df.groupby('density', as_index=False)['homes'].sum()
        fig_density = px.bar(
            density_data, x='density', y='homes', color='density',
            title='Building Density Distribution',
            labels={'homes': 'Homes', 'density': 'Density Class'},
            color_discrete_sequence=['#60a5fa', '#34d399', '#f59e0b']
        )
        fig_density.update_layout(
            paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
            font_color='#e5e7eb', height=320, showlegend=False, margin=dict(t=45, b=20)
        )
        st.plotly_chart(fig_density, use_container_width=True)

    with right:
        st.markdown('### Deployment Status')
        status_counts = zone_df.groupby('status', as_index=False)['homes'].sum()
        fig_status = px.pie(
            status_counts, names='status', values='homes', hole=0.55,
            title='Homes by Deployment Status', color='status',
            color_discrete_map={'deployed': '#10b981', 'partial': '#f59e0b', 'planned': '#60a5fa', 'unplanned': '#ef4444'}
        )
        fig_status.update_layout(
            paper_bgcolor='rgba(0,0,0,0)', font_color='#e5e7eb', height=320, margin=dict(t=45, b=20)
        )
        st.plotly_chart(fig_status, use_container_width=True)

    c1, c2 = st.columns(2)

    with c1:
        fig_dist = px.bar(
            zone_df.sort_values('avg_dist_m', ascending=False).head(15),
            x='name', y='avg_dist_m', color='status',
            title='Infrastructure Distance by Gemeinde',
            color_discrete_map={'deployed': '#10b981', 'partial': '#f59e0b', 'planned': '#60a5fa', 'unplanned': '#ef4444'}
        )
        fig_dist.update_layout(
            paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
            font_color='#e5e7eb', height=340, margin=dict(t=45, b=20)
        )
        fig_dist.update_xaxes(tickangle=25)
        st.plotly_chart(fig_dist, use_container_width=True)

    with c2:
        fig_adoption = px.bar(
            zone_df.sort_values('adoption', ascending=False).head(15),
            x='name', y='adoption', color='adoption',
            title='Adoption Rate by Gemeinde',
            color_continuous_scale=['#ef4444', '#f59e0b', '#10b981']
        )
        fig_adoption.add_hline(y=50, line_dash='dash', line_color='gray', annotation_text='Target 50%')
        fig_adoption.update_layout(
            paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
            font_color='#e5e7eb', height=340, coloraxis_showscale=False, margin=dict(t=45, b=20)
        )
        fig_adoption.update_xaxes(tickangle=25)
        st.plotly_chart(fig_adoption, use_container_width=True)


# ============================================================
# TAB 3: Financial Model
# ============================================================
with tab3:
    st.markdown('### Scenario Output')

    m1, m2, m3, m4, m5, m6 = st.columns(6)
    m1.metric('Total CAPEX', f'€{scenario["total_capex"]/1000:.0f}K', f'{phase_key} × {scenario["phase_multi"]:.2f}')
    m2.metric('Subscribers', f'{scenario["subs"]:,}', f'{take_rate}% take rate')
    m3.metric('Annual Revenue', f'€{scenario["annual_rev"]/1000:.0f}K', f'€{arpu}/month ARPU')
    m4.metric('EBITDA', f'€{scenario["ebitda"]/1000:.0f}K', f'{scenario["ebitda_margin"]:.0f}% margin')
    m5.metric('Payback', f'{roi["payback"]:.1f} yrs', 'Fast' if roi['payback'] < 7 else 'Slow')
    m6.metric('IRR', f'{roi["irr"]:.0f}%', '10-year horizon')

    st.markdown('### Cash Flow Projection')
    fig_cf = make_subplots(specs=[[{'secondary_y': True}]])
    cf_colors = ['#ef4444' if v < 0 else '#10b981' for v in cashflow_df['annual_cf_k']]

    fig_cf.add_trace(go.Bar(x=cashflow_df['year'], y=cashflow_df['annual_cf_k'],
               name='Annual CF (€K)', marker_color=cf_colors), secondary_y=False)
    fig_cf.add_trace(go.Scatter(x=cashflow_df['year'], y=cashflow_df['cumulative_k'],
                   name='Cumulative (€K)', line=dict(color='#60a5fa', width=3), mode='lines+markers'), secondary_y=True)
    fig_cf.add_hline(y=0, line_dash='dot', line_color='gray', secondary_y=True)
    fig_cf.update_layout(
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        font_color='#e5e7eb', height=420, margin=dict(t=20, b=20),
        legend=dict(orientation='h', yanchor='bottom', y=1.02)
    )
    st.plotly_chart(fig_cf, use_container_width=True)

    c1, c2 = st.columns(2)
    with c1:
        fig_npv = px.line(npv_df, x='discount_rate', y='npv_k', markers=True)
        fig_npv.add_hline(y=0, line_dash='dash', line_color='gray')
        fig_npv.add_vline(x=discount_rate, line_dash='dot', line_color='#60a5fa')
        fig_npv.update_traces(line_color='#60a5fa', marker_color='#93c5fd')
        fig_npv.update_layout(
            title='NPV Sensitivity', paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
            font_color='#e5e7eb', height=320, margin=dict(t=45, b=20)
        )
        st.plotly_chart(fig_npv, use_container_width=True)

    with c2:
        be_colors = ['#ef4444' if v < 0 else '#10b981' for v in breakeven_df['cumulative_k']]
        fig_be = go.Figure()
        fig_be.add_trace(go.Scatter(x=breakeven_df['year'], y=breakeven_df['cumulative_k'],
                    mode='lines+markers', line=dict(color='#34d399', width=3),
                    marker=dict(color=be_colors, size=9)))
        fig_be.add_hline(y=0, line_dash='dash', line_color='gray', annotation_text='Break-even')
        fig_be.update_layout(
            title='Break-even Analysis', paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
            font_color='#e5e7eb', height=320, margin=dict(t=45, b=20)
        )
        st.plotly_chart(fig_be, use_container_width=True)


# ============================================================
# TAB 4: Geo Intelligence
# ============================================================
with tab4:
    st.markdown('### Coverage Intelligence Map')

    status_colors = {'deployed': '#10b981', 'partial': '#f59e0b', 'planned': '#60a5fa', 'unplanned': '#ef4444'}
    zone_df['color'] = zone_df['status'].map(status_colors)
    zone_df['size'] = zone_df['homes'] / 20

    # Center map on data
    map_lat = zone_df['lat'].mean()
    map_lon = zone_df['lon'].mean()

    fig_map = go.Figure()
    for status, grp in zone_df.groupby('status'):
        fig_map.add_trace(go.Scattermapbox(
            lat=grp['lat'], lon=grp['lon'], mode='markers+text',
            marker=dict(size=grp['size'].clip(8, 40), color=status_colors.get(status), opacity=0.82),
            text=grp['name'], textposition='top center',
            hovertemplate='<b>%{text}</b><br>Homes: %{customdata[0]:,}<br>Adoption: %{customdata[1]:.1f}%<br>Status: ' + status,
            customdata=grp[['homes', 'adoption']].values,
            name=status.capitalize()
        ))

    fig_map.update_layout(
        mapbox=dict(style='carto-darkmatter', center=dict(lat=map_lat, lon=map_lon), zoom=8.5),
        height=550, margin=dict(t=0, b=0, l=0, r=0),
        paper_bgcolor='rgba(0,0,0,0)', font_color='#e5e7eb',
        legend=dict(orientation='h', yanchor='bottom', y=1.02)
    )
    st.plotly_chart(fig_map, use_container_width=True)

    st.markdown('### Gemeinde Priority Table')
    display_cols = ['name', 'landkreis', 'homes', 'adoption', 'avg_dist_m', 'status', 'ROI Score', 'Action']
    st.dataframe(
        zone_df[display_cols].sort_values(['ROI Score', 'adoption'], ascending=[True, False]),
        use_container_width=True, hide_index=True
    )


# ============================================================
# TAB 5: 3D Command View
# ============================================================
with tab5:
    st.markdown('### 3D Command View')
    
    zone_df['adoption_color_r'] = np.where(zone_df['adoption'] < 35, 239, np.where(zone_df['adoption'] < 50, 245, 16))
    zone_df['adoption_color_g'] = np.where(zone_df['adoption'] < 35, 68, np.where(zone_df['adoption'] < 50, 158, 185))
    zone_df['adoption_color_b'] = np.where(zone_df['adoption'] < 35, 68, np.where(zone_df['adoption'] < 50, 11, 129))

    column_layer = pdk.Layer(
        'ColumnLayer', data=zone_df,
        get_position='[lon, lat]', get_elevation='homes', elevation_scale=0.8, radius=1500,
        get_fill_color='[adoption_color_r, adoption_color_g, adoption_color_b, 210]',
        pickable=True, auto_highlight=True
    )

    deck = pdk.Deck(
        layers=[column_layer],
        initial_view_state=pdk.ViewState(latitude=map_lat, longitude=map_lon, zoom=8, pitch=50, bearing=15),
        tooltip={'html': '<b>{name}</b><br/>Homes: {homes}<br/>Adoption: {adoption}%'},
        map_style='light'
    )
    st.pydeck_chart(deck)


# ============================================================
# TAB 6: Technical Specifications
# ============================================================
with tab6:
    st.markdown('### 📐 FTTH Technical Specifications')
    st.markdown(
        "<div class='small-note'>Based on Deutsche Telekom KP18440 Planning Guidelines (August 2022)</div>",
        unsafe_allow_html=True
    )
    
    # GPON Specs
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### GPON Network Parameters")
        st.markdown(f"""
<div class='glass-card'>
<b>Bitrates</b><br>
• Downstream: <b>{GPONSpecs.DOWNSTREAM_GBPS} Gbit/s</b><br>
• Upstream: <b>{GPONSpecs.UPSTREAM_GBPS} Gbit/s</b><br><br>
<b>Wavelengths</b><br>
• Upstream (λ1): {GPONSpecs.WAVELENGTH_UPSTREAM} nm<br>
• Downstream (λ2): {GPONSpecs.WAVELENGTH_DOWNSTREAM} nm<br>
• TV Signal (λ3): {GPONSpecs.WAVELENGTH_TV} nm<br>
• Measurement (λ4): {GPONSpecs.WAVELENGTH_MEASUREMENT} nm
</div>
        """, unsafe_allow_html=True)
        
        st.markdown("#### Distance & Attenuation")
        st.markdown(f"""
<div class='glass-card'>
<b>Distance Limits</b><br>
• Max technical: <b>{GPONSpecs.MAX_DISTANCE_KM} km</b><br>
• Planning range: <b>{GPONSpecs.PLANNING_DISTANCE_KM} km</b><br><br>
<b>Attenuation Budget</b><br>
• Maximum: <b>{GPONSpecs.MAX_ATTENUATION_DB} dB</b><br>
• Minimum: <b>{GPONSpecs.MIN_ATTENUATION_DB} dB</b>
</div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("#### Splitter Specifications")
        splitter_data = []
        for ratio, spec in SPLITTER_SPECS.items():
            br = GPONSpecs.get_bitrate_per_user(int(ratio.split(":")[1]))
            splitter_data.append({
                "Ratio": ratio,
                "Attenuation": f"{spec.attenuation_db} dB",
                "DS/User": f"{br['downstream_mbps']} Mbit/s",
                "US/User": f"{br['upstream_mbps']} Mbit/s",
            })
        st.dataframe(pd.DataFrame(splitter_data), use_container_width=True, hide_index=True)
        
        st.markdown("#### Building Fiber Configuration")
        fiber_data = []
        for we_range, config in BUILDING_FIBER_CONFIG.items():
            fiber_data.append({
                "WE/Building": we_range,
                "Fibers": config["fibers"],
                "Splitter (Gebäude)": config["splitter_gebaeude"] or "-",
                "Splitter (NVt)": config["splitter_nvt"] or "-",
            })
        st.dataframe(pd.DataFrame(fiber_data), use_container_width=True, hide_index=True)
    
    st.markdown("---")
    
    # Deployment architectures
    st.markdown("#### Deployment Architectures")
    col1, col2, col3 = st.columns(3)
    
    for i, (dtype, config) in enumerate(DEPLOYMENT_CONFIGS.items()):
        with [col1, col2, col3][i]:
            icon = "🔵" if dtype == DeploymentType.MICRODUCT else "🟠" if dtype == DeploymentType.CONVENTIONAL else "🟢"
            st.markdown(f"""
<div class='glass-card'>
<b>{icon} {dtype.value.replace('_', ' ').title()}</b><br><br>
{config.description}<br><br>
<b>Max Distance:</b> {config.max_distance_m if config.max_distance_m < 9999 else '∞'} m<br>
<b>Use Case:</b> {config.use_case}
</div>
            """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # CAPEX Calculator
    st.markdown("#### 💰 CAPEX Estimator")
    
    calc_col1, calc_col2, calc_col3 = st.columns(3)
    with calc_col1:
        calc_distance = st.slider("Distance to NVt (m)", 100, 2000, 500, 50)
    with calc_col2:
        calc_we = st.slider("Residential Units (WE)", 1, 50, 8, 1)
    with calc_col3:
        calc_terrain = st.selectbox("Terrain Factor", [
            ("Standard (1.0x)", 1.0),
            ("Urban Dense (1.2x)", 1.2),
            ("Rural/Difficult (1.5x)", 1.5),
        ], format_func=lambda x: x[0])
    
    capex_estimate = estimate_capex_per_home(calc_distance, calc_we, DeploymentType.MICRODUCT, calc_terrain[1])
    
    st.markdown(f"""
<div class='glass-card' style='text-align: center;'>
<div style='font-size: 2rem; font-weight: 800; color: #3b82f6;'>€{capex_estimate['total_per_home']:,}</div>
<div style='color: #94a3b8;'>Estimated CAPEX per Home</div>
<br>
<small>Base: €{capex_estimate['base_cost']} | Distance: €{capex_estimate['distance_cost']} | Splitter: €{capex_estimate['splitter_cost']}</small>
</div>
    """, unsafe_allow_html=True)
    
    # Bitrate recommendation
    st.markdown("---")
    st.markdown("#### 📡 Bitrate Recommendation")
    
    br_col1, br_col2 = st.columns([1, 2])
    with br_col1:
        br_homes = st.number_input("Total Homes", 100, 10000, 1000, 100)
        br_adoption = st.slider("Expected Adoption %", 20, 80, 45, 5)
    
    with br_col2:
        br_rec = get_bitrate_recommendation(br_homes, br_adoption)
        st.markdown(f"**Concurrent users estimate:** {br_rec['concurrent_users_estimate']}")
        st.markdown(f"**Recommended splitting:** {br_rec['recommended']['splitting']}")
        st.markdown(f"**Downstream per user:** {br_rec['recommended']['downstream_mbps']} Mbit/s")
        st.markdown(f"**Upstream per user:** {br_rec['recommended']['upstream_mbps']} Mbit/s")
    
    # Glossary
    st.markdown("---")
    with st.expander("📚 Telekom Glossary"):
        for term, definition in TELEKOM_GLOSSARY.items():
            st.markdown(f"**{term}** — {definition}")


# ============================================================
# TAB 7: Executive Report
# ============================================================
with tab7:
    st.markdown('### Executive Report')

    # Top AI recommendations
    top_invest = [d for d in swarm_decisions if d.final_decision in [Vote.STRONG_INVEST, Vote.INVEST]][:5]
    
    st.markdown(f"""
### FTTH Expansion Business Case — Bavaria Region

**Date:** {pd.Timestamp.now().strftime('%d.%m.%Y')}  
**Region:** {region_filter}

---

#### 1. Market Overview
- **Gemeinden analyzed:** {len(zone_df)}
- **Total addressable homes:** {total_homes:,}
- **Current coverage:** {coverage_pct:.0f}% ({deployed_homes:,} homes passed)
- **Average adoption:** {avg_adoption:.1f}%

#### 2. AI Swarm Recommendations
| Priority | Gemeinde | Decision | Consensus | Homes |
|----------|----------|----------|-----------|-------|
""")
    
    for i, d in enumerate(top_invest, 1):
        z = zone_df[zone_df['name'] == d.gemeinde_name]
        homes_val = z['homes'].values[0] if len(z) > 0 else 0
        st.markdown(f"| {i} | {d.gemeinde_name} | {d.final_decision.value.upper()} | {d.consensus_score:.0%} | {homes_val:,} |")

    st.markdown(f"""

#### 3. Financial Summary
| Metric | Value |
|--------|-------|
| Scenario CAPEX | €{scenario['total_capex']/1000:.0f}K |
| Projected Annual Revenue | €{scenario['annual_rev']/1000:.0f}K |
| NPV (10y) | €{roi['npv']/1000:.0f}K |
| IRR | {roi['irr']:.0f}% |
| Payback Period | {roi['payback']:.1f} years |

#### 4. Strategic Recommendations
1. **Phase 1:** Deploy in AI-recommended STRONG_INVEST zones ({strong_invest} Gemeinden)
2. **Phase 2:** Expand to INVEST zones ({invest} Gemeinden) after Phase 1 validation
3. **Monitor:** HOLD zones ({hold} Gemeinden) for market condition changes
4. **Deprioritize:** DELAY/AVOID zones ({delay_avoid} Gemeinden) unless subsidies available

---
*Generated by FTTH Expansion Intelligence Platform — AI Swarm Analysis*
""")

    # Downloads
    st.markdown('### Downloads')
    c1, c2 = st.columns(2)
    with c1:
        st.download_button('⬇ Download Zone Data CSV', zone_df.to_csv(index=False).encode(), 'ftth_gemeinden.csv', 'text/csv')
    with c2:
        portfolio_df = pd.DataFrame(portfolio_data)
        st.download_button('⬇ Download AI Analysis CSV', portfolio_df.to_csv(index=False).encode(), 'ftth_ai_analysis.csv', 'text/csv')
