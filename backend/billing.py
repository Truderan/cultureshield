"""
CultureShield AI - Billing & Payment System
Paystack Integration with comprehensive billing features
"""

from fastapi import APIRouter, HTTPException, Depends, Request, BackgroundTasks
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone, timedelta
from enum import Enum
import uuid
import hmac
import hashlib
import httpx
import os
import logging
import json

from email_service import send_billing_event_email

# Configure logging
logger = logging.getLogger(__name__)

# Billing Router
billing_router = APIRouter(prefix="/api/billing", tags=["billing"])

# ===================== CONFIGURATION =====================

PAYSTACK_SECRET_KEY = os.environ.get('PAYSTACK_SECRET_KEY')
PAYSTACK_PUBLIC_KEY = os.environ.get('PAYSTACK_PUBLIC_KEY')
PAYSTACK_BASE_URL = "https://api.paystack.co"
BILLING_MODE = os.environ.get('BILLING_MODE')
USD_TO_NGN_RATE = float(os.environ['USD_TO_NGN_RATE'])

# ===================== PRICING PLANS =====================

class PlanTier(str, Enum):
    FREE = "free"
    STARTER = "starter"
    BUSINESS = "business"
    PRO = "pro"
    PAY_PER_AUDIT = "pay_per_audit"

PRICING_PLANS = {
    "free": {
        "id": "free",
        "name": "Free",
        "price_usd": 0,
        "price_ngn": 0,
        "interval": "monthly",
        "max_employees": 5,
        "max_audits_per_month": 1,
        "trial_days": 0,
        "features": ["Basic survey", "Single department", "Basic score"],
        "is_active": True
    },
    "starter": {
        "id": "starter",
        "name": "Starter",
        "price_usd": 29,
        "price_ngn": 43500,  # 29 * 1500
        "interval": "monthly",
        "max_employees": 25,
        "max_audits_per_month": 5,
        "trial_days": 14,
        "features": ["Up to 25 employees", "5 audits/month", "Basic AI reports", "Email support"],
        "is_active": True
    },
    "business": {
        "id": "business",
        "name": "Business",
        "price_usd": 79,
        "price_ngn": 118500,  # 79 * 1500
        "interval": "monthly",
        "max_employees": 100,
        "max_audits_per_month": 20,
        "trial_days": 14,
        "features": ["Up to 100 employees", "20 audits/month", "Full AI reports", "Priority support", "Department analytics", "Phishing simulations"],
        "is_active": True
    },
    "pro": {
        "id": "pro",
        "name": "Pro",
        "price_usd": 199,
        "price_ngn": 298500,  # 199 * 1500
        "interval": "monthly",
        "max_employees": -1,  # Unlimited
        "max_audits_per_month": -1,  # Unlimited
        "trial_days": 7,
        "features": ["Unlimited employees", "Unlimited audits", "Advanced AI reports", "24/7 support", "Custom branding", "API access", "Advanced phishing simulations"],
        "is_active": True
    },
    "pay_per_audit": {
        "id": "pay_per_audit",
        "name": "Pay Per Audit",
        "price_usd": 15,
        "price_ngn": 22500,  # 15 * 1500
        "interval": "one_time",
        "max_employees": -1,
        "max_audits_per_month": 1,  # Per purchase
        "trial_days": 0,
        "features": ["Single audit purchase", "Full AI report", "30-day access"],
        "is_active": True
    }
}

# ===================== PYDANTIC MODELS =====================

class SubscriptionStatus(str, Enum):
    ACTIVE = "active"
    TRIALING = "trialing"
    PAST_DUE = "past_due"
    CANCELLED = "cancelled"
    UNPAID = "unpaid"
    INCOMPLETE = "incomplete"

class InvoiceStatus(str, Enum):
    DRAFT = "draft"
    OPEN = "open"
    PAID = "paid"
    VOID = "void"
    UNCOLLECTIBLE = "uncollectible"

class BillingEventType(str, Enum):
    SUBSCRIPTION_CREATED = "subscription.created"
    SUBSCRIPTION_UPDATED = "subscription.updated"
    SUBSCRIPTION_CANCELLED = "subscription.cancelled"
    PAYMENT_SUCCESS = "payment.success"
    PAYMENT_FAILED = "payment.failed"
    INVOICE_CREATED = "invoice.created"
    INVOICE_PAID = "invoice.paid"
    REFUND_PROCESSED = "refund.processed"
    TRIAL_STARTED = "trial.started"
    TRIAL_ENDED = "trial.ended"
    DUNNING_STARTED = "dunning.started"
    ACCESS_SUSPENDED = "access.suspended"
    COUPON_APPLIED = "coupon.applied"
    PLAN_UPGRADED = "plan.upgraded"
    PLAN_DOWNGRADED = "plan.downgraded"

class SubscriptionModel(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    company_id: str
    paystack_customer_code: Optional[str] = None
    paystack_subscription_code: Optional[str] = None
    paystack_email_token: Optional[str] = None
    plan_id: str
    status: str
    current_period_start: str
    current_period_end: str
    cancel_at_period_end: bool = False
    trial_start: Optional[str] = None
    trial_end: Optional[str] = None
    metadata: Dict[str, Any] = {}
    created_at: str
    updated_at: str

class InvoiceModel(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    company_id: str
    subscription_id: Optional[str] = None
    paystack_reference: Optional[str] = None
    paystack_transaction_id: Optional[str] = None
    amount_due: float
    amount_paid: float
    currency: str
    status: str
    description: str
    period_start: Optional[str] = None
    period_end: Optional[str] = None
    hosted_url: Optional[str] = None
    paid_at: Optional[str] = None
    created_at: str

class PaymentMethodModel(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    company_id: str
    paystack_authorization_code: Optional[str] = None
    card_type: Optional[str] = None
    bank: Optional[str] = None
    last4: Optional[str] = None
    exp_month: Optional[str] = None
    exp_year: Optional[str] = None
    bin: Optional[str] = None
    is_default: bool = True
    created_at: str

class BillingEventModel(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    company_id: Optional[str] = None
    event_type: str
    payload: Dict[str, Any]
    idempotency_key: Optional[str] = None
    processed: bool = False
    processed_at: Optional[str] = None
    error_message: Optional[str] = None
    retry_count: int = 0
    created_at: str

class CouponModel(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    code: str
    discount_type: str  # "percentage" or "fixed"
    discount_value: float
    currency: str = "USD"
    max_uses: Optional[int] = None
    current_uses: int = 0
    valid_from: str
    valid_until: Optional[str] = None
    applicable_plans: List[str] = []
    is_recurring: bool = False
    is_active: bool = True
    created_at: str

class UsageRecordModel(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    company_id: str
    subscription_id: Optional[str] = None
    usage_type: str  # "audit", "employee", "report"
    quantity: int
    period_start: str
    period_end: str
    billed: bool = False
    invoice_id: Optional[str] = None
    created_at: str

# Request/Response Models
class InitializePaymentRequest(BaseModel):
    plan_id: str
    callback_url: str
    coupon_code: Optional[str] = None
    currency: str = "NGN"

class InitializePaymentResponse(BaseModel):
    authorization_url: str
    reference: str
    access_code: str

class VerifyPaymentResponse(BaseModel):
    status: str
    message: str
    subscription: Optional[SubscriptionModel] = None
    invoice: Optional[InvoiceModel] = None

class BillingDashboardStats(BaseModel):
    mrr: float
    arr: float
    total_customers: int
    active_subscriptions: int
    trialing: int
    cancelled_this_month: int
    new_subscriptions_this_month: int
    churn_rate: float
    trial_conversion_rate: float
    arpu: float
    delinquency_rate: float
    revenue_by_plan: Dict[str, float]
    top_customers: List[Dict[str, Any]]
    at_risk_customers: List[Dict[str, Any]]
    forecast_30_day_revenue: float

class CustomerBillingInfo(BaseModel):
    subscription: Optional[SubscriptionModel] = None
    invoices: List[InvoiceModel] = []
    payment_methods: List[PaymentMethodModel] = []
    usage_this_period: Dict[str, Any] = {}
    next_billing_date: Optional[str] = None
    plan_details: Dict[str, Any] = {}
    recommended_plan: Optional[str] = None
    upgrade_savings: Optional[float] = None

# ===================== HELPER FUNCTIONS =====================

def get_db():
    """Get database instance - will be set from main server"""
    from server import db
    return db

async def get_current_company_billing(credentials) -> dict:
    """Get current company from token - imported from main server"""
    from server import get_current_company
    return await get_current_company(credentials)

def generate_reference() -> str:
    """Generate unique payment reference"""
    return f"cs_{uuid.uuid4().hex[:16]}"

def calculate_period_dates(plan_id: str, is_trial: bool = False) -> tuple:
    """Calculate subscription period dates"""
    now = datetime.now(timezone.utc)
    plan = PRICING_PLANS.get(plan_id, {})
    
    if is_trial and plan.get("trial_days", 0) > 0:
        trial_end = now + timedelta(days=plan["trial_days"])
        return now.isoformat(), trial_end.isoformat(), now.isoformat(), trial_end.isoformat()
    
    if plan.get("interval") == "monthly":
        period_end = now + timedelta(days=30)
    else:
        period_end = now + timedelta(days=30)  # One-time still has 30-day access
    
    return now.isoformat(), period_end.isoformat(), None, None

def convert_currency(amount_usd: float, to_currency: str) -> float:
    """Convert USD to target currency"""
    if to_currency == "NGN":
        return amount_usd * USD_TO_NGN_RATE
    return amount_usd

def parse_iso_datetime(value: Optional[str]) -> Optional[datetime]:
    """Safely parse ISO datetime strings."""
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None

async def log_billing_event(
    db,
    event_type: str,
    payload: dict,
    company_id: Optional[str] = None,
    idempotency_key: Optional[str] = None
):
    """Log billing event to database"""
    event = {
        "id": str(uuid.uuid4()),
        "company_id": company_id,
        "event_type": event_type,
        "payload": payload,
        "idempotency_key": idempotency_key,
        "processed": True,
        "processed_at": datetime.now(timezone.utc).isoformat(),
        "retry_count": 0,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.billing_events.insert_one(event)
    logger.info(f"Billing event logged: {event_type} for company {company_id}")
    return event

async def send_billing_notification(
    notification_type: str,
    company_id: str,
    data: dict,
    db
):
    """Send billing email notification and log the outcome."""
    company = await db.companies.find_one({"id": company_id}, {"_id": 0})
    email_result = {"status": "skipped", "reason": "company_not_found"}

    if company and company.get("email"):
        email_result = await send_billing_event_email(
            company_name=company.get("company_name", "CultureShield customer"),
            recipient_email=company["email"],
            notification_type=notification_type,
            data=data,
            company_id=company_id,
        )

    notification = {
        "id": str(uuid.uuid4()),
        "company_id": company_id,
        "type": notification_type,
        "data": data,
        "sent": email_result.get("status") == "sent",
        "delivery_status": email_result.get("status"),
        "delivery_error": email_result.get("error"),
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.billing_notifications.insert_one(notification)
    logger.info(
        "Billing notification %s for company %s: %s",
        notification_type,
        company_id,
        json.dumps({"data": data, "delivery": email_result}, default=str)[:300],
    )
    return notification

# ===================== PAYSTACK API HELPERS =====================

async def paystack_request(method: str, endpoint: str, data: dict = None) -> dict:
    """Make authenticated request to Paystack API"""
    async with httpx.AsyncClient() as client:
        headers = {
            "Authorization": f"Bearer {PAYSTACK_SECRET_KEY}",
            "Content-Type": "application/json"
        }
        url = f"{PAYSTACK_BASE_URL}/{endpoint}"
        
        if method == "GET":
            response = await client.get(url, headers=headers)
        elif method == "POST":
            response = await client.post(url, headers=headers, json=data or {})
        elif method == "PUT":
            response = await client.put(url, headers=headers, json=data or {})
        else:
            raise ValueError(f"Unsupported method: {method}")
        
        result = response.json()
        logger.info(f"Paystack {method} {endpoint}: {result.get('status')}")
        return result

async def create_paystack_customer(email: str, company_name: str, metadata: dict = None) -> dict:
    """Create or get Paystack customer"""
    result = await paystack_request("POST", "customer", {
        "email": email,
        "first_name": company_name,
        "metadata": metadata or {}
    })
    return result

async def create_paystack_plan(plan_id: str) -> dict:
    """Create Paystack subscription plan"""
    plan = PRICING_PLANS.get(plan_id)
    if not plan or plan["interval"] == "one_time":
        return None
    
    amount_kobo = int(plan["price_ngn"] * 100)
    result = await paystack_request("POST", "plan", {
        "name": f"CultureShield {plan['name']}",
        "amount": amount_kobo,
        "interval": "monthly",
        "currency": "NGN",
        "description": f"CultureShield {plan['name']} - {', '.join(plan['features'][:3])}"
    })
    return result

async def initialize_transaction(
    email: str,
    amount_kobo: int,
    reference: str,
    callback_url: str,
    metadata: dict = None
) -> dict:
    """Initialize Paystack transaction"""
    result = await paystack_request("POST", "transaction/initialize", {
        "email": email,
        "amount": amount_kobo,
        "reference": reference,
        "callback_url": callback_url,
        "metadata": metadata or {},
        "currency": "NGN"
    })
    return result

async def verify_transaction(reference: str) -> dict:
    """Verify Paystack transaction"""
    result = await paystack_request("GET", f"transaction/verify/{reference}")
    return result

async def create_subscription(customer_code: str, plan_code: str, start_date: str = None) -> dict:
    """Create Paystack subscription"""
    data = {
        "customer": customer_code,
        "plan": plan_code
    }
    if start_date:
        data["start_date"] = start_date
    
    result = await paystack_request("POST", "subscription", data)
    return result

async def disable_subscription(subscription_code: str, email_token: str) -> dict:
    """Disable/cancel Paystack subscription"""
    result = await paystack_request("POST", "subscription/disable", {
        "code": subscription_code,
        "token": email_token
    })
    return result

async def refund_transaction(transaction_reference: str, amount: int = None) -> dict:
    """Process refund"""
    data = {"transaction": transaction_reference}
    if amount:
        data["amount"] = amount
    result = await paystack_request("POST", "refund", data)
    return result

# ===================== FEATURE GATING =====================

async def get_company_plan_context(company_id: str, db) -> dict:
    """Return the active subscription context, or fall back to the free plan."""
    subscription = await db.subscriptions.find_one(
        {"company_id": company_id},
        {"_id": 0},
        sort=[("updated_at", -1)]
    )

    now = datetime.now(timezone.utc)
    active_subscription = None

    if subscription:
        status = subscription.get("status")
        period_end = parse_iso_datetime(subscription.get("current_period_end"))
        trial_end = parse_iso_datetime(subscription.get("trial_end"))

        is_trial_active = status == "trialing" and (trial_end is None or now <= trial_end)
        is_subscription_active = status == "active" and (period_end is None or now <= period_end)

        if is_trial_active or is_subscription_active:
            active_subscription = subscription

    plan_id = active_subscription.get("plan_id", "free") if active_subscription else "free"
    plan = PRICING_PLANS.get(plan_id, PRICING_PLANS["free"])

    return {
        "subscription": subscription,
        "active_subscription": active_subscription,
        "plan_id": plan_id,
        "plan": plan,
    }

async def get_active_audit_purchase(company_id: str, db) -> Optional[dict]:
    """Return the oldest valid unused one-time audit purchase, if any."""
    purchases = await db.one_time_purchases.find(
        {"company_id": company_id},
        {"_id": 0}
    ).sort("created_at", 1).to_list(50)

    now = datetime.now(timezone.utc)
    for purchase in purchases:
        valid_until = parse_iso_datetime(purchase.get("valid_until"))
        audits_used = purchase.get("audits_used", 0)
        audits_included = purchase.get("audits_included", 0)
        if valid_until and now <= valid_until and audits_used < audits_included:
            return purchase

    return None

async def check_subscription_access(company_id: str, feature: str, db) -> dict:
    """Check if company has access to a feature based on subscription"""
    plan_context = await get_company_plan_context(company_id, db)
    subscription = plan_context["active_subscription"]
    plan_id = plan_context["plan_id"]
    plan = plan_context["plan"]
    audit_purchase = await get_active_audit_purchase(company_id, db) if feature in ["ai_report", "audit"] else None
    
    # Feature-specific checks
    feature_requirements = {
        "ai_report": ["starter", "business", "pro", "pay_per_audit"],
        "advanced_analytics": ["business", "pro"],
        "unlimited_employees": ["pro"],
        "api_access": ["pro"],
        "custom_branding": ["pro"],
        "phishing_simulation": ["business", "pro"]
    }
    
    required_plans = feature_requirements.get(feature, [])
    if required_plans and plan_id not in required_plans and not audit_purchase:
        requires_one_time_audit = feature in ["ai_report", "audit"]
        feature_message = (
            f"This feature requires {', '.join(required_plans)} plan or a one-time audit purchase."
            if requires_one_time_audit
            else f"This feature requires {', '.join(required_plans)} plan."
        )
        return {
            "allowed": False,
            "reason": "plan_insufficient" if subscription else "no_subscription",
            "message": feature_message
        }
    
    # Check usage limits
    if feature == "audit":
        if audit_purchase and plan_id == "free":
            remaining_audits = audit_purchase.get("audits_included", 0) - audit_purchase.get("audits_used", 0)
            return {
                "allowed": remaining_audits > 0,
                "reason": "one_time_credit" if remaining_audits > 0 else "usage_limit",
                "message": "Access granted via one-time audit purchase." if remaining_audits > 0 else "Your one-time audit credit has been used.",
                "billing_source": "one_time_purchase",
                "remaining_audits": remaining_audits,
            }

        usage = await get_usage_this_period(company_id, db)
        max_audits = plan.get("max_audits_per_month", 0)
        if max_audits != -1 and usage.get("audits", 0) >= max_audits:
            return {
                "allowed": False,
                "reason": "usage_limit",
                "message": f"You've reached your {max_audits} audits limit. Upgrade for more."
            }
    
    response = {"allowed": True, "reason": "access_granted", "message": "Access granted"}
    if audit_purchase and feature in ["ai_report", "audit"]:
        response["billing_source"] = "one_time_purchase"
        response["remaining_audits"] = audit_purchase.get("audits_included", 0) - audit_purchase.get("audits_used", 0)
    elif subscription:
        response["billing_source"] = "subscription"

    return response

async def consume_audit_credit(company_id: str, db) -> Optional[dict]:
    """Consume one one-time audit credit after a report is generated."""
    purchase = await get_active_audit_purchase(company_id, db)
    if not purchase:
        return None

    new_used_count = purchase.get("audits_used", 0) + 1
    await db.one_time_purchases.update_one(
        {"id": purchase["id"]},
        {
            "$set": {
                "audits_used": new_used_count,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
        }
    )

    purchase["audits_used"] = new_used_count
    return purchase

async def get_usage_this_period(company_id: str, db) -> dict:
    """Get usage for current billing period"""
    subscription = await db.subscriptions.find_one(
        {"company_id": company_id},
        {"_id": 0}
    )
    
    if not subscription:
        period_start = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
    else:
        period_start = subscription.get("current_period_start", (datetime.now(timezone.utc) - timedelta(days=30)).isoformat())
    
    # Count audits (reports generated)
    audits_count = await db.audit_reports.count_documents({
        "company_id": company_id,
        "generated_at": {"$gte": period_start}
    })
    
    # Count employees
    employees_count = await db.employees.count_documents({"company_id": company_id})
    
    # Count surveys completed
    surveys_count = await db.survey_responses.count_documents({
        "company_id": company_id,
        "submitted_at": {"$gte": period_start}
    })
    
    return {
        "audits": audits_count,
        "employees": employees_count,
        "surveys": surveys_count,
        "period_start": period_start
    }

# ===================== BILLING INTELLIGENCE =====================

async def calculate_churn_risk(company_id: str, db) -> dict:
    """Calculate churn risk score for a company"""
    # Get subscription
    subscription = await db.subscriptions.find_one(
        {"company_id": company_id},
        {"_id": 0}
    )
    
    if not subscription:
        return {"risk_score": 0, "risk_level": "none", "signals": []}

    if subscription.get("plan_id") == "free":
        return {"risk_score": 0, "risk_level": "none", "signals": []}
    
    signals = []
    risk_score = 0
    
    # Signal 1: Low usage (< 30% of allowed)
    usage = await get_usage_this_period(company_id, db)
    plan = PRICING_PLANS.get(subscription.get("plan_id", "free"), {})
    max_audits = plan.get("max_audits_per_month", 1)
    
    if max_audits > 0:
        usage_rate = usage.get("audits", 0) / max_audits
        if usage_rate < 0.3:
            signals.append("Low usage: <30% of allowed audits used")
            risk_score += 25
    
    # Signal 2: No activity in last 14 days
    last_survey = await db.survey_responses.find_one(
        {"company_id": company_id},
        {"_id": 0},
        sort=[("submitted_at", -1)]
    )
    if last_survey:
        last_activity = datetime.fromisoformat(last_survey.get("submitted_at", "").replace("Z", "+00:00"))
        days_inactive = (datetime.now(timezone.utc) - last_activity).days
        if days_inactive > 14:
            signals.append(f"Inactive for {days_inactive} days")
            risk_score += 20
    else:
        signals.append("No survey activity recorded")
        risk_score += 15
    
    # Signal 3: Failed payments
    failed_payments = await db.billing_events.count_documents({
        "company_id": company_id,
        "event_type": "payment.failed",
        "created_at": {"$gte": (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()}
    })
    if failed_payments > 0:
        signals.append(f"{failed_payments} failed payment(s) in last 30 days")
        risk_score += 30
    
    # Signal 4: Cancel at period end flag
    if subscription.get("cancel_at_period_end"):
        signals.append("Scheduled for cancellation")
        risk_score += 40
    
    # Signal 5: Downgraded recently
    downgrade_event = await db.billing_events.find_one({
        "company_id": company_id,
        "event_type": "plan.downgraded",
        "created_at": {"$gte": (datetime.now(timezone.utc) - timedelta(days=60)).isoformat()}
    })
    if downgrade_event:
        signals.append("Downgraded plan in last 60 days")
        risk_score += 20
    
    # Determine risk level
    if risk_score >= 70:
        risk_level = "high"
    elif risk_score >= 40:
        risk_level = "medium"
    elif risk_score > 0:
        risk_level = "low"
    else:
        risk_level = "none"
    
    return {
        "risk_score": min(risk_score, 100),
        "risk_level": risk_level,
        "signals": signals
    }

async def get_plan_recommendation(company_id: str, db) -> dict:
    """Recommend plan based on usage patterns"""
    usage = await get_usage_this_period(company_id, db)
    subscription = await db.subscriptions.find_one(
        {"company_id": company_id},
        {"_id": 0}
    )
    
    current_plan_id = subscription.get("plan_id", "free") if subscription else "free"
    
    employees = usage.get("employees", 0)
    audits = usage.get("audits", 0)
    
    recommendation = None
    reason = None
    projected_savings = None
    
    # Check if should upgrade
    if current_plan_id == "free":
        if employees > 5 or audits > 1:
            recommendation = "starter"
            reason = f"You have {employees} employees and {audits} audits. Starter plan offers better value."
    elif current_plan_id == "starter":
        if employees > 25 or audits > 5:
            recommendation = "business"
            reason = f"You're approaching limits ({employees} employees, {audits} audits). Business plan offers 100 employees and 20 audits."
    elif current_plan_id == "business":
        if employees > 80 or audits > 15:
            recommendation = "pro"
            reason = f"High usage detected ({employees} employees, {audits} audits). Pro plan offers unlimited access."
    
    # Check if can downgrade (save money)
    if current_plan_id == "pro":
        if employees <= 100 and audits <= 20:
            recommendation = "business"
            reason = f"Your usage ({employees} employees, {audits} audits) fits in Business plan."
            projected_savings = PRICING_PLANS["pro"]["price_usd"] - PRICING_PLANS["business"]["price_usd"]
    elif current_plan_id == "business":
        if employees <= 25 and audits <= 5:
            recommendation = "starter"
            reason = f"Your usage ({employees} employees, {audits} audits) fits in Starter plan."
            projected_savings = PRICING_PLANS["business"]["price_usd"] - PRICING_PLANS["starter"]["price_usd"]
    
    return {
        "current_plan": current_plan_id,
        "recommended_plan": recommendation,
        "reason": reason,
        "projected_monthly_savings": projected_savings
    }

async def trigger_retention_action(company_id: str, risk_data: dict, db):
    """Trigger automated retention action based on churn risk"""
    if risk_data["risk_level"] not in ["high", "medium"]:
        return None
    
    # Check if action already taken recently
    recent_action = await db.retention_actions.find_one({
        "company_id": company_id,
        "created_at": {"$gte": (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()}
    })
    
    if recent_action:
        return None  # Don't spam
    
    company = await db.companies.find_one({"id": company_id}, {"_id": 0})
    if not company:
        return None
    
    action_type = None
    action_data = {}
    
    if risk_data["risk_level"] == "high":
        # High risk: Offer discount
        action_type = "discount_offer"
        action_data = {
            "coupon_code": f"SAVE20_{uuid.uuid4().hex[:6].upper()}",
            "discount_percent": 20,
            "message": "We miss you! Here's 20% off your next month."
        }
        # Create the coupon
        coupon = {
            "id": str(uuid.uuid4()),
            "code": action_data["coupon_code"],
            "discount_type": "percentage",
            "discount_value": 20,
            "currency": "USD",
            "max_uses": 1,
            "current_uses": 0,
            "valid_from": datetime.now(timezone.utc).isoformat(),
            "valid_until": (datetime.now(timezone.utc) + timedelta(days=14)).isoformat(),
            "applicable_plans": ["starter", "business", "pro"],
            "is_recurring": False,
            "is_active": True,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        await db.coupons.insert_one(coupon)
    else:
        # Medium risk: Send engagement email
        action_type = "engagement_email"
        action_data = {
            "message": "We noticed you haven't run an audit recently. Need help getting started?"
        }
    
    # Record retention action
    retention_action = {
        "id": str(uuid.uuid4()),
        "company_id": company_id,
        "action_type": action_type,
        "action_data": action_data,
        "risk_score": risk_data["risk_score"],
        "signals": risk_data["signals"],
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.retention_actions.insert_one(retention_action)
    
    # Send notification (mocked)
    await send_billing_notification(
        f"retention_{action_type}",
        company_id,
        action_data,
        db
    )
    
    logger.info(f"Retention action triggered for company {company_id}: {action_type}")
    return retention_action

# ===================== DUNNING & RETRY LOGIC =====================

DUNNING_SCHEDULE = [
    {"days_after_failure": 1, "action": "email", "template": "payment_failed_reminder_1"},
    {"days_after_failure": 3, "action": "email", "template": "payment_failed_reminder_2"},
    {"days_after_failure": 7, "action": "email", "template": "payment_failed_final_warning"},
    {"days_after_failure": 10, "action": "suspend", "template": "access_suspended"}
]

RETRY_SCHEDULE = [
    {"days_after_failure": 1, "attempt": 1},
    {"days_after_failure": 3, "attempt": 2},
    {"days_after_failure": 7, "attempt": 3}
]

async def process_dunning(company_id: str, db):
    """Process dunning for a company with failed payment"""
    # Get the failed payment event
    failed_event = await db.billing_events.find_one(
        {
            "company_id": company_id,
            "event_type": "payment.failed",
            "processed": True
        },
        {"_id": 0},
        sort=[("created_at", -1)]
    )
    
    if not failed_event:
        return None
    
    failure_date = datetime.fromisoformat(failed_event["created_at"].replace("Z", "+00:00"))
    days_since_failure = (datetime.now(timezone.utc) - failure_date).days
    
    # Check what dunning actions to take
    for step in DUNNING_SCHEDULE:
        if days_since_failure >= step["days_after_failure"]:
            # Check if this step was already done
            existing_action = await db.dunning_actions.find_one({
                "company_id": company_id,
                "failed_event_id": failed_event["id"],
                "step_days": step["days_after_failure"]
            })
            
            if not existing_action:
                # Execute dunning action
                if step["action"] == "email":
                    await send_billing_notification(
                        step["template"],
                        company_id,
                        {"days_overdue": days_since_failure},
                        db
                    )
                elif step["action"] == "suspend":
                    # Suspend access
                    await db.subscriptions.update_one(
                        {"company_id": company_id},
                        {"$set": {"status": "unpaid", "updated_at": datetime.now(timezone.utc).isoformat()}}
                    )
                    await log_billing_event(db, "access.suspended", {"reason": "payment_failed"}, company_id)
                
                # Record dunning action
                await db.dunning_actions.insert_one({
                    "id": str(uuid.uuid4()),
                    "company_id": company_id,
                    "failed_event_id": failed_event["id"],
                    "step_days": step["days_after_failure"],
                    "action": step["action"],
                    "template": step["template"],
                    "executed_at": datetime.now(timezone.utc).isoformat()
                })
                
                logger.info(f"Dunning action executed for company {company_id}: {step['template']}")

async def retry_failed_payment(company_id: str, db):
    """Retry failed payment with exponential backoff"""
    subscription = await db.subscriptions.find_one(
        {"company_id": company_id},
        {"_id": 0}
    )
    
    if not subscription or subscription.get("status") not in ["past_due", "unpaid"]:
        return None
    
    # Get payment method
    payment_method = await db.payment_methods.find_one(
        {"company_id": company_id, "is_default": True},
        {"_id": 0}
    )
    
    if not payment_method or not payment_method.get("paystack_authorization_code"):
        return {"success": False, "error": "No valid payment method"}
    
    # Get plan amount
    plan = PRICING_PLANS.get(subscription.get("plan_id", "starter"))
    amount_kobo = int(plan["price_ngn"] * 100)
    
    # Charge authorization
    company = await db.companies.find_one({"id": company_id}, {"_id": 0})
    
    result = await paystack_request("POST", "transaction/charge_authorization", {
        "authorization_code": payment_method["paystack_authorization_code"],
        "email": company["email"],
        "amount": amount_kobo,
        "reference": generate_reference()
    })
    
    if result.get("status") and result.get("data", {}).get("status") == "success":
        # Payment succeeded
        await db.subscriptions.update_one(
            {"company_id": company_id},
            {
                "$set": {
                    "status": "active",
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }
            }
        )
        await log_billing_event(db, "payment.success", result.get("data", {}), company_id)
        await send_billing_notification("payment_success", company_id, {"amount": plan["price_usd"]}, db)
        return {"success": True}
    
    return {"success": False, "error": result.get("message")}

# ===================== COUPON FUNCTIONS =====================

async def validate_coupon(code: str, plan_id: str, db) -> dict:
    """Validate a coupon code"""
    coupon = await db.coupons.find_one(
        {"code": code.upper(), "is_active": True},
        {"_id": 0}
    )
    
    if not coupon:
        return {"valid": False, "error": "Coupon not found or inactive"}
    
    now = datetime.now(timezone.utc)
    valid_from = datetime.fromisoformat(coupon["valid_from"].replace("Z", "+00:00"))
    
    if now < valid_from:
        return {"valid": False, "error": "Coupon not yet active"}
    
    if coupon.get("valid_until"):
        valid_until = datetime.fromisoformat(coupon["valid_until"].replace("Z", "+00:00"))
        if now > valid_until:
            return {"valid": False, "error": "Coupon has expired"}
    
    if coupon.get("max_uses") and coupon.get("current_uses", 0) >= coupon["max_uses"]:
        return {"valid": False, "error": "Coupon usage limit reached"}
    
    if coupon.get("applicable_plans") and plan_id not in coupon["applicable_plans"]:
        return {"valid": False, "error": "Coupon not valid for this plan"}
    
    return {
        "valid": True,
        "coupon": coupon,
        "discount_type": coupon["discount_type"],
        "discount_value": coupon["discount_value"]
    }

async def apply_coupon_discount(amount: float, coupon: dict) -> float:
    """Apply coupon discount to amount"""
    if coupon["discount_type"] == "percentage":
        discount = amount * (coupon["discount_value"] / 100)
    else:
        discount = coupon["discount_value"]
    
    return max(0, amount - discount)

# ===================== BILLING METRICS =====================

async def calculate_billing_metrics(db, company_id: Optional[str] = None) -> BillingDashboardStats:
    """Calculate billing dashboard metrics"""
    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    if company_id:
        subscription = await db.subscriptions.find_one({"company_id": company_id}, {"_id": 0})
        company = await db.companies.find_one({"id": company_id}, {"_id": 0})
        plan_id = subscription.get("plan_id", "free") if subscription else "free"
        plan = PRICING_PLANS.get(plan_id, PRICING_PLANS["free"])
        is_paid_plan = plan_id != "free"
        is_active_paid = bool(subscription and subscription.get("status") == "active" and is_paid_plan)
        is_trialing_paid = bool(subscription and subscription.get("status") == "trialing" and is_paid_plan)

        mrr = plan.get("price_usd", 0) if (is_active_paid or is_trialing_paid) else 0
        arr = mrr * 12

        cancelled_this_month = await db.billing_events.count_documents({
            "company_id": company_id,
            "event_type": "subscription.cancelled",
            "created_at": {"$gte": month_start.isoformat()}
        })

        new_subs_this_month = await db.subscriptions.count_documents({
            "company_id": company_id,
            "plan_id": {"$ne": "free"},
            "created_at": {"$gte": month_start.isoformat()}
        })

        prev_month_active = await db.subscriptions.count_documents({
            "company_id": company_id,
            "plan_id": {"$ne": "free"},
            "created_at": {"$lt": month_start.isoformat()},
            "status": {"$in": ["active", "trialing", "cancelled"]}
        })
        churn_rate = (cancelled_this_month / prev_month_active * 100) if prev_month_active > 0 else 0

        trials_ended = await db.billing_events.count_documents({
            "company_id": company_id,
            "event_type": "trial.ended",
            "created_at": {"$gte": (now - timedelta(days=60)).isoformat()}
        })
        trials_converted = await db.billing_events.count_documents({
            "company_id": company_id,
            "event_type": "subscription.created",
            "created_at": {"$gte": (now - timedelta(days=60)).isoformat()},
            "payload.from_trial": True
        })
        trial_conversion_rate = (trials_converted / trials_ended * 100) if trials_ended > 0 else 0

        delinquency_rate = 100 if subscription and subscription.get("status") == "past_due" and is_paid_plan else 0
        risk = await calculate_churn_risk(company_id, db) if is_paid_plan else {"risk_score": 0, "risk_level": "none", "signals": []}
        at_risk_customers = []
        if company and risk["risk_level"] in ["high", "medium"]:
            at_risk_customers.append({
                "company_id": company_id,
                "company_name": company.get("company_name", "Unknown"),
                "risk_level": risk["risk_level"],
                "risk_score": risk["risk_score"],
                "signals": risk["signals"]
            })

        revenue_by_plan = {plan.get("name", "Free"): mrr}
        forecast_30_day = mrr * (1 - churn_rate / 100)

        return BillingDashboardStats(
            mrr=round(mrr, 2),
            arr=round(arr, 2),
            total_customers=1 if subscription else 0,
            active_subscriptions=1 if is_active_paid else 0,
            trialing=1 if is_trialing_paid else 0,
            cancelled_this_month=cancelled_this_month,
            new_subscriptions_this_month=new_subs_this_month,
            churn_rate=round(churn_rate, 2),
            trial_conversion_rate=round(trial_conversion_rate, 2),
            arpu=round(mrr, 2),
            delinquency_rate=round(delinquency_rate, 2),
            revenue_by_plan=revenue_by_plan,
            top_customers=[],
            at_risk_customers=at_risk_customers,
            forecast_30_day_revenue=round(forecast_30_day, 2)
        )
    
    # Get all active paid subscriptions for platform-wide metrics
    active_subs = await db.subscriptions.find(
        {"status": {"$in": ["active", "trialing"]}, "plan_id": {"$ne": "free"}},
        {"_id": 0}
    ).to_list(10000)
    
    # Calculate MRR
    mrr = 0
    revenue_by_plan = {}
    for sub in active_subs:
        plan = PRICING_PLANS.get(sub.get("plan_id", "free"), {})
        plan_mrr = plan.get("price_usd", 0)
        mrr += plan_mrr
        
        plan_name = plan.get("name", "Unknown")
        revenue_by_plan[plan_name] = revenue_by_plan.get(plan_name, 0) + plan_mrr
    
    arr = mrr * 12
    
    # Total customers
    total_customers = await db.subscriptions.count_documents({"plan_id": {"$ne": "free"}})
    active_subscriptions = len([s for s in active_subs if s.get("status") == "active"])
    trialing = len([s for s in active_subs if s.get("status") == "trialing"])
    
    # Cancellations this month
    cancelled_this_month = await db.billing_events.count_documents({
        "event_type": "subscription.cancelled",
        "created_at": {"$gte": month_start.isoformat()}
    })
    
    # New subscriptions this month
    new_subs_this_month = await db.subscriptions.count_documents({
        "plan_id": {"$ne": "free"},
        "created_at": {"$gte": month_start.isoformat()}
    })
    
    # Churn rate
    prev_month_active = await db.subscriptions.count_documents({
        "plan_id": {"$ne": "free"},
        "created_at": {"$lt": month_start.isoformat()},
        "status": {"$in": ["active", "trialing", "cancelled"]}
    })
    churn_rate = (cancelled_this_month / prev_month_active * 100) if prev_month_active > 0 else 0
    
    # Trial conversion rate
    trials_ended = await db.billing_events.count_documents({
        "event_type": "trial.ended",
        "created_at": {"$gte": (now - timedelta(days=60)).isoformat()}
    })
    trials_converted = await db.billing_events.count_documents({
        "event_type": "subscription.created",
        "created_at": {"$gte": (now - timedelta(days=60)).isoformat()},
        "payload.from_trial": True
    })
    trial_conversion_rate = (trials_converted / trials_ended * 100) if trials_ended > 0 else 0
    
    # ARPU
    arpu = mrr / total_customers if total_customers > 0 else 0
    
    # Delinquency rate
    past_due = await db.subscriptions.count_documents({"status": "past_due"})
    delinquency_rate = (past_due / total_customers * 100) if total_customers > 0 else 0
    
    # Top customers by revenue
    top_customers = []
    for sub in sorted(active_subs, key=lambda x: PRICING_PLANS.get(x.get("plan_id"), {}).get("price_usd", 0), reverse=True)[:10]:
        company = await db.companies.find_one({"id": sub["company_id"]}, {"_id": 0})
        if company:
            plan = PRICING_PLANS.get(sub.get("plan_id", "free"), {})
            top_customers.append({
                "company_id": sub["company_id"],
                "company_name": company.get("company_name", "Unknown"),
                "plan": plan.get("name", "Unknown"),
                "mrr": plan.get("price_usd", 0)
            })
    
    # At-risk customers
    at_risk_customers = []
    for sub in active_subs[:50]:  # Check first 50 for performance
        risk = await calculate_churn_risk(sub["company_id"], db)
        if risk["risk_level"] in ["high", "medium"]:
            company = await db.companies.find_one({"id": sub["company_id"]}, {"_id": 0})
            at_risk_customers.append({
                "company_id": sub["company_id"],
                "company_name": company.get("company_name", "Unknown") if company else "Unknown",
                "risk_level": risk["risk_level"],
                "risk_score": risk["risk_score"],
                "signals": risk["signals"]
            })
    
    # 30-day forecast (simple projection)
    forecast_30_day = mrr * (1 - churn_rate / 100)
    
    return BillingDashboardStats(
        mrr=round(mrr, 2),
        arr=round(arr, 2),
        total_customers=total_customers,
        active_subscriptions=active_subscriptions,
        trialing=trialing,
        cancelled_this_month=cancelled_this_month,
        new_subscriptions_this_month=new_subs_this_month,
        churn_rate=round(churn_rate, 2),
        trial_conversion_rate=round(trial_conversion_rate, 2),
        arpu=round(arpu, 2),
        delinquency_rate=round(delinquency_rate, 2),
        revenue_by_plan=revenue_by_plan,
        top_customers=top_customers,
        at_risk_customers=at_risk_customers,
        forecast_30_day_revenue=round(forecast_30_day, 2)
    )

# ===================== RECORD USAGE =====================

async def record_usage(company_id: str, usage_type: str, quantity: int, db):
    """Record billable usage"""
    subscription = await db.subscriptions.find_one(
        {"company_id": company_id},
        {"_id": 0}
    )
    
    period_start = subscription.get("current_period_start") if subscription else datetime.now(timezone.utc).isoformat()
    period_end = subscription.get("current_period_end") if subscription else (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
    
    usage_record = {
        "id": str(uuid.uuid4()),
        "company_id": company_id,
        "subscription_id": subscription.get("id") if subscription else None,
        "usage_type": usage_type,
        "quantity": quantity,
        "period_start": period_start,
        "period_end": period_end,
        "billed": False,
        "invoice_id": None,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.usage_records.insert_one(usage_record)
    logger.info(f"Usage recorded: {usage_type} x{quantity} for company {company_id}")
    return usage_record


# Export for main server
__all__ = [
    'billing_router',
    'PRICING_PLANS',
    'check_subscription_access',
    'consume_audit_credit',
    'get_company_plan_context',
    'record_usage',
    'get_usage_this_period',
    'calculate_churn_risk',
    'get_plan_recommendation',
    'trigger_retention_action',
    'log_billing_event',
    'send_billing_notification'
]
