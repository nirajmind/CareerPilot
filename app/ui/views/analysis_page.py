import streamlit as st
from views.analysis import (
    render_fitgraph_section,
    render_resume_fit_section,
    render_resume_analysis_section,
    render_jd_analysis_section,
    render_skill_matrix_section,
    render_preparation_plan_section,
    render_mock_interview_section,
    render_resume_rewrite_section,
    render_next_steps_section
)
from .analysis_page_helpers import call_analysis_api

def render_analysis_page():

    st.header("CareerPilot Analysis")

    if "resume_text" not in st.session_state or "jd_text" not in st.session_state:
        st.warning("Please provide both resume and job description first.")
        return

    if st.button("Run Analysis"):
        with st.spinner("Analyzing..."):
            result = call_analysis_api(
                st.session_state["resume_text"],
                st.session_state["jd_text"]
            )
            st.session_state["analysis_result"] = result
            st.success("Analysis complete!")

    if "analysis_result" in st.session_state:
        result = st.session_state["analysis_result"]

        render_fitgraph_section(result)
        render_resume_analysis_section(result)
        render_jd_analysis_section(result)
        render_resume_fit_section(result)
        render_skill_matrix_section(result)
        render_preparation_plan_section(result)
        render_mock_interview_section(result)
        render_resume_rewrite_section(result)
        render_next_steps_section(result)