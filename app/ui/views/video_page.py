import streamlit as st
import requests
import os

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

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

def render_video_page():
    st.header("Analyze from Video")
    st.write("Upload a video scroll of a job description and your resume.")

    uploaded_file = st.file_uploader("Choose a video file...", type=["mp4", "mov", "avi"])

    if uploaded_file is not None:
        st.video(uploaded_file)

        if st.button("Analyze Video"):
            files = {
                "video_file": (
                    uploaded_file.name,
                    uploaded_file.getvalue(),
                    uploaded_file.type
                )
            }

            # Use consistent token key
            headers = {}
            token = st.session_state.get("token")
            if token:
                headers["Authorization"] = f"Bearer {token}"

            try:
                with st.spinner("Uploading and analyzing video... This may take a moment."):
                    response = requests.post(
                        f"{BACKEND_URL}/analyze_video",
                        files=files,
                        headers=headers
                    )

                if response.status_code == 200:
                    data = response.json()

                    # Store analysis in session state
                    st.session_state["analysis"] = data

                    st.success("Analysis complete!")

                    st.session_state["analysis_result"] = data
                    st.subheader("CareerPilot Analysis")
                    render_fitgraph_section(data)
                    render_resume_analysis_section(data)
                    render_jd_analysis_section(data)
                    render_resume_fit_section(data)
                    render_skill_matrix_section(data)
                    render_preparation_plan_section(data)
                    render_mock_interview_section(data)
                    render_resume_rewrite_section(data)
                    render_next_steps_section(data)

                else:
                    st.error(f"Analysis failed. Server responded with: {response.status_code}")
                    st.json(response.json())

            except requests.exceptions.RequestException as e:
                st.error(f"Failed to connect to the API: {e}")
