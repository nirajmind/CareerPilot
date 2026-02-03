import streamlit as st
import requests
import os
from datetime import datetime
import dateutil.parser

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

def render_account_page():
    st.title("My Account")

    token = st.session_state.get("token")
    if not token:
        st.error("You must be logged in to view this page.")
        return

    try:
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(f"{BACKEND_URL}/auth/account-status", headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            
            # --- Header Info ---
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Username", data.get("username", "Unknown"))
            with col2:
                tier = data.get("tier", "free").upper()
                st.metric("Plan Tier", tier)
            with col3:
                status = "Active" if data.get("is_active") else "Inactive"
                if data.get("is_locked"):
                    status = "LOCKED"
                st.metric("Account Status", status, delta_color="off" if status=="Active" else "inverse")

            st.divider()

            # --- Quota Usage ---
            st.subheader("Daily Usage")
            
            quota = data.get("quota", {})
            used = quota.get("usage", 0)
            limit = quota.get("limit", 5)
            reset_at_str = quota.get("reset_at")
            
            # Calculate percentage
            percent = min(used / limit, 1.0) if limit > 0 else 1.0
            
            st.progress(percent)
            st.caption(f"{used} / {limit} analyses used today")
            
            if reset_at_str:
                try:
                    reset_dt = dateutil.parser.isoparse(reset_at_str)
                    st.info(f"Quota resets at: {reset_dt.strftime('%Y-%m-%d %H:%M:%S UTC')}")
                except:
                    pass

            # --- Upgrade Call to Action ---
            if data.get("tier") == "free":
                st.divider()
                st.warning("You are on the Free Tier.")
                st.markdown("Upgrade to **Premium** to get **100 analyses per day**!")
                
                if st.button("🚀 Upgrade to Premium"):
                    try:
                        checkout_res = requests.post(
                            f"{BACKEND_URL}/payments/checkout",
                            json={"username": data.get("username"), "email": data.get("email")},
                            headers=headers
                        )
                        if checkout_res.status_code == 200:
                            redirect_url = checkout_res.json().get("redirect_url")
                            if redirect_url:
                                st.link_button("Proceed to Payment", redirect_url)
                            else:
                                st.error("No redirect URL received.")
                        else:
                            st.error("Failed to initiate checkout.")
                    except requests.exceptions.ConnectionError:
                        st.error("Could not connect to payment service.")


            # --- Debug / Roles ---
            with st.expander("Advanced Details"):
                st.json(data)

        # Token might be expired or invalid
        elif response.status_code == 401:
            st.error("Session expired. Please logout and login again.")
        else:
            st.error(f"Failed to load account status: {response.status_code}")

    except requests.exceptions.ConnectionError:
        st.error("Could not connect to server.")
    except Exception as e:
        st.error(f"Error: {e}")
