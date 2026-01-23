import streamlit as st
import requests
import os

from app.ui.views.mock_interview_helpers import load_history_from_db

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

def handle_api_error(response: requests.Response, action: str):
    """Provides detailed error messages from API responses."""
    try:
        detail = response.json().get("detail")
        st.error(f"{action} failed: {detail}")
    except requests.exceptions.JSONDecodeError:
        st.error(f"{action} failed. Could not decode server response. Status code: {response.status_code}")

def render_auth_page():
    st.title("Login / Register")

    if 'token' not in st.session_state:
        st.session_state.token = None
        st.session_state.user = None

    if st.session_state.token:
        st.success(f"Logged in as {st.session_state.user['username']}")
        if st.button("Logout"):
            st.session_state.token = None
            st.session_state.user = None
            st.rerun()
        return

    choice = st.selectbox("Choose action", ["Login", "Register"])

    with st.form("auth_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        email = st.text_input("Email") if choice == "Register" else None
        
        if choice == "Register":
            roles = st.multiselect("Roles", ["user", "admin"], default=["user"])

        submitted = st.form_submit_button("Submit")

        if submitted:
            if choice == "Login":
                login(username, password)
            elif choice == "Register":
                register(username, password, roles, email)

def login(username, password):
    try:
        # Step 1: Get the token
        token_response = requests.post(
            f"{BACKEND_URL}/auth/token",
            data={"username": username, "password": password}
        )
        if token_response.status_code != 200:
            handle_api_error(token_response, "Login")
            return

        token = token_response.json()["access_token"]
        st.session_state.token = token
        
        # Step 2: Get user details from a secure endpoint
        headers = {"Authorization": f"Bearer {token}"}
        user_response = requests.get(f"{BACKEND_URL}/users/me", headers=headers)

        if user_response.status_code == 200:
            st.session_state.user = user_response.json()
            load_history_from_db()
            st.rerun()
        else:
            # If fetching user details fails, the token might be invalid or there's a server issue.
            # Clear the token and show an error.
            st.session_state.token = None
            handle_api_error(user_response, "Could not fetch user details")

    except requests.exceptions.ConnectionError:
        st.error(f"Connection error: Could not connect to the API at {BACKEND_URL}.")

def register(username, password, roles, email):
    try:
        response = requests.post(
            f"{BACKEND_URL}/auth/register",
            json={"username": username, "password": password, "roles": roles, "email": email}
        )
        if response.status_code == 201:
            st.success("Registration successful! Please login.")
        else:
            handle_api_error(response, "Registration")
    except requests.exceptions.ConnectionError:
        st.error(f"Connection error: Could not connect to the API at {BACKEND_URL}.")