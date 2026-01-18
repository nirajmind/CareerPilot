import streamlit as st
from .analysis_helpers import init_analysis_history, save_analysis_to_db

# Auto‑restore last analysis on login
if "analysis_result" not in st.session_state:
    history = st.session_state.get("analysis_history", [])
    if history:
        st.session_state["analysis_result"] = history[0]

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
    init_analysis_history()
    # ----------------------------------------- # 🔹 Sidebar: Analysis History + Filters # ----------------------------------------- 
    with st.sidebar: 
        st.subheader("Analysis History") 
        history = st.session_state.get("analysis_history", []) 
        if not history: 
            st.info("No past analyses found.") 
        else: 
            st.markdown("### Filters") 
            job_titles = list({h["jd_text"].splitlines()[0] for h in history}) 
            selected_title = st.selectbox("Job Title", ["All"] + job_titles) 
            dates = list({extract_date(h) for h in history}) 
            selected_date = st.selectbox("Date", ["All"] + dates) 
            filtered = history 
            if selected_title != "All": 
                filtered = [h for h in filtered if h["jd_text"].startswith(selected_title)] 
            if selected_date != "All": 
                filtered = [h for h in filtered if extract_date(h) == selected_date] 
            st.markdown("---") 
            st.markdown("### Select Analysis") 
            for idx, item in enumerate(filtered): 
                ts = item.get("timestamp", "No timestamp")
                jd = item.get("jd_text", "")[:40]
                label = f"{ts} — {jd}..."
                if st.button(label, key=f"analysis_{idx}"): 
                    st.session_state["analysis_result"] = item 
                    st.rerun() 
        # Resume mock interview 
        st.markdown("---") 
        st.subheader("Resume Mock Interview") 
        if "analysis_result" in st.session_state: 
            mock = st.session_state["analysis_result"].get("mock_interview", {}) 
            questions = ( 
                mock.get("questions", []) + 
                mock.get("follow_ups", []) + 
                mock.get("behavioral", []) 
                ) 
            if questions: 
                last_question = questions[0] 
                if st.button(f"Resume: {last_question[:40]}..."): 
                    st.session_state["resume_mock_question"] = last_question 
                    st.session_state["current_view"] = "Mock Interview"
                    st.rerun()
                else: 
                    st.info("Run or load an analysis to resume mock interview.") 
        # ----------------------------------------- # 
        # 🔹 Main Analysis Page Content # 
        # ----------------------------------------- 
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

            # Store analysis result
            result["resume_text"] = st.session_state["resume_text"]
            result["jd_text"] = st.session_state["jd_text"]
            st.session_state["analysis_result"] = result

            # Save to DB
            save_analysis_to_db(result)

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

def extract_date(item):
    ts = item.get("timestamp")
    if not ts:
        return None

    # ts is always a string from FastAPI
    return ts[:10]

