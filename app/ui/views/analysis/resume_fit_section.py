import streamlit as st

def render_resume_fit_section(result):
    st.subheader("Resume Fit")

    fit_summary = (
        result["fitgraph"].get("fit_summary")
        or result["resume_analysis"].get("summary", "No summary available.")
    )

    matched_list = ", ".join(result["fitgraph"].get("matching_skills", []))
    gaps_list = ", ".join(result["fitgraph"].get("missing_skills", []))

    text = (
        "Resume Fit Summary\n\n"
        f"{fit_summary}\n\n"
        f"Keywords matched: {matched_list}\n"
        f"Gaps: {gaps_list}"
    )

    st.text_area("Resume Fit Summary", text, height=200)