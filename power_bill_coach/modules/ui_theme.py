import streamlit as st

def apply_theme():
    """Injects high-impact custom CSS for Power Bill Coach."""
    custom_css = """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;600&display=swap');

    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', -apple-system, sans-serif;
    }

    /* Main background & headers */
    .main .block-container {
        padding-top: 1.8rem;
        padding-bottom: 2.5rem;
        max-width: 1200px;
    }

    /* Header title styling */
    .coach-title {
        font-size: 2.2rem;
        font-weight: 800;
        background: linear-gradient(135deg, #10B981 0%, #06B6D4 50%, #3B82F6 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.2rem;
        letter-spacing: -0.02em;
    }

    .coach-subtitle {
        color: #94A3B8;
        font-size: 1.05rem;
        margin-bottom: 1.5rem;
    }

    /* Metric cards */
    .metric-card {
        background: linear-gradient(145deg, rgba(30, 41, 59, 0.7) 0%, rgba(15, 23, 42, 0.9) 100%);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 14px;
        padding: 1.2rem;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.25);
        backdrop-filter: blur(10px);
        transition: transform 0.2s ease, border-color 0.2s ease;
    }
    .metric-card:hover {
        border-color: rgba(16, 185, 129, 0.4);
        transform: translateY(-2px);
    }
    .metric-label {
        font-size: 0.85rem;
        color: #94A3B8;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-bottom: 0.4rem;
    }
    .metric-value {
        font-size: 1.8rem;
        font-weight: 800;
        color: #F8FAFC;
        font-family: 'JetBrains Mono', monospace;
    }
    .metric-sub {
        font-size: 0.82rem;
        color: #10B981;
        margin-top: 0.3rem;
        font-weight: 500;
    }

    /* Insight card styling */
    .insight-box {
        background: #1E293B;
        border-radius: 14px;
        padding: 1.4rem;
        margin-bottom: 1.2rem;
        border-left: 5px solid #10B981;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.15);
    }
    .insight-box.warning {
        border-left-color: #F59E0B;
    }
    .insight-box.danger {
        border-left-color: #EF4444;
    }

    .insight-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 0.75rem;
    }
    .insight-badge {
        display: inline-block;
        padding: 0.25rem 0.65rem;
        font-size: 0.78rem;
        font-weight: 700;
        border-radius: 9999px;
        background: rgba(16, 185, 129, 0.15);
        color: #34D399;
    }
    .insight-badge.warning {
        background: rgba(245, 158, 11, 0.15);
        color: #FBBF24;
    }
    .insight-badge.danger {
        background: rgba(239, 68, 68, 0.15);
        color: #F87171;
    }

    /* Saving callout */
    .saving-pill {
        background: linear-gradient(135deg, rgba(16, 185, 129, 0.2) 0%, rgba(6, 182, 212, 0.2) 100%);
        border: 1px solid rgba(16, 185, 129, 0.4);
        padding: 0.4rem 0.8rem;
        border-radius: 8px;
        color: #34D399;
        font-weight: 700;
        font-size: 0.95rem;
        display: inline-block;
    }

    /* Buttons */
    .stButton>button {
        border-radius: 8px;
        font-weight: 600;
        transition: all 0.2s ease;
    }
    .stButton>button:hover {
        box-shadow: 0 0 15px rgba(16, 185, 129, 0.4);
    }

    /* Tab navigation styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px 8px 0 0;
        padding: 8px 18px;
        font-weight: 600;
    }
    </style>
    """
    st.markdown(custom_css, unsafe_allow_html=True)
