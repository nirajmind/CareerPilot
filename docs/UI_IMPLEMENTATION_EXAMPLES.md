
# CareerPilot UI Implementation Examples

This file contains ready-to-use Streamlit code for the new features.

---

## 1. Forgot Password Page

**File:** `app/ui/pages/forgot_password.py`

```python
import streamlit as st
import requests
from app.ui.utils import get_api_url, get_token

st.set_page_config(
    page_title="Forgot Password - CareerPilot",
    page_icon="🔐",
    layout="centered"
)

st.title("Reset Password")
st.write("Enter your username and email to receive a password reset link.")

with st.form("reset_request_form"):
    username = st.text_input(
        "Username",
        placeholder="your_username"
    )
    email = st.text_input(
        "Email Address",
        placeholder="your.email@example.com"
    )
    submitted = st.form_submit_button("Send Reset Link", use_container_width=True)

    if submitted:
        if not username or not email:
            st.error("Please fill in all fields")
        else:
            with st.spinner("Sending reset link..."):
                try:
                    response = requests.post(
                        f"{get_api_url()}/auth/request-reset",
                        json={"username": username, "email": email},
                        timeout=10
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        st.success(data.get("message", "Reset link sent!"))
                        st.info("Check your email for the reset link. It will expire in 24 hours.")
                    else:
                        st.error(response.json().get("detail", "Failed to send reset link"))
                except requests.exceptions.RequestException as e:
                    st.error(f"Connection error: {str(e)}")

st.divider()
st.write("Remember your password? [Back to Login](/?)")
```

---

## 2. Reset Password Confirmation Page

**File:** `app/ui/pages/reset_password_confirm.py`

```python
import streamlit as st
import requests
from app.ui.utils import get_api_url

st.set_page_config(
    page_title="Reset Password - CareerPilot",
    page_icon="🔐",
    layout="centered"
)

# Extract query parameters
query_params = st.query_params
token = query_params.get("token", [None])[0]
username = query_params.get("username", [None])[0]

if not token or not username:
    st.error("❌ Invalid reset link. Please request a new password reset.")
    st.stop()

st.title("Reset Your Password")
st.write(f"Resetting password for: **{username}**")

with st.form("reset_confirm_form"):
    new_password = st.text_input(
        "New Password",
        type="password",
        placeholder="At least 8 characters",
        help="Use a strong password with uppercase, lowercase, numbers, and symbols"
    )
    
    confirm_password = st.text_input(
        "Confirm Password",
        type="password",
        placeholder="Re-enter your password"
    )
    
    submitted = st.form_submit_button("Reset Password", use_container_width=True)

    if submitted:
        # Validation
        if not new_password or not confirm_password:
            st.error("Please fill in all fields")
        elif new_password != confirm_password:
            st.error("❌ Passwords do not match")
        elif len(new_password) < 8:
            st.error("❌ Password must be at least 8 characters long")
        else:
            with st.spinner("Resetting password..."):
                try:
                    response = requests.post(
                        f"{get_api_url()}/auth/confirm-reset",
                        json={
                            "username": username,
                            "token": token,
                            "new_password": new_password
                        },
                        timeout=10
                    )
                    
                    if response.status_code == 200:
                        st.success("✅ Password reset successfully!")
                        st.info("Redirecting to login...")
                        import time
                        time.sleep(2)
                        st.switch_page("pages/login.py")
                    else:
                        detail = response.json().get("detail", "Reset failed")
                        st.error(f"❌ {detail}")
                except requests.exceptions.RequestException as e:
                    st.error(f"Connection error: {str(e)}")
```

---

## 3. Account Status Dashboard

**File:** `app/ui/pages/account_status.py`

```python
import streamlit as st
import requests
from datetime import datetime
from app.ui.utils import get_api_url, get_token

st.set_page_config(
    page_title="Account Status - CareerPilot",
    page_icon="👤",
    layout="wide"
)

# Check authentication
token = get_token()
if not token:
    st.error("Please log in first")
    st.switch_page("pages/login.py")
    st.stop()

st.title("Account Status")

# Fetch account information
with st.spinner("Loading account information..."):
    try:
        response = requests.get(
            f"{get_api_url()}/auth/account-status",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10
        )
        
        if response.status_code != 200:
            st.error("Failed to load account information")
            st.stop()
        
        account = response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Connection error: {str(e)}")
        st.stop()

# Display account overview
col1, col2, col3, col4 = st.columns(4)

with col1:
    status_emoji = "🟢" if account['is_active'] else "🔴"
    st.metric("Account Status", f"{status_emoji} {'Active' if account['is_active'] else 'Inactive'}")

with col2:
    tier_emoji = "⭐" if account['tier'] == 'premium' else "🆓"
    st.metric("Subscription", f"{tier_emoji} {account['tier'].title()}")

with col3:
    lock_emoji = "🔒" if account['is_locked'] else "🔓"
    st.metric("Account Lock", lock_emoji)

with col4:
    st.metric("Roles", ", ".join(account['roles']))

st.divider()

# Daily Usage Quota Section
st.subheader("📊 Daily Usage Quota")

quota = account['quota']
usage_percent = quota['usage'] / quota['limit']

col1, col2 = st.columns([3, 1])

with col1:
    st.progress(
        min(usage_percent, 1.0),
        text=f"{quota['usage']}/{quota['limit']} analyses used"
    )

with col2:
    remaining_color = "🟢" if quota['remaining'] > 0 else "🔴"
    st.metric("Remaining", f"{remaining_color} {quota['remaining']}")

# Reset time
reset_time = datetime.fromisoformat(quota['reset_at'].replace('Z', '+00:00'))
time_until_reset = reset_time - datetime.now(reset_time.tzinfo)
hours_remaining = int(time_until_reset.total_seconds() / 3600)
minutes_remaining = int((time_until_reset.total_seconds() % 3600) / 60)

st.caption(f"⏰ Resets in {hours_remaining}h {minutes_remaining}m")

# Upgrade prompt for free users
if account['tier'] == 'free':
    st.warning(
        f"📈 You've used {quota['usage']}/{quota['limit']} analyses today. "
        f"Upgrade to Premium for 100 analyses per day!"
    )
    
    if st.button("🚀 Upgrade to Premium", use_container_width=True, type="primary"):
        # Redirect to checkout
        st.info("Redirecting to upgrade page...")
        # Store in session for checkout page
        st.session_state['checkout_ready'] = True
        st.switch_page("pages/upgrade_premium.py")

st.divider()

# Account Details Section
st.subheader("👤 Account Details")

col1, col2 = st.columns(2)

with col1:
    st.write(f"**Username:** `{account['username']}`")
    st.write(f"**Email:** {account['email']}")

with col2:
    st.write(f"**Account Status:** {'Active' if account['is_active'] else 'Inactive'}")
    st.write(f"**Subscription Tier:** {account['tier'].title()}")

st.divider()

# Security Section
st.subheader("🔐 Security")

col1, col2 = st.columns(2)

with col1:
    if st.button("🔄 Change Password", use_container_width=True):
        st.switch_page("pages/forgot_password.py")

with col2:
    if st.button("🚪 Logout", use_container_width=True):
        st.session_state.clear()
        st.switch_page("pages/login.py")

# Lock warning
if account['is_locked']:
    st.error(
        "⚠️ **Your account is locked due to multiple failed login attempts.** "
        "It will be automatically unlocked in 24 hours. "
        "For immediate help, contact support."
    )
```

---

## 4. Premium Upgrade Page

**File:** `app/ui/pages/upgrade_premium.py`

```python
import streamlit as st
import requests
from app.ui.utils import get_api_url, get_token

st.set_page_config(
    page_title="Upgrade to Premium - CareerPilot",
    page_icon="⭐",
    layout="centered"
)

token = get_token()
if not token:
    st.error("Please log in first")
    st.switch_page("pages/login.py")
    st.stop()

# Get user info from token
import jwt
decoded = jwt.decode(token, options={"verify_signature": False})
username = decoded.get("sub")
email = decoded.get("email")

st.title("Upgrade to Premium")

# Pricing comparison
st.subheader("Choose Your Plan")

col1, col2 = st.columns(2)

with col1:
    st.markdown("""
    ### 🆓 Free Plan
    - **5 analyses/day**
    - Basic features
    - Community support
    
    **$0/month**
    """)

with col2:
    st.markdown("""
    ### ⭐ Premium Plan
    - **100 analyses/day**
    - All features
    - Priority support
    - Advanced analytics
    
    **$9.99/month**
    """)

st.divider()

st.subheader("Ready to unlock premium?")

if st.button("Proceed to Checkout →", use_container_width=True, type="primary"):
    with st.spinner("Creating checkout session..."):
        try:
            response = requests.post(
                f"{get_api_url()}/payments/checkout",
                json={
                    "username": username,
                    "email": email
                },
                headers={"Authorization": f"Bearer {token}"},
                timeout=10
            )
            
            if response.status_code == 200:
                session_data = response.json()
                st.success("✅ Checkout session created!")
                st.markdown(
                    f"[🛒 Complete your purchase →]({session_data['redirect_url']})",
                    unsafe_allow_html=False
                )
                st.info("You will be redirected to Stripe to complete the payment securely.")
            else:
                error = response.json().get("detail", "Failed to create checkout session")
                st.error(f"❌ {error}")
        except requests.exceptions.RequestException as e:
            st.error(f"Connection error: {str(e)}")

st.divider()

col1, col2 = st.columns(2)

with col1:
    if st.button("← Back to Account", use_container_width=True):
        st.switch_page("pages/account_status.py")

with col2:
    if st.button("Skip for Now", use_container_width=True):
        st.switch_page("pages/analysis.py")

# FAQ
st.subheader("❓ Frequently Asked Questions")

with st.expander("When does my subscription start?"):
    st.write("Your subscription starts immediately after successful payment.")

with st.expander("Can I cancel anytime?"):
    st.write("Yes, you can cancel your subscription anytime from your account settings.")

with st.expander("What payment methods do you accept?"):
    st.write("We accept all major credit cards via Stripe: Visa, Mastercard, American Express, and more.")

with st.expander("Do you offer refunds?"):
    st.write("We offer a 7-day money-back guarantee for new subscriptions. Contact support for details.")

with st.expander("Why do I need analyses?"):
    st.write(
        "Each time you analyze a resume against a job description, we use our AI models "
        "to generate detailed insights. Free tier users get 5 per day, premium users get 100."
    )
```

---

## 5. Integration into Existing Analysis Page

**Update:** `app/ui/pages/analysis.py` (add this section near the top after login check)

```python
# Add this after your existing session_state check for authentication

# NEW: Fetch and display quota/tier info
col1, col2, col3 = st.columns(3)

with col1:
    st.caption("💾 Storage")

with col2:
    st.caption("📊 Usage Quota")

with col3:
    st.caption("💳 Subscription")

col1, col2, col3 = st.columns(3)

with col2:
    # Get account status
    try:
        response = requests.get(
            f"{get_api_url()}/auth/account-status",
            headers={"Authorization": f"Bearer {token}"},
            timeout=5
        )
        if response.status_code == 200:
            account = response.json()
            quota = account['quota']
            
            # Show quota progress
            usage_percent = quota['usage'] / quota['limit']
            if usage_percent >= 0.9:
                st.error(f"{quota['usage']}/{quota['limit']}")
            elif usage_percent >= 0.7:
                st.warning(f"{quota['usage']}/{quota['limit']}")
            else:
                st.success(f"{quota['usage']}/{quota['limit']}")
    except:
        pass

with col3:
    # Show upgrade button for free users
    try:
        response = requests.get(
            f"{get_api_url()}/auth/account-status",
            headers={"Authorization": f"Bearer {token}"},
            timeout=5
        )
        if response.status_code == 200:
            account = response.json()
            if account['tier'] == 'free':
                if st.button("🚀 Upgrade", use_container_width=True):
                    st.switch_page("pages/upgrade_premium.py")
            else:
                st.success("⭐ Premium Active")
    except:
        pass

st.divider()

# REST OF YOUR ANALYSIS PAGE CODE...
```

---

## 6. Helper Utility Functions

**File:** `app/ui/utils.py` (add if not exists)

```python
import streamlit as st
import os

def get_api_url() -> str:
    """Get API base URL from environment or session state."""
    return st.session_state.get(
        "api_url",
        os.getenv("BACKEND_URL", "http://api:8585")
    )

def get_token() -> str:
    """Get JWT token from session state."""
    return st.session_state.get("token")

def set_token(token: str):
    """Store JWT token in session state."""
    st.session_state["token"] = token

def clear_session():
    """Clear all session data on logout."""
    st.session_state.clear()

def is_authenticated() -> bool:
    """Check if user is authenticated."""
    return "token" in st.session_state and st.session_state["token"] is not None
```

---

## 7. Update Navigation (sidebar)

**Update:** Main `app/ui/main.py` or `app/ui/components/sidebar.py`

```python
import streamlit as st
from app.ui.utils import is_authenticated, get_token

# Sidebar Navigation
st.sidebar.title("CareerPilot")

if not is_authenticated():
    st.sidebar.write("👤 Not logged in")
    if st.sidebar.button("🔐 Login", use_container_width=True):
        st.switch_page("pages/login.py")
else:
    # Decode token to get username (for greeting)
    import jwt
    token = get_token()
    try:
        decoded = jwt.decode(token, options={"verify_signature": False})
        username = decoded.get("sub", "User")
        st.sidebar.write(f"👤 {username}")
    except:
        pass
    
    st.sidebar.divider()
    
    # Main Navigation
    page = st.sidebar.radio(
        "Navigate",
        [
            "📊 Analysis",
            "👤 Account Status",
            "💳 Upgrade Premium",
            "🔐 Change Password",
            "🚪 Logout"
        ],
        label_visibility="collapsed"
    )
    
    if page == "📊 Analysis":
        st.switch_page("pages/analysis.py")
    elif page == "👤 Account Status":
        st.switch_page("pages/account_status.py")
    elif page == "💳 Upgrade Premium":
        st.switch_page("pages/upgrade_premium.py")
    elif page == "🔐 Change Password":
        st.switch_page("pages/forgot_password.py")
    elif page == "🚪 Logout":
        st.session_state.clear()
        st.switch_page("pages/login.py")
```

---

## Installation & Testing

### 1. Install Dependencies (if needed)

```bash
pip install streamlit requests pyjwt
```

### 2. Update `requirements.txt`

Already included: `streamlit`, `requests`, `python-jose[cryptography]`

### 3. Set Environment Variables

```bash
export BACKEND_URL=http://localhost:8585  # For local testing
# or use default (http://api:8585 for Docker)
```

### 4. Run Streamlit

```bash
streamlit run app/ui/main.py
```

### 5. Test Flow

1. **Forgot Password**: Go to forgot_password.py → Enter username/email → Check console for email
2. **Reset Password**: Click reset link → Enter new password → Verify login with new password
3. **Account Status**: View quota, tier, lock status
4. **Upgrade Premium**: Click upgrade → Stripe checkout (test mode)

---

## Common Issues & Solutions

### Issue: "Connection refused" to API

**Solution:** Ensure API is running on correct port (8585 locally, 8585 in Docker)

### Issue: "Invalid token"

**Solution:** Token might be expired. Log out and log back in.

### Issue: Email not sending

**Solution:** Check Gmail app password in `.env`. Use app-specific password, not Gmail password.

### Issue: Stripe redirect not working

**Solution:** Use ngrok or expose localhost with: `ngrok http 8585`

---

## Notes

- All Streamlit pages should be in `app/ui/pages/` directory
- Each page should start with `st.set_page_config()`
- Use `st.switch_page()` for navigation between pages
- Store user token in `st.session_state["token"]`
- Use helper functions from `app/ui/utils.py`
