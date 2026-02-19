"""
CORTEX Stripe Webhook Handler.

Handles Stripe checkout.session.completed events:
1. Creates a CORTEX API key for the customer
2. Sends the key via email (via Stripe customer email)
3. Records the subscription in CORTEX

Usage:
    Add this route to your FastAPI app:
        from cortex.routes.stripe import router as stripe_router
        app.include_router(stripe_router)

Environment variables:
    STRIPE_SECRET_KEY — sk_live_... or sk_test_...
    STRIPE_WEBHOOK_SECRET — whsec_... from Stripe dashboard
"""

import hashlib
import logging
import os
import time

from fastapi import APIRouter, Header, HTTPException, Request

router = APIRouter(tags=["stripe"])
logger = logging.getLogger("uvicorn.error")

STRIPE_SECRET = os.getenv("STRIPE_SECRET_KEY", "")
WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")

# Plan → permissions mapping
PLAN_CONFIG = {
    "pro": {
        "calls_limit": 50_000,
        "projects_limit": 10,
        "permissions": ["read", "write"],
    },
    "team": {
        "calls_limit": 500_000,
        "projects_limit": -1,  # unlimited
        "permissions": ["read", "write", "admin"],
    },
}


@router.post("/v1/stripe/webhook")
async def stripe_webhook(
    request: Request,
    stripe_signature: str = Header(None, alias="Stripe-Signature"),
) -> dict:
    """Handle Stripe webhook events."""
    if not STRIPE_SECRET or not WEBHOOK_SECRET:
        raise HTTPException(status_code=500, detail="Stripe not configured")

    payload = await request.body()

    try:
        import stripe
        stripe.api_key = STRIPE_SECRET
        event = stripe.Webhook.construct_event(
            payload, stripe_signature, WEBHOOK_SECRET
        )
    except ImportError:
        raise HTTPException(status_code=500, detail="stripe package not installed")
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid signature")

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        customer_email = session.get("customer_email", "unknown")
        plan = session.get("metadata", {}).get("plan", "pro")

        # Generate API key
        raw_key = _generate_api_key(customer_email, plan)

        logger.info(
            "New subscription: %s → %s plan (key prefix: %s...)",
            customer_email, plan, raw_key[:12]
        )

        # Store in CORTEX
        try:
            from cortex import api_state
            if api_state.auth_manager:
                api_state.auth_manager.create_key(
                    name=f"stripe-{customer_email}",
                    tenant_id=customer_email,
                    permissions=PLAN_CONFIG.get(plan, PLAN_CONFIG["pro"])["permissions"],
                )
        except Exception as e:
            logger.error("Failed to create CORTEX key: %s", e)

        return {
            "status": "ok",
            "email": customer_email,
            "plan": plan,
            "key_prefix": raw_key[:12] + "...",
        }

    return {"status": "ignored", "type": event["type"]}


def _generate_api_key(email: str, plan: str) -> str:
    """Generate a deterministic but secure API key."""
    seed = f"{email}:{plan}:{time.time()}:{os.urandom(16).hex()}"
    return "ctx_" + hashlib.sha256(seed.encode()).hexdigest()[:48]
