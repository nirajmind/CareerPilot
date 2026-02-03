"""
Router initialization and export module.

Central location for importing and exposing all routers.
Simplifies main app.py imports.
"""

from app.api.routers.auth_router import router as auth_router, init_auth_services
from app.api.routers.analysis_router import router as analysis_router, init_analysis_services
from app.api.routers.payment_router import router as payment_router, init_payment_services
from app.api.routers.rag_router import router as rag_router, init_rag_services
from app.api.routers.health_router import router as health_router, init_health_services


__all__ = [
    "auth_router",
    "analysis_router",
    "payment_router",
    "rag_router",
    "health_router",
    "init_auth_services",
    "init_analysis_services",
    "init_payment_services",
    "init_rag_services",
    "init_health_services",
]
