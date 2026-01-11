import streamlit as st
import requests
import os

API_URL = os.getenv("API_URL", "http://localhost:8000")

def render_video_page():
    st.header("Analyze from Video")
    st.write("Upload a video scroll of a job description and your resume.")

    uploaded_file = st.file_uploader("Choose a video file...", type=["mp4", "mov", "avi"])

    if uploaded_file is not None:
        st.video(uploaded_file)

        if st.button("Analyze Video"):
            files = {"video_file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
            
            headers = {}
            if st.session_state.get("token"):
                headers["Authorization"] = f"Bearer {st.session_state.token}"

            try:
                with st.spinner("Uploading and analyzing video... This may take a moment."):
                    response = requests.post(f"{API_URL}/analyze_video", files=files, headers=headers)
                
                if response.status_code == 200:
                    st.success("Analysis complete!")
                    # Store the analysis in session state to be displayed on the analysis page
                    st.session_state.analysis_result = response.json()
                    st.write("Navigate to the 'Run Analysis' page to see the results.")
                else:
                    st.error(f"Analysis failed. Server responded with: {response.status_code}")
                    st.json(response.json())
            except requests.exceptions.RequestException as e:
                st.error(f"Failed to connect to the API: {e}")
