import streamlit as st

from app.ui.views.resume_page import render_resume_page
from app.ui.views.jd_page import render_jd_page
from app.ui.views.video_page import render_video_page
from app.ui.views.analysis_page import render_analysis_page
from app.ui.views.auth_page import render_auth_page
from app.ui.views.mock_interview_page import render_mock_interview_page

st.set_page_config(page_title="CareerPilot", layout="wide")

st.sidebar.title("CareerPilot")

# ---------------------------------------------------------
# SESSION INITIALIZATION
# ---------------------------------------------------------
if "token" not in st.session_state:
    st.session_state.token = None
    st.session_state.user = None

if "current_page" not in st.session_state:
    st.session_state["current_page"] = "Resume Input"

# ---------------------------------------------------------
# AUTH GATE
# ---------------------------------------------------------
if not st.session_state.token:
    render_auth_page()

else:
    # ---------------------------------------------------------
    # SIDEBAR NAVIGATION
    # ---------------------------------------------------------
    pages = [
        "Resume Input",
        "Job Description",
        "Video Upload",
        "Run Analysis",
        "Mock Interview",
    ]

    page = st.sidebar.radio(
        "Navigate",
        pages,
        index=pages.index(st.session_state["current_page"]),
        key="main_nav_radio",   # optional but safe
    )

    st.session_state["current_page"] = page

    # ---------------------------------------------------------
    # USER INFO + LOGOUT
    # ---------------------------------------------------------
    if st.session_state.user:
        st.sidebar.success(f"Logged in as {st.session_state.user['username']}")

    if st.sidebar.button("Logout"):
        st.session_state.token = None
        st.session_state.user = None
        st.session_state["current_page"] = "Resume Input"
        st.rerun()

    # ---------------------------------------------------------
    # PAGE ROUTING
    # ---------------------------------------------------------
    if page == "Resume Input":
        render_resume_page()

    elif page == "Job Description":
        render_jd_page()

    elif page == "Video Upload":
        render_video_page()

    elif page == "Run Analysis":
        render_analysis_page()

    elif page == "Mock Interview":
        render_mock_interview_page()
