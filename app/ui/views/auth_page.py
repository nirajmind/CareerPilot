import streamlit as st
import requests
import os

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
        
        if choice == "Register":
            roles = st.multiselect("Roles", ["user", "admin"], default=["user"])

        submitted = st.form_submit_button("Submit")

        if submitted:
            if choice == "Login":
                login(username, password)
            elif choice == "Register":
                register(username, password, roles)

def login(username, password):
    try:
        response = requests.post(
            f"{BACKEND_URL}/auth/token",
            data={"username": username, "password": password}
        )
        if response.status_code == 200:
            token = response.json()["access_token"]
            st.session_state.token = token
            # In a real app, you would decode the token or have a /users/me endpoint
            # For simplicity, we'll just store the username. A better approach
            # is to decode the JWT to get user roles and other data.
            st.session_state.user = {"username": username, "roles": get_roles_from_token(token)}
            st.rerun()
        else:
            handle_api_error(response, "Login")
    except requests.exceptions.ConnectionError:
        st.error(f"Connection error: Could not connect to the API at {BACKEND_URL}.")

def register(username, password, roles):
    try:
        response = requests.post(
            f"{BACKEND_URL}/auth/register",
            json={"username": username, "password": password, "roles": roles}
        )
        if response.status_code == 201:
            st.success("Registration successful! Please login.")
        else:
            handle_api_error(response, "Registration")
    except requests.exceptions.ConnectionError:
        st.error(f"Connection error: Could not connect to the API at {BACKEND_URL}.")

def get_roles_from_token(token: str) -> list:
    """A simple (and insecure) way to decode the JWT payload."""
    import base64
    import json
    try:
        payload = token.split('.')[1]
        decoded_payload = base64.b64decode(payload + '==').decode('utf-8')
        return json.loads(decoded_payload).get("roles", [])
    except Exception:
        return []
