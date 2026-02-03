import streamlit as st
import requests
import os

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

def render_reset_password_page():
    st.title("Reset Password")
    
    # Retrieve query params
    # Streamlit query params access might vary slightly by version, assuming st.query_params (Newer) or st.experimental_get_query_params (Older)
    # Using the standard st.query_params dictionary-like object
    query_params = st.query_params
    
    # Safely get token and username. In some versions, values are lists/strings.
    # We'll handle both.
    token = query_params.get("token")
    username = query_params.get("username")

    if not token or not username:
        st.error("Invalid reset link. Missing token or username.")
        if st.button("Go to Login"):
            st.query_params.clear() 
            st.session_state["auth_mode"] = "login" 
            st.rerun()
        return

    st.write(f"Resetting password for user: **{username}**")

    with st.form("reset_password_form"):
        new_password = st.text_input("New Password", type="password")
        confirm_password = st.text_input("Confirm New Password", type="password")
        submitted = st.form_submit_button("Reset Password")

        if submitted:
            if new_password != confirm_password:
                st.error("Passwords do not match.")
            elif len(new_password) < 8:
                st.warning("Password must be at least 8 characters long.")
            else:
                try:
                    response = requests.post(
                        f"{BACKEND_URL}/auth/confirm-reset",
                        json={
                            "username": username,
                            "token": token,
                            "new_password": new_password
                        }
                    )

                    if response.status_code == 200:
                        st.success("Password reset successfully! Redirecting to login...")
                        st.query_params.clear() # Clear token from URL
                        st.session_state["auth_mode"] = "login"
                        # sleep briefly or just provide a button
                        st.button("Proceed to Login", on_click=st.rerun)
                    else:
                        try:
                            detail = response.json().get("detail", "Reset failed")
                            st.error(detail)
                        except:
                            st.error(f"Reset failed with status {response.status_code}")
                
                except requests.exceptions.ConnectionError:
                    st.error("Could not connect to the server.")

    if st.button("Back to Login (Cancel)"):
        st.query_params.clear()
        st.session_state["auth_mode"] = "login"
        st.rerun()
