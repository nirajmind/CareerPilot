
# 🚀 Modular Architecture - Quick Reference Guide

## The Big Picture

**Before:** One giant `server.py` file (500+ lines)  
**After:** Clean `server.py` (90 lines) + 5 domain-specific routers

---

## File Locations

```arch
app/api/
├── server.py ........................ Main app (startup, middleware)
└── routers/
    ├── __init__.py .................. Import/export hub
    ├── auth_router.py ............... Login, password reset, account status
    ├── analysis_router.py ........... Resume analysis, video, evaluation
    ├── payment_router.py ............ Stripe, checkout, webhooks
    ├── rag_router.py ................ Vector search, document ingestion
    └── health_router.py ............ Health checks
```

---

## How Endpoints Are Organized

```arch
Domain              Endpoints                           Router
─────────────────────────────────────────────────────────────
Authentication      /auth/register                      auth_router
                    /auth/token
                    /auth/request-reset
                    /auth/confirm-reset
                    /auth/account-status
                    /auth/me

Analysis            /analyze                            analysis_router
                    /analyze_video
                    /evaluate_answer
                    /stream/analyze
                    /stream/evaluate

Payments            /payments/checkout                  payment_router
                    /payments/webhook
                    /payments/status/{username}

RAG                 /rag/search                         rag_router
                    /rag/ingest

Health              /health                             health_router
                    /
```

---

## How It Works

### 1️⃣ Server Startup

```python
# app/api/server.py

# Create services once
account_lockout_service = AccountLockoutService(redis_client, config)
rate_limiter_service = RateLimiterService(redis_client, config)
...

# Include routers
app.include_router(auth_router.router)
app.include_router(analysis_router.router)
...

# Inject services into routers
init_auth_services(account_lockout_service, ...)
init_analysis_services(agent, gemini_client, ...)
...
```

### 2️⃣ Router Uses Injected Services

```python
# app/api/routers/auth_router.py

# Services injected here at startup
account_lockout_service = None

def init_auth_services(lockout_service, ...):
    global account_lockout_service
    account_lockout_service = lockout_service

@router.post("/token")
async def login(...):
    # Can now use the service
    is_locked = await account_lockout_service.is_account_locked(...)
```

---

## Adding a New Endpoint

### Scenario: Add new endpoint to existing router

**Step 1:** Open the appropriate router file

```python
# app/api/routers/auth_router.py
```

**Step 2:** Add the endpoint

```python
@router.post("/change-password")
async def change_password(
    req: ChangePasswordRequest,
    current_user: dict = Depends(get_current_user)
):
    """Change user password."""
    # Implementation here
    pass
```

**Done!** ✅ Endpoint is immediately available.

---

## Adding a New Router (New Domain)

### Scenario: Add feedback feature with 5 endpoints

**Step 1:** Create new router file

```python
# app/api/routers/feedback_router.py

from fastapi import APIRouter, Depends
from app.api.auth import get_current_user

router = APIRouter(prefix="/feedback", tags=["Feedback"])

# Services
feedback_service = None

def init_feedback_services(service):
    global feedback_service
    feedback_service = service

@router.post("/submit")
async def submit_feedback(req: FeedbackRequest, current_user: dict = Depends(get_current_user)):
    pass

@router.get("/list")
async def list_feedback(current_user: dict = Depends(get_current_user)):
    pass

# ... more endpoints
```

**Step 2:** Update `routers/__init__.py`

```python
from app.api.routers.feedback_router import router as feedback_router, init_feedback_services

__all__ = [
    # existing routers...
    "feedback_router",
    "init_feedback_services",
]
```

**Step 3:** Update `server.py`

```python
from app.api.routers import (
    # ... existing
    feedback_router,
    init_feedback_services,
)

# Include router
app.include_router(feedback_router.router)

# Initialize services
init_feedback_services(feedback_service)
```

**Done!** ✅ New domain is integrated.

---

## Testing a Router

### Test auth router in isolation

```python
# tests/api/routers/test_auth_router.py

from fastapi.testclient import TestClient
from app.api.routers import auth_router, init_auth_services

def test_register():
    # Create app with just this router
    from fastapi import FastAPI
    app = FastAPI()
    app.include_router(auth_router.router)
    
    # Mock services
    mock_lockout = MockAccountLockoutService()
    mock_reset = MockPasswordResetService()
    
    init_auth_services(mock_lockout, mock_reset, ...)
    
    # Test
    client = TestClient(app)
    response = client.post("/auth/register", json={...})
    assert response.status_code == 201
```

---

## SOLID Principles in Practice

### ✅ Single Responsibility

- `auth_router.py` handles ONLY authentication
- `analysis_router.py` handles ONLY analysis
- `payment_router.py` handles ONLY payments
- Each file changes for ONE reason

### ✅ Open/Closed Principle

- **Open for extension:** Add `feedback_router.py` without touching existing routers
- **Closed for modification:** No need to modify `auth_router.py` when adding payments

### ✅ Liskov Substitution Principle

- All routers follow same pattern
- Can swap routers without breaking code
- Each router is replaceable

### ✅ Interface Segregation Principle

- Routers expose only needed endpoints
- Services injected only when required
- No "fat" routers with unnecessary endpoints

### ✅ Dependency Inversion

- Routers depend on service abstractions
- Easy to mock services for testing
- Implementation can change without router changes

---

## Directory Structure Explanation

```arch
app/
├── api/
│   ├── server.py
│   │   ├── Creates services
│   │   ├── Includes routers
│   │   ├── Injects services
│   │   └── Handles middleware
│   │
│   ├── routers/
│   │   ├── __init__.py (IMPORT HUB)
│   │   │   └── Central place to import all routers
│   │   │       Keep this updated when adding routers
│   │   │
│   │   ├── auth_router.py (DOMAIN: Authentication)
│   │   │   ├── Register, login, password reset
│   │   │   ├── Account status
│   │   │   └── Global services: account_lockout_service, password_reset_service
│   │   │
│   │   ├── analysis_router.py (DOMAIN: Analysis)
│   │   │   ├── Resume analysis, video analysis
│   │   │   ├── Answer evaluation, streaming
│   │   │   └── Global services: agent, gemini_client, rate_limiter_service
│   │   │
│   │   ├── payment_router.py (DOMAIN: Monetization)
│   │   │   ├── Checkout, webhooks, status
│   │   │   └── Global services: quota_service, stripe_service
│   │   │
│   │   ├── rag_router.py (DOMAIN: RAG)
│   │   │   ├── Search, ingest
│   │   │   └── Global services: gemini_client
│   │   │
│   │   └── health_router.py (DOMAIN: System)
│   │       ├── Health checks
│   │       └── No services needed
│   │
│   └── (OTHER FILES - unchanged)
│       ├── auth.py
│       ├── app_config.py
│       ├── schemas.py
│       ├── security_services.py
│       ├── identity_services.py
│       ├── monetization_services.py
│       └── ...
```

---

## Common Tasks

### Find an endpoint?

1. Look at the endpoint path
2. Determine the domain (auth, analysis, payments, etc.)
3. Open the appropriate router file
4. Find your endpoint

Example: Looking for `/analyze` endpoint?

- Domain: Analysis
- File: `routers/analysis_router.py`
- Line: Search for `@router.post("/analyze")`

### Add an endpoint to existing domain?

1. Open the router file for that domain
2. Add `@router.method("path")`
3. Implement the function
4. Done!

### Add an endpoint to new domain?

1. Create new router file: `routers/new_domain_router.py`
2. Follow router pattern (see existing routers)
3. Update `routers/__init__.py`
4. Update `server.py`
5. Done!

### Test an endpoint?

1. Use Swagger UI: <http://localhost:8585/docs>
2. Click on the endpoint
3. Click "Try it out"
4. Enter parameters
5. Click "Execute"

### Test a router in code?

1. Import router: `from app.api.routers.auth_router import router, init_auth_services`
2. Create FastAPI app: `app = FastAPI()`
3. Include router: `app.include_router(router.router)`
4. Mock services: `init_auth_services(mock_lockout, ...)`
5. Create test client: `client = TestClient(app)`
6. Make requests: `client.post("/auth/register", json={...})`

---

## Key Concepts

### APIRouter

- FastAPI's way to organize endpoints
- Each router is a separate module
- Routers are included in main app with `app.include_router()`

### Prefix

- URL prefix for all endpoints in router
- Example: `APIRouter(prefix="/auth")` → `/auth/register`, `/auth/token`

### Tags

- Organize endpoints in Swagger UI
- Example: `APIRouter(..., tags=["Authentication"])`

### Dependency Injection

- Services created in `server.py`
- Passed to routers via `init_*_services()` functions
- Routers store as global variables
- Accessed in endpoints

### Global Variables (in routers)

- Stores injected services
- Initialized by `init_*_services()` from `server.py`
- Not ideal in general, but acceptable here because:
  - Services are created once at startup
  - Reduces coupling between routers and server.py
  - Simplifies endpoint definitions

---

## Benefits Summary

| Benefit | Why It Matters |
| --------- | ---------------- |
| **Maintainability** | Find code quickly, understand context |
| **Scalability** | Add features without modifying existing code |
| **Testability** | Test routers independently with mocked services |
| **Reusability** | Use routers in different apps if needed |
| **Clarity** | 90-line server.py instead of 500-line monolith |
| **Extensibility** | Add new domains without touching existing ones |
| **Performance** | Zero runtime overhead, same speed as before |

---

## Troubleshooting

### Q: Endpoint not found?

**A:** Check router is included in `server.py` and services are initialized

### Q: Service is None in endpoint?

**A:** Check `init_*_services()` is called in `server.py`

### Q: Can't find endpoint in docs?

**A:** Check `tags=` parameter in `APIRouter()` and verify router is included

### Q: Want to add endpoint to different domain?

**A:** Create new router file or use existing router for that domain

---

## Next Steps

- ✅ Refactoring complete
- ⏭️ Run tests to verify everything works
- ⏭️ Review endpoint documentation in Swagger UI
- ⏭️ Add tests for each router
- ⏭️ Consider moving legacy routers to `routers/` directory

---

### **Pattern established. Ready to scale! 🚀**
