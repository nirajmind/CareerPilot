"""
Health Check & System Router Module

Handles health checks and basic system endpoints.
Follows Single Responsibility Principle - focuses only on system checks.
"""

from fastapi import APIRouter, Depends
from app.api.auth import require_role
from app.utils.logger import setup_logger
from app.utils.mongo_handler import mongo_handler

logger = setup_logger()

# Global service references (injected)
redis_client = None

router = APIRouter(tags=["System"])


def init_health_services(redis):
    """Initialize services - called from main app"""
    global redis_client
    redis_client = redis


@router.get("/health")
async def health_check():
    """
    Public health check endpoint.
    
    **Returns:** Service status
    
    **Used for:** Load balancing, monitoring, Kubernetes liveness probes.
    **Note:** Publicly accessible to allow infrastructure automated checks.
    """
    return {"status": "ok", "service": "career-pilot-api"}


@router.get("/health/secure", dependencies=[Depends(require_role("admin"))])
async def secure_health_check():
    """
    Protected detailed health check (Admin only).
    
    **Checks:**
    - Service status
    - MongoDB connection
    - Redis connection
    
    **Security:** Requires 'admin' role.
    """
    # Check Mongo
    mongo_status = "down"
    try:
        if mongo_handler.client:
            # simple command to check connection
            mongo_handler.client.admin.command('ismaster')
            mongo_status = "ok"
    except Exception as e:
        logger.error(f"Health check - Mongo error: {e}")
        mongo_status = "error"

    # Check Redis
    redis_status = "down"
    try:
        if redis_client and await redis_client.ping():
            redis_status = "ok"
    except Exception as e:
        logger.error(f"Health check - Redis error: {e}")
        redis_status = "error"
    
    return {
        "status": "operational",
        "service": "CareerPilot API",
        "components": {
            "mongodb": mongo_status,
            "redis": redis_status
        }
    }


@router.get("/")
async def root():
    """Root endpoint - returns API info."""
    return {
        "service": "CareerPilot API",
        "version": "1.0.0",
        "status": "operational"
    }
