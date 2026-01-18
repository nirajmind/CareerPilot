import streamlit as st
from .mock_interview_helpers import (
    init_mock_history,
    call_evaluate_api,
    parse_evaluation,
    add_to_history,
    get_question_history,
    save_evaluation_to_db,
)

def render_mock_interview_page():
    st.title("Mock Interview Practice")

    init_mock_history()

    analysis = st.session_state.get("analysis_result")
    if not analysis:
        st.warning("No analysis found. Please run an analysis first from the Analysis page.")
        return

    # Load all questions
    questions = st.session_state.get("all_questions", [])
    if not questions:
        st.info("No mock interview questions were generated for this analysis.")
        return

    # Build question text list
    question_texts = [
        q if isinstance(q, str) else q.get("question", "")
        for q in questions
    ]

    # -----------------------------------------
    # 🔹 Resume mock interview (correct location)
    # -----------------------------------------
    if "resume_mock_question" in st.session_state:
        selected_question = st.session_state["resume_mock_question"]
        del st.session_state["resume_mock_question"]
    else:
        selected_idx = render_question_selector(question_texts)
        selected_question = question_texts[selected_idx]

    # Render the question block
    render_question_block(selected_question, analysis)

    if st.button("Back to Analysis"): 
        st.session_state["current_page"] = "Run Analysis" 
        st.rerun()


def render_question_selector(question_texts):
    st.subheader("Select a question")
    return st.selectbox(
        "Choose a question to practice:",
        options=list(range(len(question_texts))),
        format_func=lambda i: question_texts[i] if question_texts[i] else f"Question {i+1}",
    )


def render_question_block(selected_question: str, analysis: dict):
    st.markdown("### Question")
    st.markdown(f"> {selected_question}")

    st.markdown("### Your Answer")
    user_answer = st.text_area(
        "Type your answer here:",
        key=f"answer_{hash(selected_question)}",
        height=200,
        placeholder="Think out loud, explain your reasoning, and cover edge cases where relevant...",
    )

    resume_text = analysis.get("resume_text", "")
    jd_text = analysis.get("jd_text", "")

    if st.button("Evaluate Answer", type="primary"):
        if not user_answer.strip():
            st.error("Please enter an answer before requesting evaluation.")
            return

        with st.spinner("Evaluating your answer..."):
            try:
                eval_text = call_evaluate_api(
                    question=selected_question,
                    user_answer=user_answer,
                    resume_text=resume_text,
                    jd_text=jd_text,
                )
            except Exception as e:
                st.error(f"Evaluation failed: {e}")
                return

        try:
            eval_result = parse_evaluation(eval_text)
        except Exception as e:
            st.error(f"Failed to parse evaluation response: {e}")
            st.text_area("Raw evaluation response:", eval_text, height=200)
            return

        add_to_history(selected_question, eval_result, user_answer) 
        save_evaluation_to_db(selected_question, eval_result, user_answer)
        render_evaluation_result(eval_result)
        render_question_analytics(selected_question)


def render_evaluation_result(result: dict):
    st.markdown("### Evaluation Result")

    col1, col2 = st.columns([1, 3])
    with col1:
        st.metric("Score", f"{result.get('score', 0)}/10")
    with col2:
        if result.get("suggestion"):
            st.markdown("**Suggestion:**")
            st.write(result["suggestion"])

    st.markdown("---")

    if result.get("strengths"):
        st.markdown("#### Strengths")
        for s in result["strengths"]:
            st.markdown(f"- {s}")

    if result.get("weaknesses"):
        st.markdown("#### Weaknesses")
        for w in result["weaknesses"]:
            st.markdown(f"- {w}")

    if result.get("ideal_answer"):
        st.markdown("#### Ideal Answer")
        st.text_area(
            "Model's ideal answer:",
            result["ideal_answer"],
            height=200,
        )


def render_question_analytics(question: str):
    st.markdown("### Question Analytics")

    q_history = get_question_history(question)
    if not q_history:
        st.info("No analytics available yet for this question.")
        return

    scores = [h["score"] for h in q_history]

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Attempts", len(q_history))
    with col2:
        st.metric("Average Score", f"{sum(scores)/len(scores):.1f}/10")
    with col3:
        st.metric("Best Score", f"{max(scores)}/10")
    with col4:
        st.metric("Last Score", f"{scores[-1]}/10")

    st.markdown("#### Attempt History")
    for h in reversed(q_history):
        st.markdown(f"- **{h['timestamp']}** — Score: {h['score']}/10")
