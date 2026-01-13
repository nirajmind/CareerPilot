import streamlit as st
import requests
import os

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

def call_analysis_api(resume_text, jd_text):
    url = f"{BACKEND_URL}/analyze"
    payload = {"resume_text": resume_text, "jd_text": jd_text}
    headers = { "Authorization": f"Bearer {st.session_state.get('token', '')}" }
    response = requests.post(url, json=payload, headers=headers)
    # If backend returned non-JSON, handle gracefully 
    print("RAW RESPONSE:", response.text)
    try: 
        data = response.json() 
    except Exception: 
        raise Exception(f"Backend returned non-JSON response: {response.text}")

    if response.status_code != 200:
        detail = data.get("detail", "Unknown error") 
        raise Exception(f"Backend error: {detail}")

    return data