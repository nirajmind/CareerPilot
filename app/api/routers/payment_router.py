"""
Payment & Monetization Router Module

Handles Stripe integration, checkout sessions, and payment webhooks.
Follows Single Responsibility Principle - focuses only on payment operations.
"""

import json
from fastapi import APIRouter, HTTPException, Depends, status, Request

from app.utils.logger import setup_logger
from app.api.auth import get_current_user
from app.api.schemas import (
    CheckoutSessionRequest,
    CheckoutSessionResponse,
    WebhookResponse,
)
from app.api.app_config import get_config

logger = setup_logger()
config = get_config()

# Will be injected by the main app
quota_service = None
stripe_service = None
payment_service = None

router = APIRouter(prefix="/payments", tags=["Monetization"])


def init_payment_services(quota_svc, stripe_svc, payment_svc):
    """Initialize services - called from main app"""
    global quota_service, stripe_service, payment_service
    quota_service = quota_svc
    stripe_service = stripe_svc
    payment_service = payment_svc


@router.post("/checkout", response_model=CheckoutSessionResponse)
async def create_checkout_session(
    req: CheckoutSessionRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Create Stripe checkout session for premium upgrade.
    
    **Returns:** Stripe session ID and redirect URL
    
    **Errors:**
    - 400: User is already premium
    - 500: Payment service error
    """
    username = current_user["username"]
    
    # Check if user is already premium
    tier = await quota_service.get_user_tier(username)
    if tier == "premium":
        logger.warning(f"Checkout requested by premium user: {username}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is already premium",
        )

    logger.info(f"Checkout session requested for '{username}'")
    
    try:
        session = await payment_service.create_checkout_session(req.username, req.email)
        logger.info(f"Checkout session created: {session.get('session_id')}")
        return CheckoutSessionResponse(**session)
    except Exception as e:
        logger.error(f"Checkout session creation failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to create checkout session")


@router.post("/webhook", response_model=WebhookResponse)
async def stripe_webhook(request: Request):
    """
    Handle Stripe webhook events.
    
    **Events Handled:**
    - payment_intent.succeeded: Upgrade user to premium
    
    **Security:**
    - Verifies webhook signature (HMAC-SHA256)
    - Prevents replay attacks
    
    **Returns:** Confirmation of webhook processing
    """
    logger.info("Stripe webhook received")
    
    try:
        payload = await request.body()
        sig_header = request.headers.get("stripe-signature")

        success, message = await stripe_service.handle_payment_webhook(
            payload,
            sig_header
        )

        if not success:
            logger.error(f"Webhook processing failed: {message}")
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message)

        logger.info(f"Webhook processed successfully: {message}")
        return WebhookResponse(success=True, message=message)
        
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        raise HTTPException(status_code=500, detail="Webhook processing failed")


@router.get("/status/{username}")
async def get_payment_status(
    username: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get payment status for a user.
    
    **Returns:** Current tier and upgrade history
    
    **Note:** Users can only view their own payment status
    """
    # Security: Users can only view their own status
    if current_user["username"] != username:
        logger.warning(f"Unauthorized payment status access: {current_user['username']} → {username}")
        raise HTTPException(status_code=403, detail="Unauthorized")

    tier = await quota_service.get_user_tier(username)
    
    return {
        "username": username,
        "tier": tier,
        "upgraded": tier == "premium"
    }
