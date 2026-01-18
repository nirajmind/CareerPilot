import json
import os
from datetime import datetime
import logging
import requests
import streamlit as st

logger = logging.getLogger(__name__)

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
DEBUG_EVALUATION = os.getenv("DEBUG_EVALUATION", "false").lower() == "true"


# ---------------------------------------------------------
# HISTORY INITIALIZATION
# ---------------------------------------------------------
def init_mock_history():
    if "mock_interview_history" not in st.session_state:
        st.session_state["mock_interview_history"] = load_history_from_db()


# ---------------------------------------------------------
# CALL EVALUATION API (STREAMING)
# ---------------------------------------------------------
def call_evaluate_api(question: str, user_answer: str, resume_text: str, jd_text: str) -> str:
    url = f"{BACKEND_URL}/stream/evaluate"
    headers = {"Authorization": f"Bearer {st.session_state.get('token', '')}"}
    payload = {
        "question": question,
        "user_answer": user_answer,
        "resume_text": resume_text,
        "jd_text": jd_text,
    }

    try:
        resp = requests.post(url, json=payload, stream=True, timeout=60, headers=headers)
    except requests.RequestException as e:
        raise RuntimeError(f"Network error calling evaluation API: {e}") from e

    if resp.status_code != 200:
        try:
            detail = resp.json()
            logger.error("Evaluation API error JSON: %s", json.dumps(detail, indent=2))
        except Exception:
            detail = resp.text
            logger.error("Evaluation API error text: %s", detail)
        raise RuntimeError(f"Evaluation API returned {resp.status_code}: {detail}")

    full_text = ""
    try:
        for chunk in resp.iter_content(chunk_size=None):
            if not chunk:
                continue
            decoded = chunk.decode("utf-8", errors="ignore")
            full_text += decoded
            if DEBUG_EVALUATION:
                logger.info("Streamed chunk: %s", decoded)
    except Exception as e:
        raise RuntimeError(f"Failed while reading streamed response: {e}") from e

    if not full_text.strip():
        raise RuntimeError("Evaluation API returned an empty response.")

    logger.info(f"Full streamed evaluation text for question '{question}': {full_text}")
    return full_text


# ---------------------------------------------------------
# PARSE EVALUATION (JSON FIRST, THEN FALLBACK)
# ---------------------------------------------------------
def parse_evaluation(text: str) -> dict:
    """
    1. Try JSON (Gemini now returns JSON)
    2. If JSON fails, fallback to legacy text parsing
    """

    # --- JSON PARSING ---
    try:
        data = json.loads(text)
        logger.info("Parsed JSON evaluation: %s", json.dumps(data, indent=2))

        return {
            "score": int(data.get("score", 0)),
            "strengths": data.get("strengths", []) or [],
            "weaknesses": data.get("weaknesses", []) or [],
            "suggestion": data.get("suggestion", "") or "",
            "ideal_answer": data.get("ideal_answer", "") or "",
        }
    except Exception as e:
        logger.warning("JSON parsing failed, falling back to text parser: %s", e)

    # ---------------------------------------------------------
    # FALLBACK: LEGACY TEXT PARSER (your original logic)
    # ---------------------------------------------------------
    score = None
    strengths, weaknesses = [], []
    suggestion_lines, ideal_answer_lines = [], []
    current_section = None

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        lower = line.lower()

        if lower.startswith("score"):
            try:
                after_colon = line.split(":", 1)[1]
                num_part = after_colon.split("/")[0].strip()
                score = int(num_part)
            except Exception:
                pass
            current_section = None

        elif lower.startswith("strengths"):
            current_section = "strengths"

        elif lower.startswith("weaknesses"):
            current_section = "weaknesses"

        elif lower.startswith("suggestion"):
            current_section = "suggestion"

        elif lower.startswith("ideal answer"):
            current_section = "ideal_answer"

        else:
            if current_section == "strengths":
                strengths.append(line.lstrip("-• ").strip())
            elif current_section == "weaknesses":
                weaknesses.append(line.lstrip("-• ").strip())
            elif current_section == "suggestion":
                suggestion_lines.append(line)
            elif current_section == "ideal_answer":
                ideal_answer_lines.append(line)

    suggestion = "\n".join(suggestion_lines).strip()
    ideal_answer = "\n".join(ideal_answer_lines).strip()

    return {
        "score": score if score is not None else 0,
        "strengths": strengths,
        "weaknesses": weaknesses,
        "suggestion": suggestion,
        "ideal_answer": ideal_answer,
    }


# ---------------------------------------------------------
# HISTORY STORAGE
# ---------------------------------------------------------
def add_to_history(question: str, eval_result: dict, user_answer: str):
    history = st.session_state.get("mock_interview_history", [])
    history.append(
        {
            "question": question,
            "user_answer": user_answer,
            "score": eval_result.get("score", 0),
            "strengths": eval_result.get("strengths", []),
            "weaknesses": eval_result.get("weaknesses", []),
            "suggestion": eval_result.get("suggestion", ""), 
            "ideal_answer": eval_result.get("ideal_answer", ""),
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
        }
    )
    st.session_state["mock_interview_history"] = history

def save_evaluation_to_db(question, eval_result, user_answer):
    url = f"{BACKEND_URL}/mock/save"
    headers = {"Authorization": f"Bearer {st.session_state.get('token', '')}"}

    payload = {
        "question": question,
        "user_answer": user_answer,
        "score": eval_result.get("score", 0),
        "strengths": eval_result.get("strengths", []),
        "weaknesses": eval_result.get("weaknesses", []),
        "suggestion": eval_result.get("suggestion", ""),
        "ideal_answer": eval_result.get("ideal_answer", ""),
    }

    requests.post(url, json=payload, headers=headers)

def load_history_from_db():
    url = f"{BACKEND_URL}/mock/history"
    headers = {"Authorization": f"Bearer {st.session_state.get('token', '')}"}

    resp = requests.get(url, headers=headers)
    if resp.status_code == 200:
        data = resp.json()
        st.session_state["mock_interview_history"] = data
        return data

    return []


# ---------------------------------------------------------
# HISTORY RETRIEVAL
# ---------------------------------------------------------
def get_question_history(question: str):
    history = st.session_state.get("mock_interview_history", [])
    if not history:
        history = load_history_from_db()
    return [h for h in history if h["question"] == question]
