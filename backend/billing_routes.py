"""
CultureShield AI - Billing API Routes
"""

from fastapi import APIRouter, HTTPException, Depends, Request, BackgroundTasks, Response
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone, timedelta
import uuid
import hmac
import hashlib
import json
import csv
from io import StringIO

from billing import (
    PRICING_PLANS,
    generate_reference,
    calculate_period_dates,
    convert_currency,
    log_billing_event,
    send_billing_notification,
    paystack_request,
    initialize_transaction,
    verify_transaction,
    create_paystack_customer,
    create_paystack_plan,
    create_subscription,
    disable_subscription,
    refund_transaction,
    check_subscription_access,
    get_usage_this_period,
    calculate_churn_risk,
    get_plan_recommendation,
    trigger_retention_action,
    process_dunning,
    retry_failed_payment,
    validate_coupon,
    apply_coupon_discount,
    calculate_billing_metrics,
    record_usage,
    SubscriptionModel,
    InvoiceModel,
    PaymentMethodModel,
    BillingEventModel,
    CouponModel,
    CustomerBillingInfo,
    BillingDashboardStats,
    BillingEventType,
    SubscriptionStatus
)

import os
import logging

logger = logging.getLogger(__name__)

# Router
billing_router = APIRouter(prefix="/api/billing", tags=["billing"])
security = HTTPBearer()

# Get configuration
PAYSTACK_SECRET_KEY = os.environ.get('PAYSTACK_SECRET_KEY')

# ===================== DEPENDENCY INJECTION =====================

def get_db():
    from server import db
    return db

async def get_current_company(credentials: HTTPAuthorizationCredentials = Depends(security)):
    from server import get_current_company as server_get_company
    return await server_get_company(credentials)

# ===================== REQUEST MODELS =====================

class InitializePaymentRequest(BaseModel):
    plan_id: str
    callback_url: str
    coupon_code: Optional[str] = None
    currency: str = "NGN"

class ChangePlanRequest(BaseModel):
    new_plan_id: str
    prorate: bool = True

class CancelSubscriptionRequest(BaseModel):
    cancel_immediately: bool = False
    reason: Optional[str] = None

class CreateCouponRequest(BaseModel):
    code: str
    discount_type: str  # "percentage" or "fixed"
    discount_value: float
    max_uses: Optional[int] = None
    valid_days: int = 30
    applicable_plans: List[str] = []
    is_recurring: bool = False

class RefundRequest(BaseModel):
    invoice_id: str
    amount: Optional[float] = None  # None = full refund
    reason: str

class ManualInvoiceRequest(BaseModel):
    company_id: str
    amount: float
    description: str
    currency: str = "NGN"

class RetryPaymentRequest(BaseModel):
    company_id: str

class EmailActivityItem(BaseModel):
    id: str
    recipient_email: str
    subject: str
    email_type: str
    status: str
    provider: str
    provider_message: Optional[str] = None
    provider_id: Optional[str] = None
    company_id: Optional[str] = None
    metadata: Dict[str, Any] = {}
    created_at: str

class EmailActivityResponse(BaseModel):
    items: List[EmailActivityItem]
    summary: Dict[str, int]

# ===================== PRICING ENDPOINTS =====================

@billing_router.get("/plans")
async def get_pricing_plans(currency: str = "USD"):
    """Get all available pricing plans"""
    plans = []
    for plan_id, plan in PRICING_PLANS.items():
        plan_data = dict(plan)
        if currency == "NGN":
            plan_data["display_price"] = plan["price_ngn"]
            plan_data["currency"] = "NGN"
        else:
            plan_data["display_price"] = plan["price_usd"]
            plan_data["currency"] = "USD"
        plans.append(plan_data)
    return plans

@billing_router.get("/plans/{plan_id}")
async def get_plan_details(plan_id: str, currency: str = "USD"):
    """Get specific plan details"""
    plan = PRICING_PLANS.get(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    
    plan_data = dict(plan)
    if currency == "NGN":
        plan_data["display_price"] = plan["price_ngn"]
        plan_data["currency"] = "NGN"
    else:
        plan_data["display_price"] = plan["price_usd"]
        plan_data["currency"] = "USD"
    return plan_data

# ===================== CHECKOUT ENDPOINTS =====================

@billing_router.post("/checkout/initialize")
async def initialize_checkout(
    request: InitializePaymentRequest,
    company: dict = Depends(get_current_company)
):
    """Initialize payment checkout with Paystack"""
    db = get_db()
    
    plan = PRICING_PLANS.get(request.plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    
    if plan["price_usd"] == 0:
        # Free plan - just create subscription
        subscription = await create_free_subscription(company["id"], request.plan_id, db)
        return {"status": "success", "subscription": subscription, "is_free": True}
    
    # Calculate amount
    amount = plan["price_ngn"]
    
    # Apply coupon if provided
    if request.coupon_code:
        coupon_result = await validate_coupon(request.coupon_code, request.plan_id, db)
        if coupon_result["valid"]:
            amount = await apply_coupon_discount(amount, coupon_result["coupon"])
    
    amount_kobo = int(amount * 100)
    reference = generate_reference()
    
    # Initialize Paystack transaction
    result = await initialize_transaction(
        email=company["email"],
        amount_kobo=amount_kobo,
        reference=reference,
        callback_url=request.callback_url,
        metadata={
            "company_id": company["id"],
            "plan_id": request.plan_id,
            "coupon_code": request.coupon_code,
            "is_subscription": plan["interval"] == "monthly"
        }
    )
    
    if not result.get("status"):
        raise HTTPException(status_code=400, detail=result.get("message", "Payment initialization failed"))
    
    # Store pending transaction
    pending_tx = {
        "id": str(uuid.uuid4()),
        "company_id": company["id"],
        "reference": reference,
        "plan_id": request.plan_id,
        "amount": amount,
        "currency": "NGN",
        "coupon_code": request.coupon_code,
        "status": "pending",
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.pending_transactions.insert_one(pending_tx)

    await send_billing_notification("abandoned_cart_scheduled", company["id"], {
        "reference": reference,
        "plan_id": request.plan_id,
        "amount": amount,
    }, db)
    
    return {
        "authorization_url": result["data"]["authorization_url"],
        "reference": result["data"]["reference"],
        "access_code": result["data"]["access_code"],
        "amount": amount,
        "currency": "NGN"
    }

@billing_router.post("/checkout/subscribe")
async def initialize_subscription_checkout(
    request: InitializePaymentRequest,
    company: dict = Depends(get_current_company)
):
    """Initialize a hosted checkout for recurring monthly plans."""
    plan = PRICING_PLANS.get(request.plan_id)
    if not plan or plan.get("interval") != "monthly":
        raise HTTPException(status_code=400, detail="This endpoint only supports recurring plans")
    return await initialize_checkout(request, company)

@billing_router.post("/checkout/audit")
async def initialize_one_time_audit_checkout(
    request: InitializePaymentRequest,
    company: dict = Depends(get_current_company)
):
    """Initialize a hosted checkout for a one-time audit purchase."""
    plan = PRICING_PLANS.get(request.plan_id)
    if not plan or plan.get("interval") != "one_time":
        raise HTTPException(status_code=400, detail="This endpoint only supports one-time audit purchases")
    return await initialize_checkout(request, company)

@billing_router.get("/checkout/verify/{reference}")
async def verify_checkout(
    reference: str,
    company: dict = Depends(get_current_company)
):
    """Verify payment after Paystack redirect"""
    db = get_db()
    
    # Verify with Paystack
    result = await verify_transaction(reference)
    
    if not result.get("status"):
        raise HTTPException(status_code=400, detail="Verification failed")
    
    tx_data = result.get("data", {})
    
    if tx_data.get("status") != "success":
        return {"status": "failed", "message": "Payment was not successful"}
    
    # Get pending transaction
    pending = await db.pending_transactions.find_one(
        {"reference": reference},
        {"_id": 0}
    )
    
    if not pending:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    plan_id = pending.get("plan_id")
    plan = PRICING_PLANS.get(plan_id)
    
    # Create or update subscription
    if plan["interval"] == "monthly":
        subscription = await create_subscription_from_payment(
            company_id=company["id"],
            plan_id=plan_id,
            payment_data=tx_data,
            coupon_code=pending.get("coupon_code"),
            db=db
        )
    else:
        # One-time purchase
        subscription = await create_one_time_purchase(
            company_id=company["id"],
            plan_id=plan_id,
            payment_data=tx_data,
            db=db
        )
    
    # Create invoice
    invoice = await create_invoice_from_payment(
        company_id=company["id"],
        payment_data=tx_data,
        subscription_id=subscription.get("id"),
        db=db
    )
    
    # Store payment method if authorization exists
    if tx_data.get("authorization"):
        await store_payment_method(company["id"], tx_data["authorization"], db)
    
    # Update pending transaction
    await db.pending_transactions.update_one(
        {"reference": reference},
        {"$set": {"status": "completed", "completed_at": datetime.now(timezone.utc).isoformat()}}
    )
    
    # Log event
    await log_billing_event(db, BillingEventType.PAYMENT_SUCCESS, tx_data, company["id"], reference)
    
    # Send notification
    await send_billing_notification("payment_success", company["id"], {
        "amount": tx_data.get("amount", 0) / 100,
        "plan": plan["name"]
    }, db)
    
    return {
        "status": "success",
        "subscription": subscription,
        "invoice": invoice
    }

# ===================== SUBSCRIPTION MANAGEMENT =====================

@billing_router.get("/subscription")
async def get_current_subscription(company: dict = Depends(get_current_company)):
    """Get current company subscription"""
    db = get_db()
    
    subscription = await db.subscriptions.find_one(
        {"company_id": company["id"]},
        {"_id": 0}
    )
    
    if not subscription:
        return {"subscription": None, "plan": PRICING_PLANS["free"]}
    
    plan = PRICING_PLANS.get(subscription.get("plan_id", "free"), PRICING_PLANS["free"])
    
    return {
        "subscription": subscription,
        "plan": plan
    }

@billing_router.post("/subscription/change-plan")
async def change_subscription_plan(
    request: ChangePlanRequest,
    company: dict = Depends(get_current_company)
):
    """Change subscription plan (upgrade/downgrade)"""
    db = get_db()
    
    new_plan = PRICING_PLANS.get(request.new_plan_id)
    if not new_plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    
    subscription = await db.subscriptions.find_one(
        {"company_id": company["id"]},
        {"_id": 0}
    )
    
    if not subscription:
        raise HTTPException(status_code=404, detail="No active subscription")
    
    old_plan_id = subscription.get("plan_id")
    old_plan = PRICING_PLANS.get(old_plan_id, {})
    
    is_upgrade = new_plan["price_usd"] > old_plan.get("price_usd", 0)
    
    # Calculate proration if applicable
    proration_amount = 0
    if request.prorate and subscription.get("status") == "active":
        period_start = datetime.fromisoformat(subscription["current_period_start"].replace("Z", "+00:00"))
        period_end = datetime.fromisoformat(subscription["current_period_end"].replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        
        total_days = (period_end - period_start).days
        remaining_days = (period_end - now).days
        
        if total_days > 0:
            old_daily_rate = old_plan.get("price_usd", 0) / total_days
            new_daily_rate = new_plan["price_usd"] / total_days
            
            # Credit for unused time on old plan
            old_credit = old_daily_rate * remaining_days
            # Cost for remaining time on new plan
            new_cost = new_daily_rate * remaining_days
            
            proration_amount = new_cost - old_credit
    
    # Update subscription
    await db.subscriptions.update_one(
        {"company_id": company["id"]},
        {
            "$set": {
                "plan_id": request.new_plan_id,
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "metadata.previous_plan": old_plan_id,
                "metadata.proration_amount": proration_amount
            }
        }
    )
    
    # Log event
    event_type = BillingEventType.PLAN_UPGRADED if is_upgrade else BillingEventType.PLAN_DOWNGRADED
    await log_billing_event(db, event_type, {
        "old_plan": old_plan_id,
        "new_plan": request.new_plan_id,
        "proration": proration_amount
    }, company["id"])
    
    # Send notification
    await send_billing_notification(
        "plan_changed",
        company["id"],
        {"old_plan": old_plan.get("name"), "new_plan": new_plan["name"]},
        db
    )
    
    return {
        "status": "success",
        "message": f"Plan changed to {new_plan['name']}",
        "proration_amount": proration_amount,
        "is_upgrade": is_upgrade
    }

@billing_router.post("/subscription/cancel")
async def cancel_subscription(
    request: CancelSubscriptionRequest,
    company: dict = Depends(get_current_company)
):
    """Cancel subscription"""
    db = get_db()
    
    subscription = await db.subscriptions.find_one(
        {"company_id": company["id"]},
        {"_id": 0}
    )
    
    if not subscription:
        raise HTTPException(status_code=404, detail="No active subscription")
    
    if request.cancel_immediately:
        # Immediate cancellation
        await db.subscriptions.update_one(
            {"company_id": company["id"]},
            {
                "$set": {
                    "status": "cancelled",
                    "cancelled_at": datetime.now(timezone.utc).isoformat(),
                    "cancellation_reason": request.reason,
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }
            }
        )
        
        # Disable Paystack subscription if exists
        if subscription.get("paystack_subscription_code") and subscription.get("paystack_email_token"):
            await disable_subscription(
                subscription["paystack_subscription_code"],
                subscription["paystack_email_token"]
            )
    else:
        # Cancel at period end
        await db.subscriptions.update_one(
            {"company_id": company["id"]},
            {
                "$set": {
                    "cancel_at_period_end": True,
                    "cancellation_reason": request.reason,
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }
            }
        )
    
    # Log event
    await log_billing_event(db, BillingEventType.SUBSCRIPTION_CANCELLED, {
        "immediate": request.cancel_immediately,
        "reason": request.reason
    }, company["id"])
    
    # Send notification
    await send_billing_notification("subscription_cancelled", company["id"], {
        "immediate": request.cancel_immediately
    }, db)
    
    return {
        "status": "success",
        "message": "Subscription cancelled" if request.cancel_immediately else "Subscription will cancel at period end"
    }

@billing_router.post("/subscription/resume")
async def resume_subscription(company: dict = Depends(get_current_company)):
    """Resume a cancelled subscription (if cancel_at_period_end)"""
    db = get_db()
    
    subscription = await db.subscriptions.find_one(
        {"company_id": company["id"]},
        {"_id": 0}
    )
    
    if not subscription:
        raise HTTPException(status_code=404, detail="No subscription found")
    
    if not subscription.get("cancel_at_period_end"):
        raise HTTPException(status_code=400, detail="Subscription is not scheduled for cancellation")
    
    await db.subscriptions.update_one(
        {"company_id": company["id"]},
        {
            "$set": {
                "cancel_at_period_end": False,
                "updated_at": datetime.now(timezone.utc).isoformat()
            },
            "$unset": {"cancellation_reason": ""}
        }
    )
    
    await send_billing_notification("subscription_resumed", company["id"], {}, db)
    
    return {"status": "success", "message": "Subscription resumed"}

# ===================== INVOICES =====================

@billing_router.get("/invoices")
async def get_invoices(
    limit: int = 20,
    company: dict = Depends(get_current_company)
):
    """Get company invoices"""
    db = get_db()
    
    invoices = await db.invoices.find(
        {"company_id": company["id"]},
        {"_id": 0}
    ).sort("created_at", -1).limit(limit).to_list(limit)
    
    return {"invoices": invoices}

@billing_router.get("/invoices/{invoice_id}")
async def get_invoice(
    invoice_id: str,
    company: dict = Depends(get_current_company)
):
    """Get specific invoice"""
    db = get_db()
    
    invoice = await db.invoices.find_one(
        {"id": invoice_id, "company_id": company["id"]},
        {"_id": 0}
    )
    
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    return invoice

# ===================== PAYMENT METHODS =====================

@billing_router.get("/payment-methods")
async def get_payment_methods(company: dict = Depends(get_current_company)):
    """Get saved payment methods"""
    db = get_db()
    
    methods = await db.payment_methods.find(
        {"company_id": company["id"]},
        {"_id": 0}
    ).to_list(10)
    
    return {"payment_methods": methods}

@billing_router.delete("/payment-methods/{method_id}")
async def delete_payment_method(
    method_id: str,
    company: dict = Depends(get_current_company)
):
    """Delete a payment method"""
    db = get_db()
    
    result = await db.payment_methods.delete_one({
        "id": method_id,
        "company_id": company["id"]
    })
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Payment method not found")
    
    return {"status": "success", "message": "Payment method deleted"}

# ===================== BILLING INFO =====================

@billing_router.get("/info")
async def get_billing_info(company: dict = Depends(get_current_company)):
    """Get complete billing information for customer"""
    db = get_db()
    
    subscription = await db.subscriptions.find_one(
        {"company_id": company["id"]},
        {"_id": 0}
    )
    
    invoices = await db.invoices.find(
        {"company_id": company["id"]},
        {"_id": 0}
    ).sort("created_at", -1).limit(10).to_list(10)
    
    payment_methods = await db.payment_methods.find(
        {"company_id": company["id"]},
        {"_id": 0}
    ).to_list(5)
    
    usage = await get_usage_this_period(company["id"], db)
    
    plan_id = subscription.get("plan_id", "free") if subscription else "free"
    plan = PRICING_PLANS.get(plan_id, PRICING_PLANS["free"])
    
    # Get plan recommendation
    recommendation = await get_plan_recommendation(company["id"], db)
    
    next_billing = subscription.get("current_period_end") if subscription else None
    
    return CustomerBillingInfo(
        subscription=SubscriptionModel(**subscription) if subscription else None,
        invoices=[InvoiceModel(**inv) for inv in invoices],
        payment_methods=[PaymentMethodModel(**pm) for pm in payment_methods],
        usage_this_period=usage,
        next_billing_date=next_billing,
        plan_details=plan,
        recommended_plan=recommendation.get("recommended_plan"),
        upgrade_savings=recommendation.get("projected_monthly_savings")
    )

@billing_router.get("/portal")
async def get_customer_portal(company: dict = Depends(get_current_company)):
    """Return the in-app billing portal location for the current customer."""
    return {
        "portal_url": "/billing?view=portal",
        "status": "available",
        "message": "Use the in-app billing portal to manage invoices, plans, and payment methods.",
        "company_id": company["id"],
    }

# ===================== COUPONS =====================

@billing_router.post("/coupons/validate")
async def validate_coupon_code(
    code: str,
    plan_id: str,
    company: dict = Depends(get_current_company)
):
    """Validate a coupon code"""
    db = get_db()
    result = await validate_coupon(code, plan_id, db)
    
    if not result["valid"]:
        raise HTTPException(status_code=400, detail=result["error"])
    
    return {
        "valid": True,
        "discount_type": result["discount_type"],
        "discount_value": result["discount_value"]
    }

# ===================== WEBHOOKS =====================

@billing_router.post("/webhooks/paystack")
async def paystack_webhook(request: Request, background_tasks: BackgroundTasks):
    """Handle Paystack webhooks"""
    db = get_db()
    
    # Get signature
    signature = request.headers.get("x-paystack-signature", "")
    body = await request.body()
    
    # Verify signature
    if PAYSTACK_SECRET_KEY:
        computed_signature = hmac.new(
            PAYSTACK_SECRET_KEY.encode('utf-8'),
            body,
            hashlib.sha512
        ).hexdigest()
        
        if not hmac.compare_digest(computed_signature, signature):
            logger.warning("Invalid webhook signature")
            # Log failed webhook
            await db.webhook_logs.insert_one({
                "id": str(uuid.uuid4()),
                "provider": "paystack",
                "signature_valid": False,
                "body": body.decode('utf-8')[:1000],
                "created_at": datetime.now(timezone.utc).isoformat()
            })
            raise HTTPException(status_code=401, detail="Invalid signature")
    
    event = await request.json()
    event_type = event.get("event")
    data = event.get("data", {})
    
    # Log webhook
    webhook_log = {
        "id": str(uuid.uuid4()),
        "provider": "paystack",
        "event_type": event_type,
        "signature_valid": True,
        "payload": event,
        "processed": False,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.webhook_logs.insert_one(webhook_log)
    
    # Process webhook in background
    background_tasks.add_task(process_paystack_webhook, event_type, data, webhook_log["id"], db)
    
    return {"status": "ok"}

async def process_paystack_webhook(event_type: str, data: dict, log_id: str, db):
    """Process Paystack webhook event"""
    try:
        company_id = data.get("metadata", {}).get("company_id")
        
        if event_type == "charge.success":
            # Payment successful
            reference = data.get("reference")
            await log_billing_event(db, BillingEventType.PAYMENT_SUCCESS, data, company_id, reference)
            
        elif event_type == "invoice.create":
            # Invoice created
            await log_billing_event(db, BillingEventType.INVOICE_CREATED, data, company_id)
            
        elif event_type == "invoice.payment_failed":
            # Payment failed
            if company_id:
                await db.subscriptions.update_one(
                    {"company_id": company_id},
                    {"$set": {"status": "past_due", "updated_at": datetime.now(timezone.utc).isoformat()}}
                )
                await log_billing_event(db, BillingEventType.PAYMENT_FAILED, data, company_id)
                await send_billing_notification("payment_failed", company_id, data, db)
                
        elif event_type == "subscription.create":
            # Subscription created
            await log_billing_event(db, BillingEventType.SUBSCRIPTION_CREATED, data, company_id)
            
        elif event_type == "subscription.disable":
            # Subscription disabled/cancelled
            if company_id:
                await db.subscriptions.update_one(
                    {"company_id": company_id},
                    {"$set": {"status": "cancelled", "updated_at": datetime.now(timezone.utc).isoformat()}}
                )
                await log_billing_event(db, BillingEventType.SUBSCRIPTION_CANCELLED, data, company_id)
                
        elif event_type == "refund.processed":
            # Refund processed
            await log_billing_event(db, BillingEventType.REFUND_PROCESSED, data, company_id)
        
        # Mark webhook as processed
        await db.webhook_logs.update_one(
            {"id": log_id},
            {"$set": {"processed": True, "processed_at": datetime.now(timezone.utc).isoformat()}}
        )
        
        logger.info(f"Webhook processed: {event_type}")
        
    except Exception as e:
        logger.error(f"Webhook processing error: {e}")
        await db.webhook_logs.update_one(
            {"id": log_id},
            {"$set": {"error": str(e)}}
        )

# ===================== ADMIN ENDPOINTS =====================

@billing_router.get("/admin/dashboard")
async def get_admin_billing_dashboard(company: dict = Depends(get_current_company)):
    """Get billing intelligence scoped to the current company."""
    db = get_db()

    metrics = await calculate_billing_metrics(db, company_id=company["id"])
    return metrics

@billing_router.get("/admin/email-activity", response_model=EmailActivityResponse)
async def get_admin_email_activity(limit: int = 25, company: dict = Depends(get_current_company)):
    """Get recent email activity for the current company admin."""
    db = get_db()
    safe_limit = min(max(limit, 1), 100)

    items = await db.email_events.find(
        {"company_id": company["id"]},
        {"_id": 0}
    ).sort("created_at", -1).to_list(safe_limit)

    all_company_events = await db.email_events.find(
        {"company_id": company["id"]},
        {"_id": 0, "status": 1}
    ).to_list(1000)

    summary = {
        "total": len(all_company_events),
        "sent": sum(1 for item in all_company_events if item.get("status") == "sent"),
        "failed": sum(1 for item in all_company_events if item.get("status") == "failed"),
        "skipped": sum(1 for item in all_company_events if item.get("status") == "skipped"),
    }

    return EmailActivityResponse(
        items=[EmailActivityItem(**item) for item in items],
        summary=summary,
    )

@billing_router.get("/admin/email-activity/export")
async def export_admin_email_activity(company: dict = Depends(get_current_company)):
    """Export the current company's email activity as CSV."""
    db = get_db()
    items = await db.email_events.find(
        {"company_id": company["id"]},
        {"_id": 0}
    ).sort("created_at", -1).to_list(1000)

    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(["created_at", "status", "email_type", "recipient_email", "subject", "provider_message"])

    for item in items:
        writer.writerow([
            item.get("created_at", ""),
            item.get("status", ""),
            item.get("email_type", ""),
            item.get("recipient_email", ""),
            item.get("subject", ""),
            item.get("provider_message", ""),
        ])

    filename = f"email-activity-{company['id']}.csv"
    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )

@billing_router.get("/admin/webhooks")
async def get_webhook_logs(
    limit: int = 100,
    company: dict = Depends(get_current_company)
):
    """Get webhook logs for debugging"""
    db = get_db()
    
    logs = await db.webhook_logs.find(
        {},
        {"_id": 0}
    ).sort("created_at", -1).limit(limit).to_list(limit)
    
    return {"logs": logs}

@billing_router.post("/admin/webhooks/{log_id}/retry")
async def retry_webhook(
    log_id: str,
    background_tasks: BackgroundTasks,
    company: dict = Depends(get_current_company)
):
    """Retry processing a failed webhook"""
    db = get_db()
    
    log = await db.webhook_logs.find_one({"id": log_id}, {"_id": 0})
    if not log:
        raise HTTPException(status_code=404, detail="Webhook log not found")
    
    event_type = log.get("event_type")
    data = log.get("payload", {}).get("data", {})
    
    background_tasks.add_task(process_paystack_webhook, event_type, data, log_id, db)
    
    return {"status": "queued", "message": "Webhook retry queued"}

@billing_router.post("/admin/coupons")
async def create_coupon(
    request: CreateCouponRequest,
    company: dict = Depends(get_current_company)
):
    """Create a new coupon"""
    db = get_db()
    
    # Check if code exists
    existing = await db.coupons.find_one({"code": request.code.upper()})
    if existing:
        raise HTTPException(status_code=400, detail="Coupon code already exists")
    
    coupon = {
        "id": str(uuid.uuid4()),
        "code": request.code.upper(),
        "discount_type": request.discount_type,
        "discount_value": request.discount_value,
        "currency": "USD",
        "max_uses": request.max_uses,
        "current_uses": 0,
        "valid_from": datetime.now(timezone.utc).isoformat(),
        "valid_until": (datetime.now(timezone.utc) + timedelta(days=request.valid_days)).isoformat(),
        "applicable_plans": request.applicable_plans or ["starter", "business", "pro"],
        "is_recurring": request.is_recurring,
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.coupons.insert_one(coupon)
    
    return {"status": "success", "coupon": coupon}

@billing_router.get("/admin/coupons")
async def list_coupons(company: dict = Depends(get_current_company)):
    """List all coupons"""
    db = get_db()
    
    coupons = await db.coupons.find({}, {"_id": 0}).to_list(100)
    return {"coupons": coupons}

@billing_router.post("/admin/refund")
async def process_refund(
    request: RefundRequest,
    company: dict = Depends(get_current_company)
):
    """Process a refund"""
    db = get_db()
    
    invoice = await db.invoices.find_one({"id": request.invoice_id}, {"_id": 0})
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    if not invoice.get("paystack_reference"):
        raise HTTPException(status_code=400, detail="No payment reference found")
    
    amount_kobo = int(request.amount * 100) if request.amount else None
    
    result = await refund_transaction(invoice["paystack_reference"], amount_kobo)
    
    if not result.get("status"):
        raise HTTPException(status_code=400, detail=result.get("message", "Refund failed"))
    
    # Update invoice
    refund_amount = request.amount or invoice.get("amount_paid", 0)
    await db.invoices.update_one(
        {"id": request.invoice_id},
        {
            "$set": {
                "refunded_amount": refund_amount,
                "refund_reason": request.reason,
                "refunded_at": datetime.now(timezone.utc).isoformat()
            }
        }
    )
    
    # Log event
    await log_billing_event(db, BillingEventType.REFUND_PROCESSED, {
        "invoice_id": request.invoice_id,
        "amount": refund_amount,
        "reason": request.reason
    }, invoice["company_id"])
    
    return {"status": "success", "refund": result.get("data")}

@billing_router.post("/admin/invoice/manual")
async def create_manual_invoice(
    request: ManualInvoiceRequest,
    company: dict = Depends(get_current_company)
):
    """Create a manual invoice"""
    db = get_db()
    
    invoice = {
        "id": str(uuid.uuid4()),
        "company_id": request.company_id,
        "subscription_id": None,
        "paystack_reference": None,
        "paystack_transaction_id": None,
        "amount_due": request.amount,
        "amount_paid": 0,
        "currency": request.currency,
        "status": "open",
        "description": request.description,
        "period_start": None,
        "period_end": None,
        "hosted_url": None,
        "paid_at": None,
        "is_manual": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.invoices.insert_one(invoice)
    
    return {"status": "success", "invoice": invoice}

@billing_router.post("/admin/retry-payment")
async def admin_retry_payment(
    request: RetryPaymentRequest,
    company: dict = Depends(get_current_company)
):
    """Admin: Retry failed payment for a company"""
    db = get_db()
    
    result = await retry_failed_payment(request.company_id, db)
    
    if result and result.get("success"):
        return {"status": "success", "message": "Payment retry successful"}
    
    return {"status": "failed", "error": result.get("error") if result else "Unknown error"}

@billing_router.get("/admin/delinquent")
async def get_delinquent_companies(company: dict = Depends(get_current_company)):
    """Get list of delinquent companies"""
    db = get_db()
    
    delinquent = await db.subscriptions.find(
        {"status": {"$in": ["past_due", "unpaid"]}},
        {"_id": 0}
    ).to_list(100)
    
    result = []
    for sub in delinquent:
        company_doc = await db.companies.find_one({"id": sub["company_id"]}, {"_id": 0})
        result.append({
            "subscription": sub,
            "company": company_doc
        })
    
    return {"delinquent_companies": result}

@billing_router.get("/admin/invoices/export")
async def export_invoices(
    start_date: str = None,
    end_date: str = None,
    company: dict = Depends(get_current_company)
):
    """Export invoices as CSV data"""
    db = get_db()
    
    query = {}
    if start_date:
        query["created_at"] = {"$gte": start_date}
    if end_date:
        if "created_at" in query:
            query["created_at"]["$lte"] = end_date
        else:
            query["created_at"] = {"$lte": end_date}
    
    invoices = await db.invoices.find(query, {"_id": 0}).to_list(10000)
    
    # Build CSV
    csv_lines = ["id,company_id,amount_due,amount_paid,currency,status,created_at"]
    for inv in invoices:
        csv_lines.append(f"{inv.get('id')},{inv.get('company_id')},{inv.get('amount_due')},{inv.get('amount_paid')},{inv.get('currency')},{inv.get('status')},{inv.get('created_at')}")
    
    return {"csv": "\n".join(csv_lines), "count": len(invoices)}

# ===================== FEATURE GATING ENDPOINT =====================

@billing_router.get("/access/{feature}")
async def check_feature_access(
    feature: str,
    company: dict = Depends(get_current_company)
):
    """Check if company has access to a feature"""
    db = get_db()
    result = await check_subscription_access(company["id"], feature, db)
    return result

# ===================== HELPER FUNCTIONS =====================

async def create_free_subscription(company_id: str, plan_id: str, db) -> dict:
    """Create a free subscription"""
    now = datetime.now(timezone.utc)
    period_end = now + timedelta(days=36500)  # ~100 years
    
    subscription = {
        "id": str(uuid.uuid4()),
        "company_id": company_id,
        "paystack_customer_code": None,
        "paystack_subscription_code": None,
        "paystack_email_token": None,
        "plan_id": plan_id,
        "status": "active",
        "current_period_start": now.isoformat(),
        "current_period_end": period_end.isoformat(),
        "cancel_at_period_end": False,
        "trial_start": None,
        "trial_end": None,
        "metadata": {},
        "created_at": now.isoformat(),
        "updated_at": now.isoformat()
    }
    
    # Upsert subscription
    await db.subscriptions.update_one(
        {"company_id": company_id},
        {"$set": subscription},
        upsert=True
    )
    
    return subscription

async def create_subscription_from_payment(
    company_id: str,
    plan_id: str,
    payment_data: dict,
    coupon_code: str,
    db
) -> dict:
    """Create subscription after successful payment"""
    plan = PRICING_PLANS.get(plan_id)
    now = datetime.now(timezone.utc)
    
    # Check for trial
    has_trial = plan.get("trial_days", 0) > 0
    existing_sub = await db.subscriptions.find_one({"company_id": company_id})
    
    # Only give trial if first subscription
    if existing_sub:
        has_trial = False
    
    if has_trial:
        status = "trialing"
        trial_end = now + timedelta(days=plan["trial_days"])
        period_end = trial_end
        trial_start = now.isoformat()
        trial_end_str = trial_end.isoformat()
    else:
        status = "active"
        period_end = now + timedelta(days=30)
        trial_start = None
        trial_end_str = None
    
    paystack_subscription_code = None
    paystack_email_token = None
    paystack_plan_code = None

    customer_code = payment_data.get("customer", {}).get("customer_code")
    if customer_code:
        paystack_plan_code = await ensure_paystack_plan_code(plan_id, db)
        if paystack_plan_code:
            paystack_subscription = await create_subscription(customer_code, paystack_plan_code)
            if paystack_subscription.get("status"):
                subscription_data = paystack_subscription.get("data", {})
                paystack_subscription_code = subscription_data.get("subscription_code")
                paystack_email_token = subscription_data.get("email_token")
            else:
                logger.warning("Paystack subscription creation failed for %s: %s", company_id, paystack_subscription.get("message"))

    subscription = {
        "id": str(uuid.uuid4()),
        "company_id": company_id,
        "paystack_customer_code": customer_code,
        "paystack_subscription_code": paystack_subscription_code,
        "paystack_email_token": paystack_email_token,
        "plan_id": plan_id,
        "status": status,
        "current_period_start": now.isoformat(),
        "current_period_end": period_end.isoformat(),
        "cancel_at_period_end": False,
        "trial_start": trial_start,
        "trial_end": trial_end_str,
        "metadata": {
            "coupon_code": coupon_code,
            "first_payment_reference": payment_data.get("reference"),
            "paystack_plan_code": paystack_plan_code,
        },
        "created_at": now.isoformat(),
        "updated_at": now.isoformat()
    }
    
    await db.subscriptions.update_one(
        {"company_id": company_id},
        {"$set": subscription},
        upsert=True
    )
    
    # Increment coupon usage if used
    if coupon_code:
        await db.coupons.update_one(
            {"code": coupon_code.upper()},
            {"$inc": {"current_uses": 1}}
        )
    
    return subscription

async def create_one_time_purchase(
    company_id: str,
    plan_id: str,
    payment_data: dict,
    db
) -> dict:
    """Create record for one-time purchase"""
    now = datetime.now(timezone.utc)
    
    purchase = {
        "id": str(uuid.uuid4()),
        "company_id": company_id,
        "plan_id": plan_id,
        "paystack_reference": payment_data.get("reference"),
        "amount": payment_data.get("amount", 0) / 100,
        "currency": payment_data.get("currency", "NGN"),
        "valid_until": (now + timedelta(days=30)).isoformat(),
        "audits_included": 1,
        "audits_used": 0,
        "created_at": now.isoformat()
    }
    
    await db.one_time_purchases.insert_one(purchase)
    
    # Also record usage credit
    await record_usage(company_id, "audit_credit", 1, db)
    
    return purchase

async def create_invoice_from_payment(
    company_id: str,
    payment_data: dict,
    subscription_id: str,
    db
) -> dict:
    """Create invoice from payment"""
    now = datetime.now(timezone.utc)
    
    invoice = {
        "id": str(uuid.uuid4()),
        "company_id": company_id,
        "subscription_id": subscription_id,
        "paystack_reference": payment_data.get("reference"),
        "paystack_transaction_id": str(payment_data.get("id", "")),
        "amount_due": payment_data.get("amount", 0) / 100,
        "amount_paid": payment_data.get("amount", 0) / 100,
        "currency": payment_data.get("currency", "NGN"),
        "status": "paid",
        "description": "Payment for CultureShield subscription",
        "period_start": now.isoformat(),
        "period_end": (now + timedelta(days=30)).isoformat(),
        "hosted_url": payment_data.get("receipt_url"),
        "paid_at": now.isoformat(),
        "created_at": now.isoformat()
    }
    
    await db.invoices.insert_one(invoice)
    
    return invoice

async def store_payment_method(company_id: str, authorization: dict, db):
    """Store payment method from Paystack authorization"""
    payment_method = {
        "id": str(uuid.uuid4()),
        "company_id": company_id,
        "paystack_authorization_code": authorization.get("authorization_code"),
        "card_type": authorization.get("card_type"),
        "bank": authorization.get("bank"),
        "last4": authorization.get("last4"),
        "exp_month": authorization.get("exp_month"),
        "exp_year": authorization.get("exp_year"),
        "bin": authorization.get("bin"),
        "is_default": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    # Set all other methods as non-default
    await db.payment_methods.update_many(
        {"company_id": company_id},
        {"$set": {"is_default": False}}
    )
    
    await db.payment_methods.insert_one(payment_method)
    
    return payment_method

async def ensure_paystack_plan_code(plan_id: str, db) -> Optional[str]:
    """Create or reuse a Paystack plan code for recurring plans."""
    existing_plan = await db.paystack_plans.find_one({"plan_id": plan_id}, {"_id": 0})
    if existing_plan:
        return existing_plan.get("paystack_plan_code")

    result = await create_paystack_plan(plan_id)
    if not result or not result.get("status"):
        logger.warning("Unable to create Paystack plan for %s: %s", plan_id, result.get("message") if result else "unknown error")
        return None

    plan_data = result.get("data", {})
    record = {
        "id": str(uuid.uuid4()),
        "plan_id": plan_id,
        "paystack_plan_code": plan_data.get("plan_code"),
        "paystack_plan_id": str(plan_data.get("id", "")),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.paystack_plans.insert_one(record)
    return record.get("paystack_plan_code")


# Export router
__all__ = ['billing_router']
