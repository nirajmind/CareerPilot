import streamlit as st

def render_jd_analysis_section(result):
    st.subheader("Job Description Analysis")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### Summary")
        st.write(result["jd_analysis"]["summary"])

    with col2:
        st.markdown("### Must Haves")
        st.write("\n".join(f"- {m}" for m in result["jd_analysis"]["must_haves"]))

    st.markdown("### Nice to Haves")
    st.write("\n".join(f"- {n}" for n in result["jd_analysis"]["nice_to_haves"]))

    st.markdown("### Hidden Signals")
    st.write("\n".join(f"- {h}" for h in result["jd_analysis"]["hidden_signals"]))