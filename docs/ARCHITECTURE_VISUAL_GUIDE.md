
# 🏗️ Modular Architecture - Visual Guide

## System Architecture Diagram

```arch
┌─────────────────────────────────────────────────────────────────────────┐
│                        CLIENT LAYER                                     │
│                    (Web, Mobile, Desktop)                               │
└────────────────────────────────┬────────────────────────────────────────┘
                                 │
                                 │ HTTP Requests
                                 ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      FASTAPI APPLICATION                                │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │                     server.py (174 lines)                        │  │
│  │  ┌─────────────────────────────────────────────────────────┐   │  │
│  │  │ Startup                                                  │   │  │
│  │  │  ├─ Create Redis client                                 │   │  │
│  │  │  ├─ Create Services                                     │   │  │
│  │  │  │  ├─ AccountLockoutService                            │   │  │
│  │  │  │  ├─ RateLimiterService                               │   │  │
│  │  │  │  ├─ PasswordResetService                             │   │  │
│  │  │  │  ├─ QuotaService                                     │   │  │
│  │  │  │  ├─ StripeService                                    │   │  │
│  │  │  │  ├─ PaymentService                                   │   │  │
│  │  │  │  ├─ GeminiClient                                     │   │  │
│  │  │  │  └─ CareerPilotAgent                                 │   │  │
│  │  │  ├─ Include Routers                                     │   │  │
│  │  │  └─ Inject Services into Routers                        │   │  │
│  │  └─────────────────────────────────────────────────────────┘   │  │
│  │                                                                  │  │
│  │  ┌─────────────────────────────────────────────────────────┐   │  │
│  │  │ Middleware                                               │   │  │
│  │  │  ├─ Request logging & session tracking                   │   │  │
│  │  │  ├─ CORS configuration                                   │   │  │
│  │  │  └─ Exception handling                                   │   │  │
│  │  └─────────────────────────────────────────────────────────┘   │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                                                                         │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │                    MODULAR ROUTERS                               │  │
│  │                  (Domain-Specific)                               │  │
│  ├──────────────────────────────────────────────────────────────────┤  │
│  │  ┌────────────────────────────────────────────────────────────┐ │  │
│  │  │ auth_router.py (Authentication Domain)                    │ │  │
│  │  │ ├─ POST   /auth/register                                  │ │  │
│  │  │ ├─ POST   /auth/token                                     │ │  │
│  │  │ ├─ POST   /auth/request-reset                             │ │  │
│  │  │ ├─ POST   /auth/confirm-reset                             │ │  │
│  │  │ ├─ GET    /auth/account-status                            │ │  │
│  │  │ └─ GET    /auth/me                                        │ │  │
│  │  │ Services: AccountLockout, PasswordReset, Quota            │ │  │
│  │  └────────────────────────────────────────────────────────────┘ │  │
│  │                                                                  │  │
│  │  ┌────────────────────────────────────────────────────────────┐ │  │
│  │  │ analysis_router.py (Analysis Domain)                       │ │  │
│  │  │ ├─ POST   /analyze                                         │ │  │
│  │  │ ├─ POST   /analyze_video                                   │ │  │
│  │  │ ├─ POST   /evaluate_answer                                 │ │  │
│  │  │ ├─ POST   /stream/analyze                                  │ │  │
│  │  │ └─ POST   /stream/evaluate                                 │ │  │
│  │  │ Services: Agent, GeminiClient, RateLimiter, Quota          │ │  │
│  │  └────────────────────────────────────────────────────────────┘ │  │
│  │                                                                  │  │
│  │  ┌────────────────────────────────────────────────────────────┐ │  │
│  │  │ payment_router.py (Monetization Domain)                    │ │  │
│  │  │ ├─ POST   /payments/checkout                               │ │  │
│  │  │ ├─ POST   /payments/webhook                                │ │  │
│  │  │ └─ GET    /payments/status/{username}                      │ │  │
│  │  │ Services: Quota, Stripe, Payment                           │ │  │
│  │  └────────────────────────────────────────────────────────────┘ │  │
│  │                                                                  │  │
│  │  ┌────────────────────────────────────────────────────────────┐ │  │
│  │  │ rag_router.py (RAG Domain)                                 │ │  │
│  │  │ ├─ POST   /rag/search                                      │ │  │
│  │  │ └─ POST   /rag/ingest                                      │ │  │
│  │  │ Services: GeminiClient                                     │ │  │
│  │  └────────────────────────────────────────────────────────────┘ │  │
│  │                                                                  │  │
│  │  ┌────────────────────────────────────────────────────────────┐ │  │
│  │  │ health_router.py (System Domain)                           │ │  │
│  │  │ ├─ GET    /health                                          │ │  │
│  │  │ └─ GET    /                                                │ │  │
│  │  │ Services: None                                             │ │  │
│  │  └────────────────────────────────────────────────────────────┘ │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                                                                         │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │                    LEGACY ROUTERS                                │  │
│  │         (Unchanged, included for backward compatibility)        │  │
│  │  ├─ mock_interview router                                      │  │
│  │  └─ analysis_history router                                    │  │
│  └──────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
                                 │
                  ┌──────────────┼──────────────┐
                  │              │              │
                  ▼              ▼              ▼
            ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐
            │  Redis   │  │ MongoDB  │  │ Gemini   │  │ Jaeger   │
            │  (Cache) │  │(Database)│  │  API     │  │(Tracing) │
            └──────────┘  └──────────┘  └──────────┘  └──────────┘
```

---

## Router Initialization Sequence

```arch
┌────────────────────────────────────────────────────────────────────────┐
│                       Application Startup                              │
└────────────────────────┬─────────────────────────────────────────────────┘
                         │
                         ▼
         ┌───────────────────────────────────┐
         │ 1. Load Configuration             │
         │    (from .env, app_config.py)     │
         │                                   │
         │ ┌─────────────────────────────┐   │
         │ │ SecuritySettings            │   │
         │ │ DatabaseSettings            │   │
         │ │ EmailSettings               │   │
         │ │ StripeSettings              │   │
         │ │ QuotaSettings               │   │
         │ │ GeminiSettings              │   │
         │ └─────────────────────────────┘   │
         └───────────────┬───────────────────┘
                         │
                         ▼
         ┌───────────────────────────────────┐
         │ 2. Create Service Instances       │
         │    (in server.py)                 │
         │                                   │
         │ ┌─────────────────────────────┐   │
         │ │ - redis_client              │   │
         │ │ - AccountLockoutService     │   │
         │ │ - RateLimiterService        │   │
         │ │ - PasswordResetService      │   │
         │ │ - QuotaService              │   │
         │ │ - StripeService             │   │
         │ │ - PaymentService            │   │
         │ │ - GeminiClient              │   │
         │ │ - CareerPilotAgent          │   │
         │ └─────────────────────────────┘   │
         └───────────────┬───────────────────┘
                         │
                         ▼
         ┌───────────────────────────────────┐
         │ 3. Include Routers                │
         │                                   │
         │ app.include_router(               │
         │   auth_router.router              │
         │ )                                 │
         │ app.include_router(               │
         │   analysis_router.router          │
         │ )                                 │
         │ ... (repeat for all routers)      │
         │                                   │
         └───────────────┬───────────────────┘
                         │
                         ▼
         ┌───────────────────────────────────┐
         │ 4. Dependency Injection           │
         │    (Pass services to routers)     │
         │                                   │
         │ init_auth_services(               │
         │   account_lockout_service,        │
         │   password_reset_service,         │
         │   quota_service                   │
         │ )                                 │
         │                                   │
         │ init_analysis_services(           │
         │   agent,                          │
         │   gemini_client,                  │
         │   rate_limiter_service,           │
         │   quota_service                   │
         │ )                                 │
         │ ... (repeat for all routers)      │
         │                                   │
         │ Each router now has access to:    │
         │ global account_lockout_service    │
         │ global password_reset_service     │
         │ global quota_service              │
         │ etc.                              │
         │                                   │
         └───────────────┬───────────────────┘
                         │
                         ▼
         ┌───────────────────────────────────┐
         │ 5. Ready for Requests             │
         │                                   │
         │ - All routes registered           │
         │ - All services injected           │
         │ - Middleware configured           │
         │ - Exception handlers ready        │
         │                                   │
         │ ✅ API Ready to Serve Clients    │
         │                                   │
         └───────────────────────────────────┘
```

---

## Request Flow: Example - POST /auth/token

```arch
CLIENT REQUEST
│
│ POST /auth/token
│ {
│   "username": "john",
│   "password": "secure123"
│ }
│
▼
┌──────────────────────────────────────────┐
│ FastAPI Router (auth_router)             │
│                                          │
│ @router.post("/token")                   │
│ async def login_for_access_token(...)    │
└──────────────────────────┬───────────────┘
                           │
                           ▼
                ┌─────────────────────────────┐
                │ Check if account is locked  │
                │                             │
                │ is_locked = await           │
                │   account_lockout_service   │
                │   .is_account_locked(      │
                │     username               │
                │   )                        │
                └──────────────┬──────────────┘
                               │
                        ┌──────┴──────┐
                        │             │
        ┌───────────────▼─┐        ┌──▼────────────────┐
        │ Account Locked  │        │ Account Not Locked│
        │                │        │                  │
        │ Return 429 Too │        │ Continue...       │
        │ Many Requests  │        │                  │
        └────────────────┘        └──────┬───────────┘
                                         │
                                         ▼
                          ┌──────────────────────────┐
                          │ Get user from database   │
                          │                          │
                          │ user = await             │
                          │   mongo_handler.get_user │
                          │   (username)             │
                          └──────────────┬───────────┘
                                         │
                      ┌──────────────────┴──────────────────┐
                      │                                     │
        ┌─────────────▼────────┐            ┌──────────────▼──────┐
        │ User Not Found or    │            │ User Found &        │
        │ Password Incorrect   │            │ Password Correct    │
        │                      │            │                     │
        │ Record failed attempt│            │ Reset failed        │
        │ await account_lockout│            │ attempts            │
        │   .record_failed_    │            │ await account_lockout│
        │   attempt(username)  │            │   .reset_failed_    │
        │                      │            │   attempts(username)│
        │ Return 401           │            │                     │
        │ Unauthorized         │            │ Create JWT token    │
        │                      │            │ token = create_     │
        │                      │            │   access_token(...) │
        │                      │            │                     │
        │                      │            │ Return 200 OK       │
        │                      │            │ with token          │
        └──────────────────────┘            └──────────────────────┘

CLIENT RECEIVES RESPONSE
```

---

## SOLID Principles - Visual Representation

```arch
┌─────────────────────────────────────────────────────────────────────┐
│                    SOLID PRINCIPLES                                 │
└─────────────────────────────────────────────────────────────────────┘

1. SINGLE RESPONSIBILITY PRINCIPLE
   ┌──────────────────────────────────────────────────────────────┐
   │ Each router has ONE reason to change                         │
   │                                                              │
   │  auth_router.py    ◄─── Changes if auth logic changes      │
   │  analysis_router.py ◄─── Changes if analysis logic changes │
   │  payment_router.py  ◄─── Changes if payment logic changes  │
   │  rag_router.py      ◄─── Changes if RAG logic changes      │
   │                                                              │
   │ NOT: "All logic in one file"                                │
   └──────────────────────────────────────────────────────────────┘

2. OPEN/CLOSED PRINCIPLE
   ┌──────────────────────────────────────────────────────────────┐
   │ Open for extension, closed for modification                  │
   │                                                              │
   │ ✅ To add feedback feature:                                 │
   │    1. Create routers/feedback_router.py                     │
   │    2. Update routers/__init__.py                            │
   │    3. Update server.py (2 lines)                            │
   │    → No changes to existing routers!                        │
   │                                                              │
   │ ❌ Old way:                                                 │
   │    Modify server.py (add 50+ lines)                         │
   │    Risk breaking existing code                             │
   └──────────────────────────────────────────────────────────────┘

3. LISKOV SUBSTITUTION PRINCIPLE
   ┌──────────────────────────────────────────────────────────────┐
   │ All routers follow the same pattern                          │
   │                                                              │
   │  router = APIRouter(prefix="...", tags=[...])               │
   │  service = None                                             │
   │  def init_*_services(*services):                            │
   │      global service                                         │
   │      service = service                                      │
   │  @router.post("/path")                                      │
   │  async def endpoint(...):                                   │
   │      # Use injected service                                 │
   │                                                              │
   │ Any router can replace another without breaking app         │
   └──────────────────────────────────────────────────────────────┘

4. INTERFACE SEGREGATION PRINCIPLE
   ┌──────────────────────────────────────────────────────────────┐
   │ Each router exposes ONLY needed endpoints                    │
   │                                                              │
   │  auth_router: 6 endpoints (all auth-related)                │
   │              NO payment endpoints                            │
   │              NO analysis endpoints                           │
   │                                                              │
   │  payment_router: 3 endpoints (all payment-related)           │
   │                 NO analysis endpoints                        │
   │                 NO auth endpoints                            │
   │                                                              │
   │  ❌ Old way: One huge server.py with all endpoints           │
   │     Router must know about everything                        │
   └──────────────────────────────────────────────────────────────┘

5. DEPENDENCY INVERSION PRINCIPLE
   ┌──────────────────────────────────────────────────────────────┐
   │ Depend on abstractions, not concrete implementations         │
   │                                                              │
   │  server.py ────┐                                             │
   │                │  Creates and injects                        │
   │                ▼                                             │
   │         account_lockout_service                              │
   │                │                                             │
   │                │  Injected into                              │
   │                ▼                                             │
   │         auth_router.py (global variable)                    │
   │                │                                             │
   │                │  Used by                                    │
   │                ▼                                             │
   │         login_for_access_token()                            │
   │                                                              │
   │ Benefits:                                                    │
   │ - Easy to mock for testing                                  │
   │ - Easy to swap implementation                               │
   │ - Loose coupling                                            │
   │ - High-level modules don't depend on low-level modules      │
   └──────────────────────────────────────────────────────────────┘
```

---

## Directory Structure Tree

```arch
CareerPilot/
│
├── app/
│   └── api/
│       ├── server.py ............................ MAIN FILE (174 lines)
│       │   ├─ Service initialization
│       │   ├─ Router imports
│       │   ├─ Router includes
│       │   ├─ Service injection
│       │   ├─ Middleware
│       │   ├─ Exception handling
│       │   └─ CORS configuration
│       │
│       ├── routers/ ............................ DOMAIN ROUTERS (NEW)
│       │   ├─ __init__.py
│       │   │   └─ Central import hub
│       │   │
│       │   ├─ auth_router.py .................. 170 lines
│       │   │   ├─ register
│       │   │   ├─ token
│       │   │   ├─ request-reset
│       │   │   ├─ confirm-reset
│       │   │   ├─ account-status
│       │   │   └─ me
│       │   │   Services: AccountLockout, PasswordReset, Quota
│       │   │
│       │   ├─ analysis_router.py ............. 180 lines
│       │   │   ├─ analyze
│       │   │   ├─ analyze_video
│       │   │   ├─ evaluate_answer
│       │   │   ├─ stream/analyze
│       │   │   └─ stream/evaluate
│       │   │   Services: Agent, GeminiClient, RateLimiter, Quota
│       │   │
│       │   ├─ payment_router.py .............. 120 lines
│       │   │   ├─ checkout
│       │   │   ├─ webhook
│       │   │   └─ status
│       │   │   Services: Quota, Stripe, Payment
│       │   │
│       │   ├─ rag_router.py .................. 100 lines
│       │   │   ├─ search
│       │   │   └─ ingest
│       │   │   Services: GeminiClient
│       │   │
│       │   └─ health_router.py ............... 25 lines
│       │       ├─ health
│       │       └─ root
│       │       Services: None
│       │
│       ├── config.py .......................... (unchanged)
│       ├── auth.py ........................... (unchanged)
│       ├── app_config.py ..................... (unchanged)
│       ├── schemas.py ........................ (unchanged)
│       ├── security_services.py ............. (unchanged)
│       ├── identity_services.py ............. (unchanged)
│       ├── monetization_services.py ......... (unchanged)
│       │
│       ├── mock_interview.py ................ (legacy router)
│       └── analysis_history.py .............. (legacy router)
│
└── docs/
    ├── MODULAR_ARCHITECTURE.md .............. Comprehensive guide
    ├── ROUTERS_QUICK_REFERENCE.md .......... Quick reference
    └── REFACTORING_SUMMARY.md .............. Summary (this file)
```

---

## Before & After Comparison

### BEFORE: Monolithic

```arch
app/api/server.py (508 lines)
│
├─ Imports (30 lines)
├─ Config & Services (60 lines)
├─ Auth endpoints (120 lines) ◄─── Mixed with everything else
├─ Analysis endpoints (150 lines) ◄─── Hard to navigate
├─ RAG endpoints (40 lines) ◄─── Everything in one place
├─ Payment endpoints (60 lines)
├─ Health check (5 lines)
├─ Streaming endpoints (30 lines)
├─ Middleware (25 lines)
├─ Exception handling (10 lines)
└─ CORS configuration (15 lines)

Problems:
❌ Hard to find specific endpoints
❌ Hard to test individual domains
❌ Hard to understand code flow
❌ Hard to add features without risking breaking changes
❌ Violates Single Responsibility Principle
❌ Tight coupling
❌ Not scalable
```

### AFTER: Modular

```arch
app/api/server.py (174 lines)
│
├─ Imports (50 lines) ◄─ Includes routers
├─ Config & Services (50 lines)
├─ Router Includes (10 lines) ◄─ Clean, organized
├─ Service Injection (15 lines)
├─ Middleware (30 lines)
├─ Exception handling (10 lines)
└─ CORS configuration (9 lines)

app/api/routers/
├─ __init__.py (20 lines) ◄─ Central hub
├─ auth_router.py (170 lines) ◄─ Isolated domain
├─ analysis_router.py (180 lines) ◄─ Isolated domain
├─ payment_router.py (120 lines) ◄─ Isolated domain
├─ rag_router.py (100 lines) ◄─ Isolated domain
└─ health_router.py (25 lines) ◄─ Isolated domain

Benefits:
✅ Easy to find specific endpoints
✅ Easy to test individual domains
✅ Easy to understand code flow
✅ Easy to add features safely
✅ Follows Single Responsibility Principle
✅ Loose coupling
✅ Highly scalable
✅ Professional, maintainable architecture
```

---

#### **Architecture Status: ✅ PRODUCTION READY**
