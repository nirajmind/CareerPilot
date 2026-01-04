import streamlit as st
import requests
import os

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

def call_evaluate_answer(question, user_answer, resume_text, jd_text):
    url = f"{BACKEND_URL}/evaluate_answer"
    payload = {
        "question": question,
        "user_answer": user_answer,
        "resume_text": resume_text,
        "jd_text": jd_text
    }
    response = requests.post(url, json=payload)
    return response.json()

def render_mock_interview_section(result):
    st.subheader("Mock Interview Practice")

    mock = result["mock_interview"]

    if "mock_evaluations" not in st.session_state:
        st.session_state["mock_evaluations"] = {}

    def render_question_block(q, q_key):
        st.markdown(f"**{q}**")
        answer = st.text_area(f"Your Answer", key=f"{q_key}_answer", height=100)

        if st.button(f"Evaluate", key=f"{q_key}_btn"):
            if not answer.strip():
                st.warning("Please type an answer first.")
            else:
                with st.spinner("Evaluating..."):
                    eval_result = call_evaluate_answer(
                        q, answer,
                        st.session_state.get("resume_text", ""),
                        st.session_state.get("jd_text", "")
                    )
                    st.session_state["mock_evaluations"][q_key] = eval_result
                    st.success("Evaluation complete!")

        if q_key in st.session_state["mock_evaluations"]:
            eval_result = st.session_state["mock_evaluations"][q_key]
            with st.expander("Feedback", expanded=True):
                st.markdown(f"**Score:** {eval_result['score']} / 10")
                st.markdown("**Strengths:**")
                st.write("\n".join(f"- {s}" for s in eval_result["strengths"]))
                st.markdown("**Weaknesses:**")
                st.write("\n".join(f"- {w}" for w in eval_result["weaknesses"]))
                st.markdown("**Suggestion:**")
                st.write(eval_result["suggestion"])
                st.markdown("**Ideal Answer:**")
                st.write(eval_result["ideal_answer"])

    st.markdown("### Technical Questions")
    for i, q in enumerate(mock["questions"]):
        render_question_block(q, f"tech_{i}")

    st.markdown("### Follow-up Questions")
    for i, q in enumerate(mock["follow_ups"]):
        render_question_block(q, f"follow_{i}")

    st.markdown("### Behavioral Questions")
    for i, q in enumerate(mock["behavioral"]):
        render_question_block(q, f"beh_{i}")