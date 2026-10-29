import streamlit as st

def init_auth():
    """Initializes authentication state in Streamlit session_state."""
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False
    if "user_name" not in st.session_state:
        st.session_state["user_name"] = None
    if "user_email" not in st.session_state:
        st.session_state["user_email"] = None

def login_user(username, email="user@example.com"):
    st.session_state["authenticated"] = True
    st.session_state["user_name"] = username
    st.session_state["user_email"] = email

def logout_user():
    st.session_state["authenticated"] = False
    st.session_state["user_name"] = None
    st.session_state["user_email"] = None
    st.rerun()

def render_login_gate():
    """Renders a sleek login and 1-click evaluator demo modal."""
    st.markdown("""
        <div style="text-align: center; margin-bottom: 2rem;">
            <div style="font-size: 3rem;">⚡</div>
            <h1 style="margin: 0; font-size: 2.2rem; font-weight: 800; color: #10B981;">Power Bill Coach</h1>
            <p style="color: #94A3B8; font-size: 1.05rem; margin-top: 0.5rem;">
                Find hidden electricity waste, understand your meter data in plain English, and forecast your next bill.
            </p>
        </div>
    """, unsafe_allow_html=True)

    c1, c2, c3 = st.columns([1, 1.8, 1])
    with c2:
        with st.container(border=True):
            st.markdown("### 🔐 Welcome to Power Bill Coach")
            
            tab_demo, tab_login = st.tabs(["⚡ Instant Demo / Evaluator Access", "🔑 Member Login"])

            with tab_demo:
                st.info("💡 **Instant Demo:** Test the full system immediately without registering.")
                selected_persona = st.selectbox(
                    "Select a household profile to test:",
                    [
                        "Apartment with 2 ACs (Evening & Night Spikes)",
                        "Family of 4 with High Vampire Load (Standby Waste)",
                        "Housing Society (Water Pumps & Common Lighting)"
                    ]
                )
                if st.button("🚀 Launch Dashboard as Guest Evaluator", use_container_width=True, type="primary"):
                    login_user("Guest Evaluator", "evaluator@demo.com")
                    st.session_state["selected_persona"] = selected_persona
                    st.rerun()

            with tab_login:
                email = st.text_input("Email address", placeholder="name@domain.com")
                password = st.text_input("Password", type="password")
                if st.button("Sign In", use_container_width=True):
                    if email and password:
                        name = email.split("@")[0].title()
                        login_user(name, email)
                        st.rerun()
                    else:
                        st.error("Please enter email and password.")
