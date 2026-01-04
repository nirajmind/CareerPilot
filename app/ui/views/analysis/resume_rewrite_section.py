import streamlit as st

def render_resume_rewrite_section(result):
    st.subheader("Resume Rewrite")

    rewritten_resume = result["resume_rewrite"]

    st.text_area("Generated Resume", rewritten_resume, height=300)

    st.download_button(
        label="Download Resume",
        data=rewritten_resume,
        file_name="rewritten_resume.txt",
        mime="text/plain"
    )