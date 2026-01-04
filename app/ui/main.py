import streamlit as st
from views.resume_page import render_resume_page
from views.jd_page import render_jd_page
from views.analysis_page import render_analysis_page

st.set_page_config(page_title="CareerPilot", layout="wide")

st.sidebar.title("CareerPilot")
page = st.sidebar.radio(
    "Navigate",
    ["Resume Input", "Job Description", "Run Analysis"]
)

if page == "Resume Input":
    render_resume_page()

elif page == "Job Description":
    render_jd_page()

elif page == "Run Analysis":
    render_analysis_page()