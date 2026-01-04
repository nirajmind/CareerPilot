import streamlit as st

def render_preparation_plan_section(result):
    st.subheader("Preparation Plan")

    st.markdown("### Steps")
    st.write("\n".join(f"- {s}" for s in result["preparation_plan"]["steps"]))

    st.markdown("### Priority")
    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("#### High")
        st.write("\n".join(f"- {x}" for x in result["preparation_plan"]["priority"]["high"]))

    with col2:
        st.markdown("#### Medium")
        st.write("\n".join(f"- {x}" for x in result["preparation_plan"]["priority"]["medium"]))

    with col3:
        st.markdown("#### Low")
        st.write("\n".join(f"- {x}" for x in result["preparation_plan"]["priority"]["low"]))