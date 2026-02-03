"""
Security services for account lockout and rate limiting.
Follows SOLID principle: Single Responsibility (each service has one job).
Uses Redis for fast, scalable state tracking.
"""

from redis import asyncio as aioredis
from app.utils.logger import setup_logger
from typing import Optional
from datetime import datetime, timedelta

logger = setup_logger()


class AccountLockoutService:
    """
    Manages account lockout mechanism using Redis.
    Tracks failed login attempts and locks accounts after threshold.
    
    Redis keys:
    - failed_attempts:{username} -> count of failed attempts
    - account_locked:{username} -> boolean flag (exists = locked)
    """
    
    def __init__(self, redis_client: aioredis.Redis, config):
        self.redis = redis_client
        self.max_failed_attempts = config.security.max_failed_attempts
        self.lockout_duration_hours = config.security.lockout_duration_hours
        self.lockout_ttl_seconds = self.lockout_duration_hours * 3600

    async def is_account_locked(self, username: str) -> bool:
        """Check if account is locked."""
        key = f"account_locked:{username}"
        locked = await self.redis.exists(key)
        return bool(locked)

    async def get_failed_attempts(self, username: str) -> int:
        """Get current failed attempt count."""
        key = f"failed_attempts:{username}"
        count = await self.redis.get(key)
        return int(count) if count else 0

    async def record_failed_attempt(self, username: str) -> None:
        """
        Increment failed attempt counter and lock account if threshold exceeded.
        Failed attempts expire after lockout_duration.
        """
        attempts_key = f"failed_attempts:{username}"
        current_attempts = await self.get_failed_attempts(username)
        new_attempts = current_attempts + 1

        # Increment counter with TTL
        await self.redis.setex(attempts_key, self.lockout_ttl_seconds, new_attempts)

        if new_attempts >= self.max_failed_attempts:
            lock_key = f"account_locked:{username}"
            await self.redis.setex(lock_key, self.lockout_ttl_seconds, "1")
            logger.warning(
                f"Account '{username}' locked after {new_attempts} failed attempts",
                extra={"username": username, "attempts": new_attempts}
            )
        else:
            logger.info(
                f"Failed login attempt for '{username}'",
                extra={"username": username, "attempts": new_attempts, "max": self.max_failed_attempts}
            )

    async def reset_failed_attempts(self, username: str) -> None:
        """
        Clear failed attempts counter on successful login.
        Also unlock account if it was locked.
        """
        attempts_key = f"failed_attempts:{username}"
        lock_key = f"account_locked:{username}"
        
        await self.redis.delete(attempts_key)
        await self.redis.delete(lock_key)
        
        logger.info(f"Failed attempts reset for user '{username}'", extra={"username": username})


class RateLimiterService:
    """
    Rate limiting service using token bucket algorithm via Redis.
    Limits requests per minute per user.
    
    Redis keys:
    - rate_limit:{username}:{minute} -> count of requests in this minute
    """
    
    def __init__(self, redis_client: aioredis.Redis, config):
        self.redis = redis_client
        self.enabled = config.security.rate_limit_enabled
        self.requests_per_window = config.security.rate_limit_requests
        self.window_minutes = config.security.rate_limit_window_minutes
        self.window_seconds = self.window_minutes * 60

    async def is_allowed(self, username: str) -> tuple[bool, dict]:
        """
        Check if request is allowed.
        Returns (allowed: bool, info: dict with remaining and reset_time)
        """
        if not self.enabled:
            return True, {"remaining": self.requests_per_window, "reset_at": None}

        # Use minute-based key (resets every minute)
        now = datetime.utcnow()
        current_minute = int(now.timestamp() // 60)
        key = f"rate_limit:{username}:{current_minute}"

        # Get current count
        current_count = await self.redis.get(key)
        current_count = int(current_count) if current_count else 0

        if current_count < self.requests_per_window:
            # Increment and set TTL
            new_count = await self.redis.incr(key)
            if new_count == 1:  # First request in this window
                await self.redis.expire(key, self.window_seconds)

            remaining = self.requests_per_window - new_count
            next_reset = now + timedelta(minutes=self.window_minutes)

            logger.debug(
                f"Rate limit check passed for '{username}'",
                extra={"username": username, "count": new_count, "remaining": remaining}
            )

            return True, {"remaining": remaining, "reset_at": next_reset.isoformat()}
        else:
            next_reset = now + timedelta(minutes=self.window_minutes)
            logger.warning(
                f"Rate limit exceeded for '{username}'",
                extra={"username": username, "limit": self.requests_per_window}
            )
            return False, {"remaining": 0, "reset_at": next_reset.isoformat()}


class CircuitBreakerState:
    """States for circuit breaker pattern."""
    CLOSED = "CLOSED"  # Normal operation
    OPEN = "OPEN"      # Failing, reject requests
    HALF_OPEN = "HALF_OPEN"  # Testing if service recovered


class CircuitBreakerService:
    """
    Circuit breaker pattern for external service calls (e.g., Gemini API).
    Prevents cascading failures by failing fast when service is down.
    
    Redis keys:
    - circuit_breaker:{service_name}:state -> CLOSED/OPEN/HALF_OPEN
    - circuit_breaker:{service_name}:failures -> count of consecutive failures
    """
    
    def __init__(self, redis_client: aioredis.Redis, service_name: str, config):
        self.redis = redis_client
        self.service_name = service_name
        self.failure_threshold = config.gemini.circuit_breaker_failure_threshold
        self.recovery_timeout = config.gemini.circuit_breaker_recovery_timeout_seconds

    async def is_healthy(self) -> bool:
        """Check if circuit is closed (service is operational)."""
        state = await self._get_state()
        return state == CircuitBreakerState.CLOSED

    async def record_success(self) -> None:
        """Record successful call; reset failure count."""
        await self.redis.delete(f"circuit_breaker:{self.service_name}:failures")
        await self.redis.delete(f"circuit_breaker:{self.service_name}:state")
        logger.debug(f"Circuit breaker '{self.service_name}': success recorded, resetting")

    async def record_failure(self) -> None:
        """Record failed call; open circuit if threshold exceeded."""
        failures_key = f"circuit_breaker:{self.service_name}:failures"
        current_failures = await self.redis.get(failures_key)
        current_failures = int(current_failures) if current_failures else 0
        new_failures = current_failures + 1

        await self.redis.setex(failures_key, self.recovery_timeout, new_failures)

        if new_failures >= self.failure_threshold:
            state_key = f"circuit_breaker:{self.service_name}:state"
            await self.redis.setex(state_key, self.recovery_timeout, CircuitBreakerState.OPEN)
            logger.error(
                f"Circuit breaker '{self.service_name}' OPENED after {new_failures} failures",
                extra={"service": self.service_name, "failures": new_failures}
            )
        else:
            logger.warning(
                f"Circuit breaker '{self.service_name}': failure recorded",
                extra={"service": self.service_name, "failures": new_failures}
            )

    async def _get_state(self) -> str:
        """Get current circuit state."""
        state_key = f"circuit_breaker:{self.service_name}:state"
        state = await self.redis.get(state_key)
        return state if state else CircuitBreakerState.CLOSED
