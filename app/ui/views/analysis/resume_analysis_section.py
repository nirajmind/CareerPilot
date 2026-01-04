import streamlit as st

def render_resume_analysis_section(result):
    st.subheader("Resume Analysis")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### Summary")
        st.write(result["resume_analysis"]["summary"])

    with col2:
        st.markdown("### Strengths")
        st.write("\n".join(f"- {s}" for s in result["resume_analysis"]["strengths"]))

    st.markdown("### Gaps")
    st.write("\n".join(f"- {g}" for g in result["resume_analysis"]["gaps"]))

    st.markdown("### Recommendations")
    st.write("\n".join(f"- {r}" for r in result["resume_analysis"]["recommendations"]))