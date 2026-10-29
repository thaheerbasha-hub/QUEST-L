import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import os
import sys

# Ensure root directory is on path for modules
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

from modules.data_loader import load_data, calculate_bill_amount, DEFAULT_SLABS
from modules.insights_engine import generate_three_insights
from modules.forecast_engine import forecast_next_bill
from modules.coach_ai import ask_coach
from modules.pdf_report import generate_pdf_audit
from modules.auth import init_auth, render_login_gate, logout_user
from modules.ui_theme import apply_theme

# --- Page Config ---
st.set_page_config(
    page_title="Power Bill Coach - Electricity Waste & Forecast",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Apply UI Theme
apply_theme()
init_auth()

# --- Login Gate ---
if not st.session_state["authenticated"]:
    render_login_gate()
    st.stop()

# --- Data Selection & Loading ---
SAMPLE_DATASETS = {
    "Apartment with 2 ACs (Evening & Night Spikes)": os.path.join(CURRENT_DIR, "sample_data", "apartment_with_ac.csv"),
    "Family of 4 with High Vampire Load (Standby Waste)": os.path.join(CURRENT_DIR, "sample_data", "family_high_vampire_load.csv"),
    "Housing Society (Water Pumps & Common Lighting)": os.path.join(CURRENT_DIR, "sample_data", "society_common_meters.csv")
}

# --- Sidebar ---
with st.sidebar:
    st.markdown("### ⚡ **Power Bill Coach**")
    st.markdown(f"👤 Logged in as: **{st.session_state.get('user_name', 'User')}**")
    
    st.markdown("---")
    st.markdown("#### 📂 **Select Meter Dataset**")
    default_persona = st.session_state.get("selected_persona", list(SAMPLE_DATASETS.keys())[0])
    selected_profile = st.selectbox(
        "Choose Household / Society Profile:",
        list(SAMPLE_DATASETS.keys()),
        index=list(SAMPLE_DATASETS.keys()).index(default_persona) if default_persona in SAMPLE_DATASETS else 0
    )

    uploaded_file = st.file_uploader("Or upload custom meter CSV (timestamp, kwh):", type=["csv"])

    st.markdown("---")
    st.markdown("#### ⚙️ **Tariff Settings (INR)**")
    base_unit_rate = st.slider("Average Base Rate (₹ / kWh)", min_value=4.0, max_value=12.0, value=6.5, step=0.5)

    st.markdown("---")
    if st.button("🚪 Sign Out", use_container_width=True):
        logout_user()

# Load chosen dataset
if uploaded_file is not None:
    df = load_data(uploaded_file)
    dataset_name = uploaded_file.name
else:
    file_path = SAMPLE_DATASETS[selected_profile]
    df = load_data(file_path)
    dataset_name = selected_profile

# Compute Insights & Forecast
insights, total_savings = generate_three_insights(df, avg_rate=base_unit_rate)
forecast_results = forecast_next_bill(df, savings_potential_rupees=total_savings)

# --- Top Header ---
c_title, c_act = st.columns([3, 1])
with c_title:
    st.markdown('<div class="coach-title">⚡ Power Bill Coach</div>', unsafe_allow_html=True)
    st.markdown(
        f'<div class="coach-subtitle">Analyzing <b>{dataset_name}</b> • Discover hidden electricity leaks, get plain-English advice, and control your next bill.</div>',
        unsafe_allow_html=True
    )

with c_act:
    # 1-Click PDF Report Download Button
    pdf_bytes = generate_pdf_audit(insights, forecast_results, profile_name=dataset_name)
    st.download_button(
        label="📄 Download Energy Audit (PDF)",
        data=pdf_bytes,
        file_name="Power_Bill_Audit_Report.pdf",
        mime="application/pdf",
        use_container_width=True,
        type="primary"
    )

# --- Top Metric Tiles ---
m1, m2, m3, m4 = st.columns(4)

with m1:
    st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Projected Next Bill</div>
            <div class="metric-value">₹{forecast_results['forecast_bill_inr']:,.0f}</div>
            <div class="metric-sub" style="color: #EF4444;">▲ At current consumption rate</div>
        </div>
    """, unsafe_allow_html=True)

with m2:
    st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Potential Monthly Waste</div>
            <div class="metric-value" style="color: #10B981;">₹{forecast_results['achievable_savings_inr']:,.0f}</div>
            <div class="metric-sub">✓ Avoidable with 3 Coach insights</div>
        </div>
    """, unsafe_allow_html=True)

with m3:
    st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Optimized Bill Target</div>
            <div class="metric-value" style="color: #06B6D4;">₹{forecast_results['optimized_bill_inr']:,.0f}</div>
            <div class="metric-sub">Target if waste is eliminated</div>
        </div>
    """, unsafe_allow_html=True)

with m4:
    st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Projected 30-Day Units</div>
            <div class="metric-value">{forecast_results['forecast_kwh']:,.0f} <span style="font-size: 1rem; color: #94A3B8;">kWh</span></div>
            <div class="metric-sub">{df['date'].nunique()} days of meter history analyzed</div>
        </div>
    """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# --- Main Dashboard Tabs ---
tab_insights, tab_forecast, tab_chat, tab_data = st.tabs([
    "🔍 Three Plain-English Insights",
    "📈 Next Bill Forecast & Slabs",
    "🤖 Ask Power Coach (AI Chat)",
    "📊 Meter Data & Daily Breakdown"
])

# ------------------------------------------------------------------
# TAB 1: THREE PLAIN-ENGLISH INSIGHTS
# ------------------------------------------------------------------
with tab_insights:
    st.markdown("### 🔍 **Three Waste Discoveries Found in Your Meter Data**")
    st.caption("Here is exactly why your electricity bill jumps, translated into plain words without jargon.")

    for i, ins in enumerate(insights, 1):
        box_class = "danger" if "High" in ins["status"] or "Severe" in ins["status"] or "Jump" in ins["status"] else "normal"
        badge_class = "danger" if box_class == "danger" else "normal"

        with st.container(border=True):
            col_left, col_right = st.columns([3, 1.2])
            with col_left:
                st.markdown(f"#### {ins['icon']} **Insight {i}: {ins['title']}**")
                st.markdown(f"**What the data says:** {ins['explanation']}")
                st.info(ins['action_plan'])
            with col_right:
                st.metric(label=ins['metric_label'], value=ins['metric_value'])
                st.markdown(f"""
                    <div style="background: rgba(16, 185, 129, 0.12); padding: 0.8rem; border-radius: 8px; border: 1px solid rgba(16, 185, 129, 0.3); text-align: center;">
                        <span style="font-size: 0.8rem; color: #94A3B8; text-transform: uppercase; font-weight: 700;">Potential Savings</span><br>
                        <span style="font-size: 1.5rem; font-weight: 800; color: #10B981;">{ins['potential_saving']}</span>
                    </div>
                """, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("#### 🕒 **24-Hour Electricity Consumption Curve (Where the Power Goes)**")
    hourly_avg = df.groupby("hour")["kwh"].mean().reset_index()
    
    fig_hourly = go.Figure()
    fig_hourly.add_trace(go.Scatter(
        x=hourly_avg["hour"],
        y=hourly_avg["kwh"],
        mode="lines+markers",
        line=dict(color="#10B981", width=3),
        marker=dict(size=6, color="#06B6D4"),
        name="Average Units / Hour"
    ))
    
    # Highlight Midnight Vampire Window (1 AM - 5 AM)
    fig_hourly.add_vrect(
        x0=1, x1=5,
        fillcolor="red", opacity=0.12,
        annotation_text="Vampire Standby Window (1 AM - 5 AM)",
        annotation_position="top left"
    )
    # Highlight Peak Window (6 PM - 10 PM)
    fig_hourly.add_vrect(
        x0=18, x1=22,
        fillcolor="amber", opacity=0.15,
        annotation_text="Evening Peak Demand (6 PM - 10 PM)",
        annotation_position="top right"
    )
    
    fig_hourly.update_layout(
        xaxis_title="Hour of the Day (0:00 to 23:00)",
        yaxis_title="Average Electricity Draw (kWh / hour)",
        template="plotly_dark",
        height=380,
        margin=dict(l=20, r=20, t=30, b=20)
    )
    st.plotly_chart(fig_hourly, use_container_width=True)

# ------------------------------------------------------------------
# TAB 2: NEXT BILL FORECAST & SLAB BREAKDOWN
# ------------------------------------------------------------------
with tab_forecast:
    st.markdown("### 📈 **Next Bill Forecast: 30-Day Outlook**")
    st.caption("Statistical forward projection combining your 14-day weighted run-rate and weekday/weekend patterns.")

    fc_col1, fc_col2 = st.columns([2, 1])

    with fc_col1:
        # Forecast Chart: History + Projected Forward 30 Days
        history_tail = forecast_results["daily_history"].tail(30)
        forecast_df = forecast_results["forecast_df"]

        fig_forecast = go.Figure()
        # Historical Trace
        fig_forecast.add_trace(go.Scatter(
            x=history_tail["date"],
            y=history_tail["kwh"],
            mode="lines+markers",
            name="Past 30 Days (Actual)",
            line=dict(color="#64748B", width=2)
        ))
        # Forecast Trace
        fig_forecast.add_trace(go.Scatter(
            x=forecast_df["date"],
            y=forecast_df["forecast_kwh"],
            mode="lines+markers",
            name="Next 30 Days (Projected)",
            line=dict(color="#06B6D4", width=3, dash="dot")
        ))
        # Confidence Band
        fig_forecast.add_trace(go.Scatter(
            x=forecast_df["date"].tolist() + forecast_df["date"].tolist()[::-1],
            y=forecast_df["upper_bound"].tolist() + forecast_df["lower_bound"].tolist()[::-1],
            fill='toself',
            fillcolor='rgba(6, 182, 212, 0.1)',
            line=dict(color='rgba(255,255,255,0)'),
            hoverinfo="skip",
            showlegend=True,
            name="95% Confidence Interval"
        ))

        fig_forecast.update_layout(
            xaxis_title="Timeline",
            yaxis_title="Daily Units (kWh)",
            template="plotly_dark",
            height=400,
            margin=dict(l=20, r=20, t=30, b=20)
        )
        st.plotly_chart(fig_forecast, use_container_width=True)

    with fc_col2:
        st.markdown("#### 🧾 **Slab-Wise Bill Breakdown**")
        breakdown_df = pd.DataFrame(forecast_results["bill_breakdown"])
        if not breakdown_df.empty:
            st.dataframe(
                breakdown_df[["slab", "units", "rate", "cost"]].rename(columns={
                    "slab": "Tariff Tier",
                    "units": "Units (kWh)",
                    "rate": "Rate (₹)",
                    "cost": "Cost (₹)"
                }),
                use_container_width=True,
                hide_index=True
            )
        
        st.markdown(f"""
            <div style="background: rgba(30, 41, 59, 0.7); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 10px; padding: 1rem; margin-top: 1rem;">
                <div style="display: flex; justify-content: space-between; font-size: 0.9rem; color: #94A3B8;">
                    <span>Energy Charges:</span>
                    <span>₹{forecast_results['energy_cost']:,.2f}</span>
                </div>
                <div style="display: flex; justify-content: space-between; font-size: 0.9rem; color: #94A3B8; margin-top: 0.4rem;">
                    <span>Fixed / Meter Charge:</span>
                    <span>₹{forecast_results['fixed_charge']:,.2f}</span>
                </div>
                <hr style="border-color: rgba(255,255,255,0.1); margin: 0.6rem 0;">
                <div style="display: flex; justify-content: space-between; font-weight: 800; font-size: 1.2rem; color: #F8FAFC;">
                    <span>Total Projected Bill:</span>
                    <span style="color: #EF4444;">₹{forecast_results['forecast_bill_inr']:,.2f}</span>
                </div>
                <div style="display: flex; justify-content: space-between; font-weight: 700; font-size: 0.95rem; color: #10B981; margin-top: 0.5rem;">
                    <span>With Coach Plan:</span>
                    <span>₹{forecast_results['optimized_bill_inr']:,.2f}</span>
                </div>
            </div>
        """, unsafe_allow_html=True)

# ------------------------------------------------------------------
# TAB 3: ASK POWER COACH (AI CHAT)
# ------------------------------------------------------------------
with tab_chat:
    st.markdown("### 🤖 **Ask Power Coach (Plain-English Q&A)**")
    st.caption("Ask questions about your appliances, bill spikes, or ways to save money.")

    # Initialize chat history
    if "chat_messages" not in st.session_state:
        st.session_state["chat_messages"] = [
            {"role": "assistant", "content": "Hello! I am your **Power Bill Coach**. I've audited your meter data and found ₹" + f"{forecast_results['achievable_savings_inr']:,.0f}" + " in avoidable electricity waste. How can I help you save today?"}
        ]

    # Quick prompt chips
    st.markdown("**Quick questions to ask:**")
    qc1, qc2, qc3, qc4 = st.columns(4)
    with qc1:
        if st.button("❄️ Why does my AC bill jump?", use_container_width=True):
            st.session_state["pending_query"] = "Why does my AC bill jump?"
    with qc2:
        if st.button("🚿 How to stop geyser waste?", use_container_width=True):
            st.session_state["pending_query"] = "How to stop geyser waste?"
    with qc3:
        if st.button("🧛 Explain midnight vampire power", use_container_width=True):
            st.session_state["pending_query"] = "Explain midnight vampire power"
    with qc4:
        if st.button("💡 Top 3 ways to cut ₹1,000", use_container_width=True):
            st.session_state["pending_query"] = "Top 3 ways to cut my bill by ₹1000"

    # Display chat history
    for msg in st.session_state["chat_messages"]:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Handle input
    chat_input = st.chat_input("Type your question in plain words (e.g. 'How much does running a 1.5 ton AC cost per hour?')...")
    query_to_process = chat_input or st.session_state.pop("pending_query", None)

    if query_to_process:
        st.session_state["chat_messages"].append({"role": "user", "content": query_to_process})
        with st.chat_message("user"):
            st.markdown(query_to_process)

        # Generate response
        response = ask_coach(query_to_process, insights_list=insights, forecast_data=forecast_results)
        st.session_state["chat_messages"].append({"role": "assistant", "content": response})
        with st.chat_message("assistant"):
            st.markdown(response)

# ------------------------------------------------------------------
# TAB 4: METER DATA & DAILY BREAKDOWN
# ------------------------------------------------------------------
with tab_data:
    st.markdown("### 📊 **Raw Meter Readings & Historical Stats**")
    
    st.markdown("#### Daily Consumption History (Last 30 Days)")
    daily_summary = df.groupby("date").agg(
        total_kwh=("kwh", "sum"),
        peak_kwh=("kwh", lambda x: x[df.loc[x.index, "hour"].between(18, 21)].sum()),
        night_kwh=("kwh", lambda x: x[df.loc[x.index, "hour"].between(1, 4)].sum())
    ).reset_index().tail(30)

    daily_summary["estimated_cost_inr"] = (daily_summary["total_kwh"] * base_unit_rate).round(2)

    st.dataframe(
        daily_summary.rename(columns={
            "date": "Date",
            "total_kwh": "Total Daily (kWh)",
            "peak_kwh": "Peak Evening (kWh)",
            "night_kwh": "Night Standby (kWh)",
            "estimated_cost_inr": "Est. Cost (₹)"
        }),
        use_container_width=True,
        hide_index=True
    )
