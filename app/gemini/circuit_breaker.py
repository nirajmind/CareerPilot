"""
Circuit breaker pattern implementation for resilient external service calls.
Prevents cascading failures when Gemini API or other services are unstable.
"""

from typing import Any, Callable, Coroutine
from functools import wraps
from app.utils.logger import setup_logger

logger = setup_logger()


class CircuitBreakerError(Exception):
    """Raised when circuit breaker is open (service down)."""
    pass


def circuit_breaker(service_name: str, circuit_breaker_service):
    """
    Decorator for circuit breaker pattern.
    
    Usage:
        @circuit_breaker("gemini", cb_service)
        async def call_gemini(...):
            ...
    
    Wraps function with circuit breaker state management.
    """
    def decorator(func: Callable[..., Coroutine]) -> Callable[..., Coroutine]:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Check if circuit is open
            if not await circuit_breaker_service.is_healthy():
                raise CircuitBreakerError(
                    f"Circuit breaker OPEN for service '{service_name}'. "
                    f"Service is unavailable. Please try again later."
                )

            try:
                result = await func(*args, **kwargs)
                # Success: reset failure count
                await circuit_breaker_service.record_success()
                return result

            except Exception as e:
                # Failure: increment failure count and potentially open circuit
                await circuit_breaker_service.record_failure()
                logger.error(
                    f"Call to '{service_name}' failed: {str(e)}",
                    extra={"service": service_name, "error": str(e)}
                )
                raise

        return wrapper
    return decorator
