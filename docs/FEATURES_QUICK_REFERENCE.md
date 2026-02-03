
# Quick Reference: New Features API & Configuration

## Environment Variables Checklist

Copy to `.env`:

```dotenv
# NEW: Security
JWT_SECRET_KEY=your-secret-key-here
MAX_FAILED_ATTEMPTS=5
LOCKOUT_DURATION_HOURS=24
RATE_LIMIT_ENABLED=true
RATE_LIMIT_REQUESTS=10
RATE_LIMIT_WINDOW_MINUTES=1

# NEW: Email (Gmail)
GMAIL_SENDER_EMAIL=your-email@gmail.com
GMAIL_APP_PASSWORD=xxxx-xxxx-xxxx-xxxx  # Google app password
PASSWORD_RESET_TOKEN_EXPIRY_HOURS=24

# NEW: Stripe
STRIPE_API_KEY=sk_test_xxxxx
STRIPE_WEBHOOK_SECRET=whsec_test_xxxxx
STRIPE_PRICE_ID_PREMIUM=price_xxxxx

# NEW: Quotas
FREE_TIER_DAILY_LIMIT=5
PREMIUM_TIER_DAILY_LIMIT=100

# EXISTING (now via config)
MONGO_URI=mongodb://mongo:27017/careerpilot
REDIS_HOST=redis
REDIS_PORT=6379
```

---

## API Endpoints Summary

### Authentication

| Endpoint               | Method | Purpose                       | Auth   | Notes              |
|------------------------|--------|-------------------------------|--------|--------------------|
| `/auth/register`       | POST   | Register new user             | -      | Unchanged          |
| `/auth/token`          | POST   | Login (now with lockout)      | -      | Returns JWT token  |
| `/auth/request-reset`  | POST   | Request password reset        | -      | Sends email        |
| `/auth/confirm-reset`  | POST   | Confirm password reset        | -      | Requires token     |
| `/auth/account-status` | GET    | Check tier, quota, lock       | Bearer | New endpoint       |

### Analysis

| Endpoint   | Method | Purpose                                       | Auth   | Notes           |
|------------|--------|-----------------------------------------------|--------|-----------------|
| `/analyze` | POST   | Analyze resume (now with quota & rate limit)  | Bearer | Enforces limits |

### Payments

| Endpoint              | Method | Purpose                 | Auth   | Notes               |
|-----------------------|--------|-------------------------|--------|---------------------|
| `/payments/checkout`  | POST   | Create Stripe checkout  | Bearer | New endpoint        |
| `/payments/webhook`   | POST   | Handle Stripe webhook   | -      | Signature verified  |

---

## Service Classes Quick Ref

### AccountLockoutService

```python
from app.api.security_services import AccountLockoutService
from app.api.app_config import get_config
from redis import asyncio as aioredis

config = get_config()
redis_client = aioredis.Redis(...)
service = AccountLockoutService(redis_client, config)

# Check lock
is_locked = await service.is_account_locked("john_doe")

# Record failure
await service.record_failed_attempt("john_doe")

# Reset on success
await service.reset_failed_attempts("john_doe")
```

### RateLimiterService

```python
from app.api.security_services import RateLimiterService

service = RateLimiterService(redis_client, config)

# Check if allowed
allowed, info = await service.is_allowed("john_doe")
# Returns: (bool, {"remaining": int, "reset_at": str})

if not allowed:
    raise HTTPException(status_code=429, detail=f"Limit exceeded. Reset at {info['reset_at']}")
```

### QuotaService

```python
from app.api.monetization_services import QuotaService

service = QuotaService(redis_client, config)

# Check usage
can_analyze, info = await service.can_perform_analysis("john_doe")
# Returns: (bool, {"usage": int, "limit": int, "remaining": int, "tier": str, "reset_at": str})

# After successful analysis
await service.increment_usage("john_doe")

# Check/set tier
tier = await service.get_user_tier("john_doe")  # "free" or "premium"
await service.set_user_tier("john_doe", "premium")
```

### PasswordResetService

```python
from app.api.identity_services import PasswordResetService

service = PasswordResetService(redis_client, mongo_handler, config)

# Request reset (sends email)
success, msg = await service.request_password_reset("john_doe", "john@example.com")

# Validate token
valid, msg = await service.validate_reset_token("john_doe", token)

# Complete reset (requires hashed password from auth.py)
success, msg = await service.complete_password_reset("john_doe", token, hashed_pwd)
```

### StripeService

```python
from app.api.monetization_services import StripeService

service = StripeService(quota_service, mongo_handler, config)

# Handle webhook
success, msg = await service.handle_payment_webhook(raw_payload, stripe_signature)
```

---

## Request/Response Examples

### Password Reset Flow

#### **1. Request Reset**

```curl
POST /auth/request-reset
Content-Type: application/json

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

#### **2. Confirm Reset**

```curl
POST /auth/confirm-reset
Content-Type: application/json

{
  "username": "john_doe",
  "token": "dN5q7zK2mP1jL8vX3yR4...",
  "new_password": "NewSecurePassword123!"
}

Response (200):
{
  "success": true,
  "message": "Password reset successfully!"
}
```

### Account Status

```curl
GET /auth/account-status
Authorization: Bearer <JWT_TOKEN>

Response (200):
{
  "username": "john_doe",
  "email": "john@example.com",
  "is_active": true,
  "is_locked": false,
  "tier": "free",
  "quota": {
    "usage": 3,
    "limit": 5,
    "remaining": 2,
    "tier": "free",
    "reset_at": "2026-02-03T00:00:00Z"
  },
  "roles": ["user"]
}
```

### Premium Upgrade

```curl
POST /payments/checkout
Authorization: Bearer <JWT_TOKEN>
Content-Type: application/json

{
  "username": "john_doe",
  "email": "john@example.com"
}

Response (200):
{
  "session_id": "cs_test_abc123",
  "redirect_url": "https://checkout.stripe.com/pay/cs_test_abc123",
  "status": "created"
}
```

### Error Responses

#### **Account Locked (429)**

```json
{
  "detail": "Account locked due to too many failed attempts. Try again in 24 hours."
}
```

#### **Rate Limit Exceeded (429)**

```json
{
  "detail": "Rate limit exceeded. 0 requests remaining. Resets at 2026-02-02T14:31:00Z"
}
```

#### **Quota Exceeded (402)**

```json
{
  "detail": "Daily quota exceeded. You have 5/5 analyses. Upgrade to premium or wait until 2026-02-03T00:00:00Z"
}
```

#### **Invalid Reset Token (400)**

```json
{
  "detail": "Invalid reset token."
}
```

---

## Common Tasks

### Check if User is Premium

```python
tier = await quota_service.get_user_tier(username)
is_premium = tier == "premium"
```

### Check User's Remaining Quota

```python
can_analyze, quota_info = await quota_service.can_perform_analysis(username)
print(f"Remaining: {quota_info['remaining']}")
```

### Upgrade User to Premium (after payment)

```python
await quota_service.set_user_tier(username, "premium")
await mongo_handler.set_user_premium(username)
```

### Manually Lock/Unlock Account

```python
# Lock
await redis_client.setex(f"account_locked:{username}", 86400, "1")

# Unlock
await redis_client.delete(f"account_locked:{username}")
```

### Reset Daily Usage for Testing

```python
from datetime import datetime
today = datetime.utcnow().strftime("%Y-%m-%d")
await redis_client.delete(f"user_usage:{today}:{username}")
```

---

## Testing Locally

### 1. Register User

```bash
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "email": "test@example.com",
    "password": "TestPassword123!",
    "roles": ["user"]
  }'
```

### 2. Login (with account lockout)

```bash
curl -X POST http://localhost:8000/auth/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d 'username=testuser&password=TestPassword123!'
```

### 3. Check Account Status

```bash
curl -X GET http://localhost:8000/auth/account-status \
  -H "Authorization: Bearer <TOKEN>"
```

### 4. Test Quota (call /analyze 6 times)

```bash
for i in {1..6}; do
  curl -X POST http://localhost:8000/analyze \
    -H "Authorization: Bearer <TOKEN>" \
    -H "Content-Type: application/json" \
    -d '{"resume_text":"...", "jd_text":"..."}'
done
# 6th call returns 402 Payment Required
```

### 5. Request Password Reset

```bash
curl -X POST http://localhost:8000/auth/request-reset \
  -H "Content-Type: application/json" \
  -d '{"username": "testuser", "email": "test@example.com"}'
```

---

## Troubleshooting

### Gmail auth fails

**Error:** `SMTPAuthenticationError`

**Solution:**

1. Create app-specific password in Gmail Settings → Security → App passwords
2. Use that password (not your Gmail password) in `GMAIL_APP_PASSWORD`
3. Ensure 2FA is enabled

### Stripe webhook not triggered

**Solution:**

1. Use `stripe listen` CLI to forward webhooks locally
2. Use ngrok to expose local endpoint publicly
3. Configure webhook URL in Stripe dashboard

### User stuck in locked state

**Solution:**

```python
# Delete lock key directly
await redis_client.delete(f"account_locked:{username}")
```

### Quota not resetting

**Solution:**
Check Redis key: `user_usage:2026-02-02:username`

- Should have TTL set to ~23h 59m
- If missing, quota has already reset

---

## Files Summary

| File                            | Purpose             | Key Classes                                                          |
|---------------------------------|---------------------|----------------------------------------------------------------------|
| `app/api/app_config.py`         | Centralized config  | `AppConfig`, `get_config()`                                          |
| `app/api/security_services.py`  | Auth security       | `AccountLockoutService`, `RateLimiterService`                        |
| `app/api/identity_services.py`  | Password reset      | `PasswordResetService`                                               |
| `app/api/monetization_services.py`| Quotas & payments | `QuotaService`, `StripeService`, `PaymentService`                   |
| `app/gemini/circuit_breaker.py` | Resilience          | `@circuit_breaker` decorator                                         |
| `app/api/server.py`             | API endpoints       | All new endpoints integrated                                         |
| `app/utils/mongo_handler.py`    | DB                  | New methods: `update_user_password`, `set_user_premium`              |
| `FEATURES_IMPLEMENTATION.md`    | Full docs           | This complete guide                                                  |

---

## Support

For issues or questions, check:

1. `FEATURES_IMPLEMENTATION.md` for detailed docs
2. Logs: Look for service class names (e.g., `[AccountLockoutService]`)
3. Redis keys: Use `redis-cli KEYS '*'` to inspect state
4. MongoDB: Check user documents for `tier` and `roles` fields
