import streamlit as st
import requests
import os

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

def render_forgot_password_page():
    st.title("Forgot Password")
    st.markdown("Enter your registered username and email to receive a password reset link.")

    with st.form("forgot_password_form"):
        username = st.text_input("Username")
        email = st.text_input("Email")
        submitted = st.form_submit_button("Send Reset Link")

        if submitted:
            if not username or not email:
                st.error("Please provide both username and email.")
                return

            try:
                response = requests.post(
                    f"{BACKEND_URL}/auth/request-reset",
                    json={"username": username, "email": email}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    st.success(data.get("message", "Reset link sent."))
                else:
                    try:
                        detail = response.json().get("detail", "Request failed")
                        st.error(detail)
                    except:
                        st.error(f"Request failed with status {response.status_code}")
            
            except requests.exceptions.ConnectionError:
                st.error("Could not connect to the server.")
            except Exception as e:
                st.error(f"An unexpected error occurred: {e}")

    if st.button("Back to Login"):
        st.session_state["auth_mode"] = "login"
        st.rerun()
