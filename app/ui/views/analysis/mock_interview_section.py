import streamlit as st

def render_mock_interview_section(result):
    st.subheader("Mock Interview Questions")

    mock = result.get("mock_interview", {})
    questions = mock.get("questions", [])
    follow_ups = mock.get("follow_ups", [])
    behavioral = mock.get("behavioral", [])
    # Flatten all questions into one list 
    all_questions = questions + follow_ups + behavioral

    # No questions at all
    if not questions and not follow_ups and not behavioral:
        st.info("No mock interview questions were generated.")
        return

    # --- Technical Questions ---
    if questions:
        st.session_state["technical_questions"] = questions
        st.markdown("### Technical Questions")
        for i, q in enumerate(questions, start=1):
            st.markdown(f"**{i}.** {q}")

    # --- Follow-up Questions ---
    if follow_ups:
        st.session_state["follow_ups"] = follow_ups
        st.markdown("### Follow-up Questions")
        for i, q in enumerate(follow_ups, start=1):
            st.markdown(f"**{i}.** {q}")

    # --- Behavioral Questions ---
    if behavioral:
        st.session_state["behavioral_questions"] = behavioral
        st.markdown("### Behavioral Questions")
        for i, q in enumerate(behavioral, start=1):
            st.markdown(f"**{i}.** {q}")
            
    st.session_state["all_questions"] = all_questions
    st.markdown("---")

    # CTA to go to the dedicated practice page
    if st.button("Start Practice", type="primary"):
        st.session_state["current_page"] = "Mock Interview"
        st.rerun()
