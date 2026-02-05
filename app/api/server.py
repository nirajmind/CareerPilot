from datetime import datetime
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import time
import uuid

from redis import asyncio as aioredis

from app.utils.logger import setup_logger
from app.utils.mongo_handler import mongo_handler


# --- Tracing ---
from app.utils.tracing import setup_tracing
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.instrumentation.pymongo import PymongoInstrumentor

# --- Config & Services ---
from app.api.app_config import get_config
from app.api.security_services import AccountLockoutService, RateLimiterService, CircuitBreakerService
from app.api.identity_services import PasswordResetService
from app.api.monetization_services import QuotaService, StripeService, PaymentService

# --- Gemini Client & Agent ---
from app.gemini import GeminiClient
from app.agent.workflow import CareerPilotAgent

# --- Routers (Modular, SOLID-compliant) ---
from app.api.routers import (
    auth_router,
    analysis_router,
    payment_router,
    rag_router,
    health_router,
    init_auth_services,
    init_analysis_services,
    init_payment_services,
    init_rag_services,
    init_health_services,
)

# --- Legacy Routers ---
from app.api.mock_interview import router as mock_router
from app.api.analysis_history import router as analysis_history_router

from .config import API_TITLE, API_VERSION

logger = setup_logger()
config = get_config()

# --- Redis Client ---
redis_client = aioredis.Redis(
    host=config.database.redis_host,
    port=config.database.redis_port,
    decode_responses=config.database.redis_decode_responses
)

# --- Service Initialization ---
account_lockout_service = AccountLockoutService(redis_client, config)
rate_limiter_service = RateLimiterService(redis_client, config)
password_reset_service = PasswordResetService(redis_client, mongo_handler, config)
quota_service = QuotaService(redis_client, config)
stripe_service = StripeService(quota_service, mongo_handler, config)
payment_service = PaymentService(config)
circuit_breaker_service = CircuitBreakerService(redis_client, "gemini", config)

# --- Gemini Client & Agent ---
gemini_client = GeminiClient(redis_client=redis_client)
agent = CareerPilotAgent(gemini_client=gemini_client, redis_client=redis_client)

# --- FastAPI App ---
app = FastAPI(title=API_TITLE, version=API_VERSION)

# --- Tracing Initialization ---
# Middleware must be added before application startup.
if config.tracing.enabled:
    setup_tracing(config.tracing.service_name, config.tracing.otlp_endpoint)
    # Instrument FastAPI (must be done before startup to attach middleware)
    FastAPIInstrumentor.instrument_app(app)
    RedisInstrumentor().instrument()
    PymongoInstrumentor().instrument()
    logger.info("OpenTelemetry instrumentation enabled.")

# --- Include Modular Routers (SOLID-Compliant) ---
app.include_router(health_router)
app.include_router(auth_router)
app.include_router(analysis_router)
app.include_router(payment_router)
app.include_router(rag_router)

# --- Include Legacy Routers ---
app.include_router(mock_router)
app.include_router(analysis_history_router)

# --- Initialize Router Services (Dependency Injection) ---
init_auth_services(account_lockout_service, password_reset_service, quota_service)
init_analysis_services(agent, gemini_client, rate_limiter_service, quota_service)
init_payment_services(quota_service, stripe_service, payment_service)
init_rag_services(gemini_client)
init_health_services(redis_client)

# ---------------------------------------------------------
# Global Exception Handler
# ---------------------------------------------------------
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler - logs all unhandled exceptions."""
    logger.exception("Unhandled exception occurred")
    return JSONResponse(
        status_code=500,
        content={"error": str(exc)}
    )


# ---------------------------------------------------------
# Startup / Shutdown Events
# ---------------------------------------------------------
@app.on_event("startup")
async def startup_event():
    """Initialize database connections and tracing on startup."""
    logger.info("Starting up CareerPilot API...")
    


    mongo_handler.connect()
    
    # --- Load Dynamic Config from DB ---
    try:
        db_config = await mongo_handler.get_system_config()
        if db_config:
            logger.info("Loading dynamic configuration from MongoDB...")
            
            # Update specific sections if present in DB
            # 1. Quota Settings
            if "quota" in db_config:
                q_conf = db_config["quota"]
                # Update attributes in place (since we made valid mutable)
                if "free_tier_daily_limit" in q_conf:
                    config.quota.free_tier_daily_limit = q_conf["free_tier_daily_limit"]
                if "premium_tier_daily_limit" in q_conf:
                    config.quota.premium_tier_daily_limit = q_conf["premium_tier_daily_limit"]
                logger.info("Updated Quota settings from DB")

            # 2. Gemini Settings (Models)
            if "gemini" in db_config:
                g_conf = db_config["gemini"]
                if "gemini_model" in g_conf:
                    config.gemini.gemini_model = g_conf["gemini_model"]
                    gemini_client.chat_model = config.gemini.gemini_model # Sync to client
                if "gemini_vision_model" in g_conf:
                    config.gemini.gemini_vision_model = g_conf["gemini_vision_model"]
                    gemini_client.vision_model = config.gemini.gemini_vision_model # Sync to client
                logger.info("Updated Gemini settings from DB")

    except Exception as e:
        logger.error(f"Failed to load dynamic config from DB: {e}")

    logger.info("✅ API startup complete")


@app.on_event("shutdown")
def shutdown_event():
    """Close database connections on shutdown."""
    logger.info("Shutting down CareerPilot API...")
    mongo_handler.close()
    logger.info("✅ API shutdown complete")


# ---------------------------------------------------------
# Middleware: Request Logging & Session Tracking
# ---------------------------------------------------------
@app.middleware("http")
async def db_handler_middleware(request: Request, call_next):
    """Middleware to track sessions and log requests."""
    start_time = time.time()
    session_id = str(uuid.uuid4())

    await mongo_handler.insert_session({
        "session_id": session_id,
        "start_time": start_time,
        "request_path": request.url.path,
        "request_method": request.method,
    })

    response = await call_next(request)

    await mongo_handler.insert_log({
        "session_id": session_id,
        "request_path": request.url.path,
        "request_method": request.method,
        "process_time": time.time() - start_time,
        "status_code": response.status_code,
    })

    return response


# ---------------------------------------------------------
# Middleware: CORS
# ---------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------
# API Documentation
# ---------------------------------------------------------
# Endpoint documentation is auto-generated from router docstrings.
# View API docs at: http://localhost:8585/docs (Swagger UI)
# Or at: http://localhost:8585/redoc (ReDoc)
#
# Routers organize endpoints by domain (SOLID principle):
# - auth_router: User registration, login, password reset
# - analysis_router: Resume + video analysis, evaluation
# - payment_router: Stripe integration, premium upgrade
# - rag_router: Vector search and document ingestion
# - health_router: Health checks and system status
#
# Legacy routers (mock_interview, analysis_history) are also included.
# ---------------------------------------------------------

