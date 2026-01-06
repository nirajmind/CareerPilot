import streamlit as st
from app.ui.views.resume_page import render_resume_page
from app.ui.views.jd_page import render_jd_page
from app.ui.views.analysis_page import render_analysis_page
from app.ui.views.auth_page import render_auth_page

st.set_page_config(page_title="CareerPilot", layout="wide")

st.sidebar.title("CareerPilot")

# Initialize session state
if 'token' not in st.session_state:
    st.session_state.token = None
    st.session_state.user = None

# --- Page Navigation ---
if not st.session_state.token:
    render_auth_page()
else:
    page = st.sidebar.radio(
        "Navigate",
        ["Resume Input", "Job Description", "Run Analysis"]
    )

    st.sidebar.success(f"Logged in as {st.session_state.user['username']}")
    if st.sidebar.button("Logout"):
        st.session_state.token = None
        st.session_state.user = None
        st.rerun()

    if page == "Resume Input":
        render_resume_page()
    elif page == "Job Description":
        render_jd_page()
    elif page == "Run Analysis":
        render_analysis_page()