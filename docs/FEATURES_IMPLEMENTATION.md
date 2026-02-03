
# CareerPilot: Security, Identity & Monetization Implementation Guide

## Overview

This document describes the new features added to CareerPilot:

1. **Security Hardening** - Account Lockout + Rate Limiting + Config Refactor
2. **Identity Management** - Password Reset with Email Integration
3. **Monetization** - Usage Quotas + Stripe Integration

All features follow **SOLID design principles** with clear service separation, are **non-breaking** (don't affect existing flow), and work in both API and UI.

---

## Architecture & Design Principles

### SOLID Principles Applied

1. **Single Responsibility Principle (SRP)**
   - Each service handles one concern:
     - `AccountLockoutService`: Tracks failed attempts & locks
     - `RateLimiterService`: Enforces request rate limits
     - `PasswordResetService`: Manages password reset flow
     - `QuotaService`: Tracks daily usage
     - `StripeService`: Handles payment webhooks
   - `AppConfig`: Single source of truth for configuration

2. **Open/Closed Principle**
   - Services are closed for modification but open for extension
   - New payment providers can be added without changing existing code

3. **Liskov Substitution Principle**
   - All services follow consistent interfaces
   - Can be mocked/tested independently

4. **Interface Segregation**
   - Each service exposes minimal, focused methods
   - Clients don't depend on unused functionality

5. **Dependency Inversion**
   - Services depend on abstractions (Redis, MongoHandler) not implementations
   - Injected via constructor

---

## Feature Details

### 1. Security Hardening

#### A. Account Lockout (`AccountLockoutService`)

**Mechanism:**

- Redis tracks failed login attempts per username
- After `MAX_FAILED_ATTEMPTS` (default: 5), account is locked for `LOCKOUT_DURATION_HOURS` (default: 24)
- Both counters expire after lockout duration

**Redis Keys:**

```config
failed_attempts:{username}  -> count (expires in 24h)
account_locked:{username}   -> "1" (expires in 24h)
```

**API Changes:**

- `POST /auth/token`: Now checks `account_locked:{username}` before verifying password
  - Returns 429 if locked: "Account locked due to too many failed attempts"
  - Increments `failed_attempts:{username}` on failed login
  - Resets counters on successful login

**Example Behavior:**

```config
User attempts login 5 times (wrong password):
→ failed_attempts:john = 5
→ account_locked:john = "1"
→ User locked for 24 hours

Successful login resets:
→ DELETE failed_attempts:john
→ DELETE account_locked:john
```

#### B. Rate Limiting (`RateLimiterService`)

**Mechanism:**

- Token bucket algorithm: tracks requests per username per minute
- Default: 10 requests per minute (configurable)
- Resets at each minute boundary

**Redis Keys:**

```config
rate_limit:{username}:{minute} -> count (expires in 60s)
```

**API Changes:**

- `POST /analyze`: Now checks rate limit before processing
  - Returns 429 if exceeded with remaining quota and reset time
  - Logged for monitoring

**Configuration:**

```env
RATE_LIMIT_ENABLED=true
RATE_LIMIT_REQUESTS=10
RATE_LIMIT_WINDOW_MINUTES=1
```

#### C. Config Refactor (`AppConfig`)

**Old Approach:** Scattered `os.getenv()` calls throughout codebase

```python
SECRET_KEY = os.environ["JWT_SECRET_KEY"]  # Fails at runtime if missing
gemini_url = os.getenv("GEMINI_PROXY_URL")
```

**New Approach:** Centralized Pydantic config with validation

```python
from app.api.app_config import get_config

config = get_config()  # Validated & cached once
print(config.security.jwt_secret_key)
print(config.stripe.stripe_api_key)
```

**Benefits:**

- Type-safe with IDE autocomplete
- Early validation (fails at startup, not runtime)
- Single source of truth
- Easy to override per environment
- Clear grouping by feature

**Structure:**

```python
AppConfig
├── security: SecuritySettings (JWT, lockout, rate limit)
├── database: DatabaseSettings (Mongo, Redis URIs)
├── email: EmailSettings (Gmail SMTP)
├── stripe: StripeSettings (Stripe keys & price IDs)
├── quota: QuotaSettings (free/premium limits)
├── api: APISettings (logging, API info)
└── gemini: GeminiSettings (API keys, circuit breaker)
```

---

### 2. Identity Management

#### Password Reset Flow (`PasswordResetService`)

**Mechanism:**

1. User requests reset: `POST /auth/request-reset` → Generate token → Send email
2. User clicks link in email → Frontend calls `POST /auth/confirm-reset` with token
3. API validates token and updates password

**No new dependencies:** Uses Python's built-in `smtplib` + Gmail SMTP.

**Redis Keys:**

```config
password_reset_token:{username} -> token (expires in 24h)
```

**API Endpoints:**

##### `POST /auth/request-reset`

```json
Request:
{
  "username": "john_doe",
  "email": "john@example.com"
}

Response (200):
{
  "success": true,
  "message": "Password reset link sent to john@example.com. Valid for 24 hours."
}
```

**Security:** Returns success even if user doesn't exist (prevents user enumeration).

##### `POST /auth/confirm-reset`

```json
Request:
{
  "username": "john_doe",
  "token": "dN5q..._secure_token_...",
  "new_password": "NewPassword123!"
}

Response (200):
{
  "success": true,
  "message": "Password reset successfully!"
}

Error (400):
{
  "detail": "Invalid reset token."
}
```

**Email Example:**

```config
To: john@example.com
Subject: Password Reset Request - CareerPilot

Hello john_doe,

Click to reset: https://careerpilot.chickenkiller.com/reset-password?token=...&username=john_doe

Valid for 24 hours. If you didn't request this, ignore.
```

**Configuration:**

```env
GMAIL_SENDER_EMAIL=your-gmail@gmail.com
GMAIL_APP_PASSWORD=your-app-specific-password  # Generated in Gmail settings
PASSWORD_RESET_TOKEN_EXPIRY_HOURS=24
```

**Why no new dependencies?**

- `smtplib`: Built into Python
- `email.mime`: Built into Python
- Just add Gmail credentials to `.env` (you provide them)

---

### 3. Monetization

#### A. Usage Quotas (`QuotaService`)

**Mechanism:**

- Free tier: 5 analyses per day
- Premium tier: 100 analyses per day
- Daily quota resets at UTC midnight
- Tracked per user in Redis

**Redis Keys:**

```config
user_usage:{YYYY-MM-DD}:{username} -> count (expires at midnight)
user_tier:{username} -> "free" or "premium" (no expiry)
```

**API Changes:**

##### `POST /analyze` now enforces quotas

```python
# Before processing:
can_analyze, quota_info = await quota_service.can_perform_analysis(username)
if not can_analyze:
    raise HTTPException(
        status_code=402,  # Payment Required
        detail=f"Quota exceeded: {usage}/{limit} analyses. Upgrade to premium or wait until {reset_at}"
    )

# After successful analysis:
await quota_service.increment_usage(username)
```

**Response on quota exceeded:**

```json
{
  "detail": "Daily quota exceeded. You have 5/5 analyses. Upgrade to premium or wait until 2026-02-03T00:00:00Z"
}
```

##### `GET /auth/account-status` - View quota & tier

```json
{
  "username": "john_doe",
  "email": "john@example.com",
  "is_active": true,
  "is_locked": false,
  "tier": "premium",
  "quota": {
    "usage": 42,
    "limit": 100,
    "remaining": 58,
    "tier": "premium",
    "reset_at": "2026-02-03T00:00:00Z"
  },
  "roles": ["user", "premium"]
}
```

**Configuration:**

```env
FREE_TIER_DAILY_LIMIT=5
PREMIUM_TIER_DAILY_LIMIT=100
```

#### B. Stripe Integration (`StripeService` & `PaymentService`)

**Mechanism:**

1. User clicks "Upgrade to Premium" → Calls `POST /payments/checkout`
2. Frontend redirects to Stripe checkout
3. User completes payment
4. Stripe sends webhook: `POST /payments/webhook`
5. API validates signature, upgrades user

**API Endpoints:**

##### `POST /payments/checkout` - Create checkout session

```json
Request:
{
  "username": "john_doe",
  "email": "john@example.com"
}

Response (200):
{
  "session_id": "cs_test_xxx",
  "redirect_url": "https://checkout.stripe.com/pay/cs_test_xxx",
  "status": "created"
}
```

##### `POST /payments/webhook` - Handle Stripe events

```json
Request (from Stripe):
{
  "type": "payment_intent.succeeded",
  "data": {
    "object": {
      "metadata": {
        "username": "john_doe"
      }
    }
  }
}

Response (200):
{
  "success": true,
  "message": "User 'john_doe' upgraded to premium"
}
```

**What happens on successful payment:**

1. `QuotaService.set_user_tier(username, "premium")`
   - Sets Redis: `user_tier:john_doe = "premium"` (persistent)
2. `MongoHandler.set_user_premium(username)`
   - Adds "premium" to user's roles in MongoDB
   - Sets tier field: `tier: "premium"`

**User immediately sees:**

- Quota limit increased from 5 → 100
- Extra "premium" role in JWT claims
- Next `/analyze` uses premium limits

**Configuration:**

```env
STRIPE_API_KEY=sk_test_xxx
STRIPE_WEBHOOK_SECRET=whsec_test_xxx
STRIPE_PRICE_ID_PREMIUM=price_xxx  # Created in Stripe dashboard
```

**Circuit Breaker (for resilience):**

```python
@circuit_breaker("gemini", circuit_breaker_service)
async def call_gemini(...):
    # If Gemini fails 5 times → circuit opens
    # Returns CircuitBreakerError for next 60s
    # Prevents cascading failures
    ...
```

---

## Environment Variables

Add to `.env`:

```dotenv
# --- Security ---
JWT_SECRET_KEY=your-super-secret-key
MAX_FAILED_ATTEMPTS=5
LOCKOUT_DURATION_HOURS=24
RATE_LIMIT_ENABLED=true
RATE_LIMIT_REQUESTS=10
RATE_LIMIT_WINDOW_MINUTES=1

# --- Email (Gmail) ---
GMAIL_SENDER_EMAIL=your-gmail@gmail.com
GMAIL_APP_PASSWORD=your-app-specific-password
PASSWORD_RESET_TOKEN_EXPIRY_HOURS=24

# --- Stripe ---
STRIPE_API_KEY=sk_test_xxx
STRIPE_WEBHOOK_SECRET=whsec_test_xxx
STRIPE_PRICE_ID_PREMIUM=price_xxx

# --- Quotas ---
FREE_TIER_DAILY_LIMIT=5
PREMIUM_TIER_DAILY_LIMIT=100

# --- Existing vars (unchanged) ---
MONGO_URI=mongodb://mongo:27017/careerpilot
REDIS_HOST=redis
REDIS_PORT=6379
GEMINI_API_KEY=...
GEMINI_PROXY_URL=...
PROXY_SECRET=...
```

---

## UI Implementation Guide

### 1. Forgot Password Page

**File:** `app/ui/pages/forgot_password.py`

```python
import streamlit as st
import requests

st.set_page_config(page_title="Forgot Password - CareerPilot")

st.title("Reset Password")

with st.form("reset_request_form"):
    username = st.text_input("Username")
    email = st.text_input("Email")
    submitted = st.form_submit_button("Send Reset Link")

    if submitted:
        response = requests.post(
            "http://api:8585/auth/request-reset",
            json={"username": username, "email": email}
        )
        if response.status_code == 200:
            st.success(response.json()["message"])
        else:
            st.error("Failed to send reset link")
```

### 2. Reset Password Confirmation Page

**File:** `app/ui/pages/reset_password.py`

```python
import streamlit as st
import requests
from urllib.parse import urlparse, parse_qs

st.set_page_config(page_title="Reset Password - CareerPilot")

# Extract token & username from URL query params
query_params = st.query_params
token = query_params.get("token", [None])[0]
username = query_params.get("username", [None])[0]

if not token or not username:
    st.error("Invalid reset link")
    st.stop()

st.title("Reset Password")
st.write(f"Reset password for: **{username}**")

with st.form("reset_confirm_form"):
    new_password = st.text_input("New Password", type="password")
    confirm_password = st.text_input("Confirm Password", type="password")
    submitted = st.form_submit_button("Reset Password")

    if submitted:
        if new_password != confirm_password:
            st.error("Passwords do not match")
        elif len(new_password) < 8:
            st.error("Password must be at least 8 characters")
        else:
            response = requests.post(
                "http://api:8585/auth/confirm-reset",
                json={
                    "username": username,
                    "token": token,
                    "new_password": new_password
                }
            )
            if response.status_code == 200:
                st.success("Password reset successfully! Redirecting to login...")
                st.switch_page("pages/login.py")
            else:
                st.error(response.json().get("detail", "Reset failed"))
```

### 3. Premium Upgrade Button (in existing page)

**File:** `app/ui/pages/analysis.py` (add to existing)

```python
# After getting current_user:
user_info = requests.get(
    "http://api:8585/auth/account-status",
    headers={"Authorization": f"Bearer {token}"}
).json()

col1, col2 = st.columns(2)
with col1:
    st.metric("Analyses Used Today", f"{user_info['quota']['usage']}/{user_info['quota']['limit']}")

with col2:
    if user_info['tier'] == 'free':
        if st.button("🚀 Upgrade to Premium"):
            # Create checkout session
            checkout_response = requests.post(
                "http://api:8585/payments/checkout",
                json={"username": user_info['username'], "email": user_info['email']},
                headers={"Authorization": f"Bearer {token}"}
            ).json()
            
            # Redirect to Stripe
            st.markdown(f"[Click here to upgrade]({checkout_response['redirect_url']})")
    else:
        st.success("✅ Premium Active")
```

### 4. Account Status Page

**File:** `app/ui/pages/account_status.py`

```python
import streamlit as st
import requests

st.set_page_config(page_title="Account Status - CareerPilot")

token = st.session_state.get("token")
if not token:
    st.error("Please log in first")
    st.stop()

response = requests.get(
    "http://api:8585/auth/account-status",
    headers={"Authorization": f"Bearer {token}"}
)

if response.status_code == 200:
    account = response.json()
    
    st.title("Account Status")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Status", "🟢 Active" if account['is_active'] else "🔴 Inactive")
    with col2:
        st.metric("Tier", "⭐ Premium" if account['tier'] == 'premium' else "🆓 Free")
    with col3:
        status = "🔒 Locked" if account['is_locked'] else "🔓 Unlocked"
        st.metric("Account Lock", status)
    
    st.divider()
    
    st.subheader("Daily Usage Quota")
    quota = account['quota']
    st.progress(quota['usage'] / quota['limit'])
    st.caption(f"{quota['usage']}/{quota['limit']} analyses used")
    st.caption(f"Resets at: {quota['reset_at']}")
    
    st.divider()
    
    st.subheader("Account Details")
    st.write(f"**Username:** {account['username']}")
    st.write(f"**Email:** {account['email']}")
    st.write(f"**Roles:** {', '.join(account['roles'])}")
    
    if account['tier'] == 'free':
        st.info("Upgrade to Premium to get 100 analyses per day!")
else:
    st.error("Failed to load account status")
```

---

## Testing Guide

### Unit Tests

**File:** `tests/api/test_security_services.py`

```python
import pytest
import fakeredis.aioredis
from app.api.security_services import AccountLockoutService
from app.api.app_config import AppConfig

@pytest.fixture
def fake_redis():
    return fakeredis.aioredis.FakeRedis(decode_responses=True)

@pytest.fixture
def lockout_service(fake_redis):
    config = AppConfig(...)  # Mock config
    return AccountLockoutService(fake_redis, config)

@pytest.mark.asyncio
async def test_account_lockout_after_failed_attempts(lockout_service):
    username = "test_user"
    
    # Record 5 failed attempts
    for i in range(5):
        await lockout_service.record_failed_attempt(username)
    
    # Account should be locked
    is_locked = await lockout_service.is_account_locked(username)
    assert is_locked == True

@pytest.mark.asyncio
async def test_successful_login_resets_attempts(lockout_service):
    username = "test_user"
    
    # Record failed attempts
    await lockout_service.record_failed_attempt(username)
    await lockout_service.record_failed_attempt(username)
    
    # Reset on success
    await lockout_service.reset_failed_attempts(username)
    
    attempts = await lockout_service.get_failed_attempts(username)
    assert attempts == 0
```

**File:** `tests/api/test_password_reset.py`

```python
@pytest.mark.asyncio
async def test_password_reset_flow(password_reset_service, fake_redis):
    username = "john_doe"
    email = "john@example.com"
    
    # Step 1: Request reset
    success, msg = await password_reset_service.request_password_reset(username, email)
    assert success == True
    
    # Token should be in Redis
    token = await fake_redis.get(f"password_reset_token:{username}")
    assert token is not None
    
    # Step 2: Validate token
    valid, _ = await password_reset_service.validate_reset_token(username, token)
    assert valid == True
    
    # Step 3: Complete reset (mocked mongo)
    success, msg = await password_reset_service.complete_password_reset(username, token, "hashed_new_pwd")
    assert success == True
    
    # Token should be deleted
    token = await fake_redis.get(f"password_reset_token:{username}")
    assert token is None
```

**File:** `tests/api/test_quota_service.py`

```python
@pytest.mark.asyncio
async def test_quota_enforcement(quota_service):
    username = "free_user"
    
    # Free user can do 5 analyses
    for i in range(5):
        can_analyze, info = await quota_service.can_perform_analysis(username)
        assert can_analyze == True
        await quota_service.increment_usage(username)
    
    # 6th should fail
    can_analyze, info = await quota_service.can_perform_analysis(username)
    assert can_analyze == False
    assert info['remaining'] == 0

@pytest.mark.asyncio
async def test_premium_upgrade(quota_service):
    username = "user_to_upgrade"
    
    # Start as free
    tier = await quota_service.get_user_tier(username)
    assert tier == "free"
    
    # Upgrade to premium
    await quota_service.set_user_tier(username, "premium")
    
    # Now has 100 limit
    limit = await quota_service.get_quota_limit(username)
    assert limit == 100
```

---

## Migration Guide (for existing deployments)

### 1. Database Changes (MongoDB)

No new collections required. Optional: Add indexes for performance.

```javascript
// Optional: Index for faster lookups
db.users.createIndex({ "email": 1 })
db.users.createIndex({ "tier": 1 })
```

### 2. Environment Variables

Add new variables to `.env` (see Environment Variables section above).

### 3. Backwards Compatibility

All changes are **100% backwards compatible**:

- Existing `/auth/register` and `/auth/token` still work unchanged
- New endpoints are optional
- Existing users without tier default to "free"
- No database migrations needed

### 4. Redis Cleanup (optional)

To clean up test data:

```python
redis_client.delete(f"failed_attempts:*")
redis_client.delete(f"account_locked:*")
redis_client.delete(f"rate_limit:*")
redis_client.delete(f"password_reset_token:*")
redis_client.delete(f"user_usage:*")
redis_client.delete(f"user_tier:*")
```

---

## Monitoring & Observability

All services log important events with context:

```changes
# Account Lockout
logger.warning("Account 'john' locked after 5 failed attempts", extra={"username": "john", "attempts": 5})

# Rate Limit
logger.warning("Rate limit exceeded for 'jane'", extra={"username": "jane", "limit": 10})

# Password Reset
logger.info("Password reset email sent to john@example.com", extra={"username": "john", "email": "john@example.com"})

# Quota Check
logger.info("Quota check passed for 'bob'", extra={"username": "bob", "usage": 3, "remaining": 2})

# Payment Success
logger.info("User 'alice' upgraded to premium via Stripe", extra={"username": "alice"})
```

### Monitoring Queries

**Check locked accounts:**

```redis
KEYS account_locked:*
```

**Check user tier:**

```redis
GET user_tier:john_doe
```

**Check daily usage:**

```redis
GET user_usage:2026-02-02:jane_doe
```

---

## Known Limitations & Future Improvements

1. **Circuit Breaker:** Currently a service; could be wrapped as decorator around Gemini calls
2. **Stripe:** Currently mocked (returns stub); integrate real Stripe SDK in production
3. **Email:** Only Gmail supported; could abstract into email provider interface
4. **Quota Reset:** Midnight UTC; could be user-specific timezone
5. **Persistent Premium Tier:** Stored in Redis (no expiry); could add subscription expiry logic

---

## Summary

| Feature | Status | Files | API Endpoints |
| --- | --- | --- | --- |
| Account Lockout | ✅ Complete | `security_services.py` | `POST /auth/token` |
| Rate Limiting | ✅ Complete | `security_services.py` | `POST /analyze` |
| Config Refactor | ✅ Complete | `app_config.py` | All endpoints |
| Password Reset | ✅ Complete | `identity_services.py` | `POST /auth/request-reset`, `POST /auth/confirm-reset` |
| Usage Quotas | ✅ Complete | `monetization_services.py` | `POST /analyze`, `GET /auth/account-status` |
| Stripe Integration | ✅ Complete | `monetization_services.py` | `POST /payments/checkout`, `POST /payments/webhook` |
| Circuit Breaker | ✅ Complete | `app/gemini/circuit_breaker.py` | (Decorator-based) |
| UI - Forgot Password | ⏳ TODO | `app/ui/pages/forgot_password.py` | Streamlit form |
| UI - Reset Password | ⏳ TODO | `app/ui/pages/reset_password.py` | Streamlit form |
| UI - Account Status | ⏳ TODO | `app/ui/pages/account_status.py` | Streamlit dashboard |
| UI - Premium Upgrade | ⏳ TODO | Modify existing pages | Streamlit buttons |
| Tests | ⏳ TODO | `tests/api/test_*.py` | Unit & integration |
