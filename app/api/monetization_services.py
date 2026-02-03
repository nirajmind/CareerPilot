"""
Monetization services: usage quotas and payment processing.
Follows SOLID principle: Single Responsibility.
"""

from datetime import datetime
from typing import Tuple
from app.utils.logger import setup_logger
import hashlib
import hmac
import stripe
import json

logger = setup_logger()


class QuotaService:
    """
    Manages daily usage quotas for free and premium users.
    Quotas reset daily at UTC midnight.
    
    Redis keys:
    - user_usage:{date}:{username} -> count of analyses performed
    - user_tier:{username} -> 'free' or 'premium'
    """
    
    def __init__(self, redis_client, config):
        self.redis = redis_client
        self.config = config
        self.free_limit = config.quota.free_tier_daily_limit
        self.premium_limit = config.quota.premium_tier_daily_limit

    async def get_user_tier(self, username: str) -> str:
        """Get user tier ('free' or 'premium'). Default: 'free'."""
        tier = await self.redis.get(f"user_tier:{username}")
        return tier if tier else "free"

    async def set_user_tier(self, username: str, tier: str) -> None:
        """Set user tier (called when payment is processed)."""
        if tier not in ["free", "premium"]:
            raise ValueError("Tier must be 'free' or 'premium'")
        
        # No expiry for tier—persists until manually changed
        await self.redis.set(f"user_tier:{username}", tier)
        logger.info(
            f"User tier updated: '{username}' -> {tier}",
            extra={"username": username, "tier": tier}
        )

    async def get_daily_usage(self, username: str) -> int:
        """Get today's usage count."""
        today = datetime.utcnow().strftime("%Y-%m-%d")
        key = f"user_usage:{today}:{username}"
        usage = await self.redis.get(key)
        return int(usage) if usage else 0

    async def get_quota_limit(self, username: str) -> int:
        """Get daily quota limit for user based on tier."""
        tier = await self.get_user_tier(username)
        return self.premium_limit if tier == "premium" else self.free_limit

    async def can_perform_analysis(self, username: str) -> Tuple[bool, dict]:
        """
        Check if user can perform analysis (within quota).
        Returns (allowed: bool, info: dict with usage/limit/remaining)
        """
        usage = await self.get_daily_usage(username)
        limit = await self.quota_limit(username)
        allowed = usage < limit
        remaining = limit - usage

        info = {
            "usage": usage,
            "limit": limit,
            "remaining": remaining,
            "tier": await self.get_user_tier(username),
            "reset_at": self._get_reset_time(),
        }

        if not allowed:
            logger.warning(
                f"Quota exceeded for '{username}'",
                extra={"username": username, "usage": usage, "limit": limit}
            )

        return allowed, info

    async def increment_usage(self, username: str) -> int:
        """Increment daily usage counter. Returns new usage count."""
        today = datetime.utcnow().strftime("%Y-%m-%d")
        key = f"user_usage:{today}:{username}"
        
        # Increment and set TTL to 24 hours (resets daily)
        new_usage = await self.redis.incr(key)
        await self.redis.expire(key, 86400)  # 24 hours
        
        logger.debug(
            f"Usage incremented for '{username}'",
            extra={"username": username, "usage": new_usage}
        )
        return new_usage

    async def quota_limit(self, username: str) -> int:
        """Alias for get_quota_limit for backwards compatibility."""
        return await self.get_quota_limit(username)

    def _get_reset_time(self) -> str:
        """Get ISO timestamp for next UTC midnight."""
        now = datetime.utcnow()
        next_midnight = datetime(now.year, now.month, now.day, 0, 0, 0) + \
                       __import__('datetime').timedelta(days=1)
        return next_midnight.isoformat() + "Z"


class StripeService:
    """
    Handles Stripe webhook events (payment_intent.succeeded).
    Upgrades user to premium tier on successful payment.
    
    Payment flow:
    1. User clicks "Upgrade to Premium" -> Stripe checkout
    2. User completes payment -> Stripe webhook to POST /payments/webhook
    3. Webhook validates signature and updates user tier
    """
    
    def __init__(self, quota_service: QuotaService, mongo_handler, config):
        self.quota_service = quota_service
        self.mongo = mongo_handler
        self.config = config
        self.webhook_secret = config.stripe.stripe_webhook_secret

    async def handle_payment_webhook(self, payload: bytes, stripe_signature: str) -> Tuple[bool, str]:
        """
        Validate Stripe webhook signature and handle payment event.
        Uses stripe.Webhook.construct_event for secure verification.
        
        Returns (success: bool, message: str)
        """
        try:
            # Construct event using Stripe library
            event = stripe.Webhook.construct_event(
                payload, stripe_signature, self.webhook_secret
            )

            if event.get("type") == "checkout.session.completed":
                 # Extract session data
                 session = event["data"]["object"]
                 
                 # Extract client_reference_id (username)
                 # Note: In checkout creation, we set client_reference_id=username
                 username = session.get("client_reference_id")
                 
                 if not username:
                     logger.error("Stripe webhook missing client_reference_id")
                     return False, "Missing username (client_reference_id)"

                 # Validate payment status
                 if session.get("payment_status") != "paid":
                     logger.warning(f"Payment not paid: {session.get('id')}")
                     return True, "Payment status not paid"

                 # Upgrade user to premium
                 await self.quota_service.set_user_tier(username, "premium")
                 
                 # Update MongoDB user doc
                 await self.mongo.set_user_premium(username)

                 logger.info(
                     f"User upgraded to premium via Stripe: '{username}'",
                     extra={"username": username}
                 )
                 return True, f"User '{username}' upgraded to premium"

            elif event.get("type") == "payment_intent.succeeded":
                # Fallback if using PaymentIntents directly (less common for Checkout)
                 username = event.get("data", {}).get("object", {}).get("metadata", {}).get("username")
                 if username:
                     await self.quota_service.set_user_tier(username, "premium")
                     await self.mongo.set_user_premium(username)
                     return True, f"User '{username}' upgraded to premium"

            logger.debug(f"Ignoring Stripe event type: {event.get('type')}")
            return True, "Event ignored"

        except stripe.error.SignatureVerificationError as e:
            logger.error(f"Invalid Stripe webhook signature: {str(e)}")
            return False, "Invalid signature"
        except Exception as e:
            logger.error(f"Stripe webhook handling error: {str(e)}", extra={"error": str(e)})
            return False, str(e)

    def _verify_webhook_signature(self, payload: str, stripe_signature: str) -> bool:
        """Deprecated: Use stripe.Webhook.construct_event instead."""
        pass


class PaymentService:
    """
    Orchestrates payment operations (checkout session creation, etc).
    Thin wrapper around Stripe API for business logic.
    Note: In production, install stripe SDK; for MVP can skip session creation.
    """
    
    def __init__(self, config):
        self.config = config
        self.stripe_key = config.stripe.stripe_api_key
        stripe.api_key = self.stripe_key

    async def create_checkout_session(self, username: str, email: str) -> dict:
        """
        Create Stripe checkout session for premium upgrade.
        Returns session data with redirect_url.
        """
        logger.info(
            f"Checkout session requested for '{username}'",
            extra={"username": username, "email": email}
        )
        
        try:
            # Create session using Stripe SDK
            session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=[{
                    'price': self.config.stripe.stripe_price_id_premium,
                    'quantity': 1,
                }],
                mode='payment',
                success_url=f"https://careerpilot.chickenkiller.com/payment-success?session_id={{CHECKOUT_SESSION_ID}}",
                cancel_url=f"https://careerpilot.chickenkiller.com/payment-cancel",
                client_reference_id=username,
                customer_email=email,
                metadata={
                    "username": username,
                    "plan": "premium"
                }
            )

            return {
                "session_id": session.id,
                "redirect_url": session.url,
                "status": "created",
            }

        except stripe.error.StripeError as e:
            logger.error(f"Stripe API error: {str(e)}")
            raise ValueError(f"Stripe error: {str(e)}")
        except Exception as e:
            logger.error(f"Failed to create checkout session: {str(e)}")
            raise ValueError("Failed to create checkout session")
