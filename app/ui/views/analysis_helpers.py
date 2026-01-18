
import os
import requests
import streamlit as st


BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
DEBUG_EVALUATION = os.getenv("DEBUG_EVALUATION", "false").lower() == "true"

def save_analysis_to_db(analysis_result):
    url = f"{BACKEND_URL}/analysis_history/analysis/save"
    headers = {"Authorization": f"Bearer {st.session_state.get('token', '')}"}
    requests.post(url, json=analysis_result, headers=headers)

def load_analysis_history_from_db():
    url = f"{BACKEND_URL}/analysis_history/analysis/history"
    headers = {"Authorization": f"Bearer {st.session_state.get('token', '')}"}
    resp = requests.get(url, headers=headers)
    if resp.status_code == 200:
        data = resp.json()
        st.session_state["analysis_history"] = data
        return data
    return []

def init_analysis_history():
    if "analysis_history" not in st.session_state:
        load_analysis_history_from_db()
