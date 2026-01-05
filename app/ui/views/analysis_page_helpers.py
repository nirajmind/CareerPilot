import requests
import os

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

def call_analysis_api(resume_text, jd_text):
    url = f"{BACKEND_URL}/analyze"
    payload = {"resume_text": resume_text, "jd_text": jd_text}
    response = requests.post(url, json=payload)

    # If backend returned non-JSON, handle gracefully 
    try: 
        data = response.json() 
    except Exception: 
        raise Exception(f"Backend returned non-JSON response: {response.text}")

    if response.status_code != 200:
        raise Exception(response.json().get("detail", "Unknown error"))

    return response.json()