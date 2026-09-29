from fastapi import FastAPI, APIRouter, HTTPException, Depends, status, Response, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, EmailStr, ConfigDict
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timezone, timedelta
from passlib.context import CryptContext
from jose import JWTError, jwt
import asyncio
from fpdf import FPDF
import io
import base64

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# JWT Configuration
JWT_SECRET = os.environ['JWT_SECRET']
JWT_ALGORITHM = os.environ['JWT_ALGORITHM']
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.environ['ACCESS_TOKEN_EXPIRE_MINUTES'])

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Security
security = HTTPBearer()

# Create the main app
app = FastAPI(title="CultureShield AI API")

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

from billing import PRICING_PLANS, check_subscription_access, consume_audit_credit, get_company_plan_context
from email_service import (
    send_password_reset_email,
    send_phishing_simulation_email,
    send_report_ready_email,
    send_survey_completion_email,
    send_survey_invite_email,
    send_welcome_email,
)
from auth_security import (
    consume_backup_code,
    create_auth_session,
    create_mfa_login_challenge,
    create_password_reset_record,
    create_totp_setup,
    decrypt_sensitive_value,
    encrypt_sensitive_value,
    enforce_auth_rate_limit,
    generate_backup_codes,
    get_remaining_backup_codes,
    get_request_ip,
    get_valid_mfa_login_challenge,
    get_valid_password_reset_record,
    hash_backup_codes,
    log_auth_event,
    revoke_auth_session,
    validate_password_strength,
    verify_totp_code,
)
from phishing_simulation import (
    build_training_content,
    get_phishing_template,
    list_phishing_templates,
    render_phishing_email,
)

# ===================== MODELS =====================

class CompanyCreate(BaseModel):
    company_name: str
    email: EmailStr
    password: str

class CompanyLogin(BaseModel):
    email: EmailStr
    password: str

class CompanyLoginResponse(BaseModel):
    access_token: Optional[str] = None
    token_type: str = "bearer"
    company: Optional["CompanyResponse"] = None
    mfa_required: bool = False
    mfa_setup_required: bool = False
    mfa_token: Optional[str] = None

class CompanyResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    company_name: str
    email: str
    created_at: str
    mfa_enabled: bool = False
    mfa_enforced: bool = True

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    company: CompanyResponse

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    token: str
    password: str

class VerifyMFALoginRequest(BaseModel):
    mfa_token: str
    code: str

class ConfirmMFASetupRequest(BaseModel):
    code: str

class DisableMFARequest(BaseModel):
    password: str
    code: str

class MFAStatusResponse(BaseModel):
    enabled: bool
    enforced: bool
    backup_codes_remaining: int

class MFASetupInitResponse(BaseModel):
    qr_code_data_url: str
    manual_entry_key: str
    backup_codes: List[str]
    issuer: str = "CultureShield AI"

class AuthSessionResponse(BaseModel):
    id: str
    device_name: str
    browser: str
    os: str
    ip_address: str
    mfa_verified: bool
    created_at: str
    last_active_at: str
    is_current: bool
    risk_flags: List[str] = []

class AuthSessionListResponse(BaseModel):
    current_session_id: str
    items: List[AuthSessionResponse]

class PhishingCampaignCreate(BaseModel):
    name: str
    template_id: str
    target_employee_ids: List[str]
    send_immediately: bool = False

class PhishingTemplateResponse(BaseModel):
    id: str
    name: str
    category: str
    difficulty: str
    subject: str
    preview_text: str
    scenario: str
    cta_label: str

class PhishingRecipientResponse(BaseModel):
    id: str
    employee_id: str
    employee_name: str
    employee_email: str
    department: str
    delivery_status: str
    delivery_error: Optional[str] = None
    opened_at: Optional[str] = None
    clicked_at: Optional[str] = None
    reported_at: Optional[str] = None
    sent_at: Optional[str] = None

class PhishingCampaignResponse(BaseModel):
    id: str
    name: str
    template_id: str
    template_name: str
    status: str
    total_targets: int
    delivered_count: int
    opened_count: int
    clicked_count: int
    reported_count: int
    created_at: str
    sent_at: Optional[str] = None
    recipients: List[PhishingRecipientResponse] = []

class PhishingSimulationLandingResponse(BaseModel):
    campaign_name: str
    template_name: str
    employee_name: str
    company_name: str
    difficulty: str
    category: str
    scenario: str
    red_flags: List[str]
    learning_points: List[str]
    already_reported: bool

CompanyLoginResponse.model_rebuild()

class EmployeeCreate(BaseModel):
    name: str
    email: EmailStr
    department: str

class EmployeeResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    company_id: str
    name: str
    email: str
    department: str
    survey_completed: bool
    survey_link: str
    created_at: str

class SurveyQuestion(BaseModel):
    id: str
    category: str
    question: str
    options: List[str]
    risk_weight: int  # Higher = more risky if answered poorly

class SurveySubmission(BaseModel):
    responses: Dict[str, int]  # question_id -> option_index (0-based)

class RiskFlag(BaseModel):
    flag_id: str
    severity: str  # critical, high, medium, low
    category: str
    title: str
    description: str
    recommendation: str

class SurveyResponseModel(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    employee_id: str
    company_id: str
    responses: Dict[str, int]
    scores: Dict[str, float]
    overall_score: float
    risk_level: str
    risk_flags: List[Dict[str, Any]] = []
    risk_profile: Dict[str, Any] = {}
    submitted_at: str

class HighRiskEmployee(BaseModel):
    employee_id: str
    name: str
    department: str
    overall_score: float
    risk_level: str
    critical_flags: int
    high_flags: int
    top_risks: List[str]

class TrendDataPoint(BaseModel):
    period: str
    date: str
    overall_score: float
    awareness_score: float
    behavior_score: float
    reporting_score: float
    participation_rate: float
    responses_count: int
    risk_level: str

class TrendAnalysis(BaseModel):
    weekly_trends: List[TrendDataPoint]
    monthly_trends: List[TrendDataPoint]
    score_change_weekly: float
    score_change_monthly: float
    trend_direction: str  # improving, declining, stable
    insights: List[str]

class BulkImportResult(BaseModel):
    total_processed: int
    successful: int
    failed: int
    errors: List[Dict[str, str]]
    employees_created: List[EmployeeResponse]

class DashboardStats(BaseModel):
    overall_score: float
    awareness_score: float
    behavior_score: float
    reporting_score: float
    participation_rate: float
    risk_level: str
    total_employees: int
    completed_surveys: int
    department_risks: Dict[str, Dict[str, Any]]
    risk_heatmap: Dict[str, float]
    # Enhanced risk metrics
    critical_risk_count: int = 0
    high_risk_employees: List[Dict[str, Any]] = []
    risk_distribution: Dict[str, int] = {}
    behavioral_red_flags: List[Dict[str, Any]] = []
    vulnerability_index: float = 0.0
    risk_trend_indicator: str = "stable"
    maturity_level: str = "Initial"
    maturity_summary: str = "Assessment pending"
    framework_note: str = ""
    aligned_domains: Dict[str, Any] = {}
    phishing_program: Dict[str, Any] = {}

class AuditReportResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    company_id: str
    report_content: Dict[str, Any]
    generated_at: str
    pdf_base64: Optional[str] = None

# ===================== SURVEY QUESTIONS =====================

SURVEY_QUESTIONS = [
    # Awareness Questions
    {"id": "q1", "category": "awareness", "question": "How confident are you in identifying a phishing email?", 
     "options": ["Not confident at all", "Somewhat confident", "Confident", "Very confident"], "risk_weight": 3},
    {"id": "q2", "category": "awareness", "question": "Do you know your organization's security policy?",
     "options": ["Never heard of it", "Heard of it but haven't read", "Read it once", "Know it well"], "risk_weight": 2},
    {"id": "q3", "category": "awareness", "question": "Have you received cybersecurity training in the past year?",
     "options": ["No", "Once", "Twice", "More than twice"], "risk_weight": 3},
    {"id": "q4", "category": "awareness", "question": "Can you identify social engineering tactics?",
     "options": ["Not at all", "A little", "Mostly", "Definitely"], "risk_weight": 3},
    
    # Password Behavior
    {"id": "q5", "category": "behavior", "question": "Do you reuse the same password for multiple accounts?",
     "options": ["Yes, for all accounts", "Yes, for some accounts", "Rarely", "Never"], "risk_weight": 4},
    {"id": "q6", "category": "behavior", "question": "Do you use a password manager?",
     "options": ["No", "Thinking about it", "Sometimes", "Always"], "risk_weight": 3},
    {"id": "q7", "category": "behavior", "question": "How often do you change your work passwords?",
     "options": ["Never", "When forced", "Every 6 months", "Every 3 months or more"], "risk_weight": 2},
    
    # Device Security
    {"id": "q8", "category": "behavior", "question": "Do you lock your computer when leaving your desk?",
     "options": ["Never", "Sometimes", "Usually", "Always"], "risk_weight": 3},
    {"id": "q9", "category": "behavior", "question": "Do you connect to public Wi-Fi without VPN?",
     "options": ["Always", "Often", "Rarely", "Never"], "risk_weight": 4},
    {"id": "q10", "category": "behavior", "question": "Do you keep your software and systems updated?",
     "options": ["Never", "When reminded", "Usually", "Automatically enabled"], "risk_weight": 3},
    
    # Phishing Awareness
    {"id": "q11", "category": "awareness", "question": "Would you click a link from an unknown sender offering a prize?",
     "options": ["Yes, definitely", "Maybe", "Probably not", "Never"], "risk_weight": 5},
    {"id": "q12", "category": "awareness", "question": "How do you verify if an email is legitimate?",
     "options": ["I don't verify", "Check if it looks official", "Check sender email", "Multiple verification steps"], "risk_weight": 4},
    
    # Incident Reporting
    {"id": "q13", "category": "reporting", "question": "Would you report a suspicious email to IT?",
     "options": ["No", "Only if I'm sure it's bad", "Probably", "Definitely"], "risk_weight": 3},
    {"id": "q14", "category": "reporting", "question": "Do you know how to report a security incident?",
     "options": ["No idea", "Have a vague idea", "Know the process", "Have used it before"], "risk_weight": 3},
    {"id": "q15", "category": "reporting", "question": "Have you ever reported a security concern?",
     "options": ["Never", "Once", "A few times", "Regularly when needed"], "risk_weight": 2},
    
    # Security Policy Attitude
    {"id": "q16", "category": "behavior", "question": "Do you follow security policies even when inconvenient?",
     "options": ["Rarely", "Sometimes", "Usually", "Always"], "risk_weight": 3},
    {"id": "q17", "category": "behavior", "question": "Do you share your work credentials with colleagues?",
     "options": ["Yes, often", "Sometimes", "Rarely", "Never"], "risk_weight": 5},
    {"id": "q18", "category": "awareness", "question": "Do you understand the risks of data breaches to the company?",
     "options": ["Not really", "Somewhat", "Pretty well", "Very well"], "risk_weight": 2},
]

# ===================== UTILITY FUNCTIONS =====================

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)

def build_app_base_url(request: Request) -> str:
    # With split hosting the API and the web app live on different domains,
    # so emailed links (reset, survey, payment) must point at the web app.
    configured = os.environ.get("FRONTEND_URL", "").strip()
    if configured:
        return configured.rstrip("/")
    return str(request.base_url).rstrip("/")

def schedule_email_task(coro) -> None:
    try:
        asyncio.create_task(coro)
    except Exception as exc:
        logger.error("Failed to schedule email task: %s", str(exc))

def build_company_response(company: dict) -> CompanyResponse:
    return CompanyResponse(
        id=company["id"],
        company_name=company["company_name"],
        email=company["email"],
        created_at=company["created_at"],
        mfa_enabled=company.get("mfa_enabled", False),
        mfa_enforced=company.get("mfa_enforced", True),
    )

async def get_current_company(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    try:
        token = credentials.credentials
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        company_id = payload.get("sub")
        session_id = payload.get("sid")
        if company_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        if session_id is None:
            raise HTTPException(status_code=401, detail="Session expired. Please sign in again.")
        session = await db.auth_sessions.find_one({"id": session_id, "company_id": company_id, "revoked_at": None}, {"_id": 0})
        if session is None:
            raise HTTPException(status_code=401, detail="Session expired. Please sign in again.")
        await db.auth_sessions.update_one({"id": session_id}, {"$set": {"last_active_at": datetime.now(timezone.utc).isoformat()}})
        company = await db.companies.find_one({"id": company_id}, {"_id": 0})
        if company is None:
            raise HTTPException(status_code=401, detail="Company not found")
        company["current_session_id"] = session_id
        return company
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")


def build_phishing_campaign_response(campaign: dict, recipients: List[dict]) -> PhishingCampaignResponse:
    delivered_count = sum(1 for recipient in recipients if recipient.get("delivery_status") == "sent")
    opened_count = sum(1 for recipient in recipients if recipient.get("opened_at"))
    clicked_count = sum(1 for recipient in recipients if recipient.get("clicked_at"))
    reported_count = sum(1 for recipient in recipients if recipient.get("reported_at"))
    template = get_phishing_template(campaign["template_id"])

    return PhishingCampaignResponse(
        id=campaign["id"],
        name=campaign["name"],
        template_id=campaign["template_id"],
        template_name=str(template["name"]),
        status=campaign.get("status", "draft"),
        total_targets=len(recipients),
        delivered_count=delivered_count,
        opened_count=opened_count,
        clicked_count=clicked_count,
        reported_count=reported_count,
        created_at=campaign["created_at"],
        sent_at=campaign.get("sent_at"),
        recipients=[PhishingRecipientResponse(**recipient) for recipient in recipients],
    )


async def get_phishing_campaign_or_404(campaign_id: str, company_id: str) -> dict:
    campaign = await db.phishing_campaigns.find_one({"id": campaign_id, "company_id": company_id}, {"_id": 0})
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return campaign


async def send_phishing_campaign_messages(campaign: dict, company: dict, request: Request) -> PhishingCampaignResponse:
    recipients = await db.phishing_campaign_recipients.find(
        {"campaign_id": campaign["id"], "company_id": company["id"]},
        {"_id": 0}
    ).to_list(5000)

    base_url = build_app_base_url(request)
    any_sent = False
    any_failed = False
    send_started_at = datetime.now(timezone.utc).isoformat()

    for recipient in recipients:
        if recipient.get("delivery_status") == "sent":
            continue

        landing_url = f"{base_url}/phishing/simulation/{recipient['tracking_token']}"
        open_pixel_url = f"{base_url}/api/phishing/track/open/{recipient['tracking_token']}"
        rendered_email = render_phishing_email(
            campaign["template_id"],
            recipient["employee_name"],
            company["company_name"],
            landing_url,
            open_pixel_url,
        )

        result = await send_phishing_simulation_email(
            recipient_email=recipient["employee_email"],
            subject=rendered_email["subject"],
            html_content=rendered_email["html"],
            company_id=company["id"],
            metadata={
                "campaign_id": campaign["id"],
                "campaign_name": campaign["name"],
                "employee_id": recipient["employee_id"],
                "template_id": campaign["template_id"],
            },
        )

        delivery_status = "sent" if result.get("status") == "sent" else "failed"
        any_sent = any_sent or delivery_status == "sent"
        any_failed = any_failed or delivery_status == "failed"
        sent_at_value = datetime.now(timezone.utc).isoformat() if delivery_status == "sent" else None

        await db.phishing_campaign_recipients.update_one(
            {"id": recipient["id"]},
            {"$set": {
                "delivery_status": delivery_status,
                "delivery_error": result.get("error"),
                "provider_message_id": result.get("email_id"),
                "sent_at": sent_at_value,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }}
        )

    new_status = "sent" if any_sent and not any_failed else "partially_sent" if any_sent and any_failed else "failed"
    await db.phishing_campaigns.update_one(
        {"id": campaign["id"]},
        {"$set": {"status": new_status, "sent_at": send_started_at, "updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    refreshed_campaign = await get_phishing_campaign_or_404(campaign["id"], company["id"])
    refreshed_recipients = await db.phishing_campaign_recipients.find(
        {"campaign_id": campaign["id"], "company_id": company["id"]},
        {"_id": 0}
    ).sort("employee_name", 1).to_list(5000)
    return build_phishing_campaign_response(refreshed_campaign, refreshed_recipients)

# ===================== ENHANCED RISK DETECTION SYSTEM =====================

# Critical risk behaviors - these are red flags that require immediate attention
CRITICAL_RISK_BEHAVIORS = {
    "q5": {  # Password reuse
        "trigger_values": [0, 1],  # "Yes, for all accounts" or "Yes, for some accounts"
        "severity": "critical",
        "title": "Password Reuse Detected",
        "description": "Employee reuses passwords across multiple accounts, creating a critical security vulnerability",
        "recommendation": "Implement mandatory password manager training and enforce unique password policies"
    },
    "q11": {  # Would click unknown links
        "trigger_values": [0, 1],  # "Yes, definitely" or "Maybe"
        "severity": "critical",
        "title": "High Phishing Susceptibility",
        "description": "Employee likely to click on malicious links from unknown senders",
        "recommendation": "Prioritize phishing awareness training and conduct simulated phishing exercises"
    },
    "q17": {  # Credential sharing
        "trigger_values": [0, 1],  # "Yes, often" or "Sometimes"
        "severity": "critical",
        "title": "Credential Sharing Practice",
        "description": "Employee shares work credentials with colleagues, violating security protocols",
        "recommendation": "Enforce strict credential policies and implement role-based access controls"
    },
    "q9": {  # Public WiFi without VPN
        "trigger_values": [0, 1],  # "Always" or "Often"
        "severity": "high",
        "title": "Unsecured Network Usage",
        "description": "Employee frequently uses public WiFi without VPN protection",
        "recommendation": "Mandate VPN usage for remote work and provide VPN training"
    },
    "q12": {  # Email verification
        "trigger_values": [0],  # "I don't verify"
        "severity": "high",
        "title": "No Email Verification Practice",
        "description": "Employee does not verify email legitimacy before acting",
        "recommendation": "Train on email verification techniques and implement email security tools"
    },
    "q8": {  # Computer locking
        "trigger_values": [0],  # "Never"
        "severity": "high",
        "title": "Device Security Negligence",
        "description": "Employee never locks computer when leaving desk",
        "recommendation": "Implement automatic screen lock policies and security awareness training"
    },
    "q13": {  # Incident reporting
        "trigger_values": [0],  # "No"
        "severity": "high",
        "title": "Non-Reporter Profile",
        "description": "Employee would not report suspicious emails to IT",
        "recommendation": "Establish clear reporting channels and incentivize security reporting"
    }
}

# Risk weight multipliers based on question criticality
RISK_WEIGHT_MULTIPLIERS = {
    "q5": 2.5,   # Password reuse - very critical
    "q11": 2.5,  # Phishing clicks - very critical
    "q17": 2.5,  # Credential sharing - very critical
    "q9": 2.0,   # Public WiFi - critical
    "q12": 2.0,  # Email verification - critical
    "q1": 1.5,   # Phishing confidence
    "q4": 1.5,   # Social engineering awareness
    "q8": 1.8,   # Device locking
    "q13": 1.5,  # Incident reporting willingness
    "q16": 1.3,  # Policy compliance
}

FRAMEWORK_NOTE = (
    "This CultureShield assessment maps workforce awareness and human security behaviors to "
    "ISO/IEC 27001:2022 people and awareness controls and NIST Cybersecurity Framework functions "
    "as guidance only. It is not a formal certification or compliance attestation."
)

MATURITY_BANDS = [
    {
        "level": "Initial",
        "minimum": 0,
        "description": "Security awareness is mostly ad hoc, reactive, and inconsistently reinforced across the workforce.",
        "next_focus": "Establish baseline awareness, clear reporting channels, and repeatable awareness practices.",
    },
    {
        "level": "Developing",
        "minimum": 35,
        "description": "Core practices exist, but staff behavior and reporting habits still depend on reminders and isolated training moments.",
        "next_focus": "Move from one-off training to role-relevant routines, simulations, and stronger reinforcement.",
    },
    {
        "level": "Defined",
        "minimum": 50,
        "description": "Awareness and human security controls are documented and repeatable, with growing employee understanding of expected behaviors.",
        "next_focus": "Tighten behavior change, verify controls through exercises, and build management evidence.",
    },
    {
        "level": "Managed",
        "minimum": 65,
        "description": "The organization measures behavior, reinforces expectations, and uses evidence to steer awareness and response improvements.",
        "next_focus": "Optimize for proactive reinforcement, role-based learning, and board-ready metrics.",
    },
    {
        "level": "Adaptive",
        "minimum": 80,
        "description": "Security culture is continuously measured, reinforced, and adjusted using human-risk evidence and management oversight.",
        "next_focus": "Sustain continuous improvement and keep human-risk monitoring aligned with business change.",
    },
]

FRAMEWORK_CONTROL_DOMAINS = {
    "govern_awareness": {
        "label": "Governance & Awareness",
        "weight": 0.20,
        "iso_reference": "ISO/IEC 27001:2022 Annex A 6.3, 6.4",
        "nist_reference": "NIST CSF Govern / Protect",
        "focus": "Security policy knowledge, awareness training, and security responsibility understanding.",
        "question_ids": ["q2", "q3", "q16", "q18"],
    },
    "protect_secure_behavior": {
        "label": "Protective Behavior",
        "weight": 0.35,
        "iso_reference": "ISO/IEC 27001:2022 Annex A 6.7, 6.8",
        "nist_reference": "NIST CSF Protect",
        "focus": "Password hygiene, remote-work protection, secure device use, and day-to-day policy-compliant behavior.",
        "question_ids": ["q5", "q6", "q7", "q8", "q9", "q10", "q17"],
    },
    "detect_verify": {
        "label": "Threat Recognition & Verification",
        "weight": 0.20,
        "iso_reference": "ISO/IEC 27001:2022 Annex A 6.3",
        "nist_reference": "NIST CSF Detect / Protect",
        "focus": "Recognizing phishing, social engineering, and suspicious content before taking action.",
        "question_ids": ["q1", "q4", "q11", "q12"],
    },
    "respond_report": {
        "label": "Reporting & Response Readiness",
        "weight": 0.25,
        "iso_reference": "ISO/IEC 27001:2022 Annex A 6.8, 5.24",
        "nist_reference": "NIST CSF Respond",
        "focus": "Willingness to report, knowledge of reporting channels, and fast human escalation of suspicious activity.",
        "question_ids": ["q13", "q14", "q15"],
    },
}

def clamp_score(value: float) -> float:
    return round(max(0, min(100, value)), 1)


def get_maturity_band(score: float) -> Dict[str, str]:
    selected_band = MATURITY_BANDS[0]
    for band in MATURITY_BANDS:
        if score >= band["minimum"]:
            selected_band = band
    return {
        "level": selected_band["level"],
        "description": selected_band["description"],
        "next_focus": selected_band["next_focus"],
    }


def determine_company_risk_level(score: float, critical_count: int) -> str:
    if critical_count >= 3:
        return "Critical"
    if critical_count >= 2 or score < 35:
        return "High"
    if score < 50:
        return "Medium-High"
    if score < 65:
        return "Medium"
    if score < 80:
        return "Low-Medium"
    return "Low"


def calculate_framework_domain_scores(responses: Dict[str, int]) -> Dict[str, Any]:
    domain_scores: Dict[str, Any] = {}

    for domain_key, domain in FRAMEWORK_CONTROL_DOMAINS.items():
        weighted_total = 0.0
        weight_sum = 0.0
        measured_questions = []

        for qid in domain["question_ids"]:
            if qid not in responses:
                continue

            question = next((item for item in SURVEY_QUESTIONS if item["id"] == qid), None)
            if not question:
                continue

            raw_score = (responses[qid] / 3) * 100
            weight = question["risk_weight"] * RISK_WEIGHT_MULTIPLIERS.get(qid, 1.0)
            weighted_total += raw_score * weight
            weight_sum += weight
            measured_questions.append(qid)

        score = weighted_total / weight_sum if weight_sum > 0 else 0
        maturity = get_maturity_band(score)
        domain_scores[domain_key] = {
            "label": domain["label"],
            "score": clamp_score(score),
            "maturity_level": maturity["level"],
            "maturity_summary": maturity["description"],
            "iso_reference": domain["iso_reference"],
            "nist_reference": domain["nist_reference"],
            "focus": domain["focus"],
            "questions_assessed": measured_questions,
        }

    return domain_scores


def calculate_framework_overall_score(domain_scores: Dict[str, Any]) -> float:
    weighted_total = 0.0
    total_weight = 0.0

    for domain_key, domain in FRAMEWORK_CONTROL_DOMAINS.items():
        domain_score = domain_scores.get(domain_key, {}).get("score")
        if domain_score is None:
            continue
        weighted_total += domain_score * domain["weight"]
        total_weight += domain["weight"]

    return clamp_score(weighted_total / total_weight) if total_weight else 0.0


def aggregate_framework_domain_scores(responses_list: List[dict]) -> Dict[str, Any]:
    if not responses_list:
        return {}

    aggregated: Dict[str, Dict[str, Any]] = {}
    for response in responses_list:
        response_domains = response.get("framework_domains") or calculate_framework_domain_scores(response.get("responses", {}))
        for domain_key, domain_info in response_domains.items():
            if domain_key not in aggregated:
                aggregated[domain_key] = {
                    "label": domain_info["label"],
                    "iso_reference": domain_info["iso_reference"],
                    "nist_reference": domain_info["nist_reference"],
                    "focus": domain_info["focus"],
                    "scores": [],
                }
            aggregated[domain_key]["scores"].append(domain_info.get("score", 0))

    result = {}
    for domain_key, item in aggregated.items():
        average_score = sum(item["scores"]) / len(item["scores"]) if item["scores"] else 0
        maturity = get_maturity_band(average_score)
        result[domain_key] = {
            "label": item["label"],
            "score": clamp_score(average_score),
            "maturity_level": maturity["level"],
            "maturity_summary": maturity["description"],
            "iso_reference": item["iso_reference"],
            "nist_reference": item["nist_reference"],
            "focus": item["focus"],
        }

    return result

def detect_risk_flags(responses: Dict[str, int]) -> List[Dict[str, Any]]:
    """Detect critical and high-risk behaviors from responses"""
    flags = []
    
    for question_id, behavior_config in CRITICAL_RISK_BEHAVIORS.items():
        if question_id in responses:
            response_value = responses[question_id]
            if response_value in behavior_config["trigger_values"]:
                flags.append({
                    "flag_id": f"flag_{question_id}",
                    "question_id": question_id,
                    "severity": behavior_config["severity"],
                    "title": behavior_config["title"],
                    "description": behavior_config["description"],
                    "recommendation": behavior_config["recommendation"],
                    "response_value": response_value
                })
    
    return flags

def calculate_risk_profile(responses: Dict[str, int], risk_flags: List[Dict]) -> Dict[str, Any]:
    """Generate comprehensive risk profile for an employee"""
    
    # Count flags by severity
    critical_count = sum(1 for f in risk_flags if f["severity"] == "critical")
    high_count = sum(1 for f in risk_flags if f["severity"] == "high")
    
    # Calculate behavioral risk indicators
    password_risk = 0
    phishing_risk = 0
    device_risk = 0
    compliance_risk = 0
    reporting_risk = 0
    
    # Password security (q5, q6, q7)
    if "q5" in responses:
        password_risk += (3 - responses["q5"]) * 33.3
    if "q6" in responses:
        password_risk += (3 - responses["q6"]) * 16.7
    if "q7" in responses:
        password_risk += (3 - responses["q7"]) * 16.7
    
    # Phishing susceptibility (q1, q4, q11, q12)
    if "q11" in responses:
        phishing_risk += (3 - responses["q11"]) * 35
    if "q12" in responses:
        phishing_risk += (3 - responses["q12"]) * 25
    if "q1" in responses:
        phishing_risk += (3 - responses["q1"]) * 20
    if "q4" in responses:
        phishing_risk += (3 - responses["q4"]) * 20
    
    # Device security (q8, q9, q10)
    if "q8" in responses:
        device_risk += (3 - responses["q8"]) * 40
    if "q9" in responses:
        device_risk += (3 - responses["q9"]) * 40
    if "q10" in responses:
        device_risk += (3 - responses["q10"]) * 20
    
    # Policy compliance (q16, q17, q2)
    if "q17" in responses:
        compliance_risk += (3 - responses["q17"]) * 50
    if "q16" in responses:
        compliance_risk += (3 - responses["q16"]) * 30
    if "q2" in responses:
        compliance_risk += (3 - responses["q2"]) * 20
    
    # Reporting culture (q13, q14, q15)
    if "q13" in responses:
        reporting_risk += (3 - responses["q13"]) * 40
    if "q14" in responses:
        reporting_risk += (3 - responses["q14"]) * 35
    if "q15" in responses:
        reporting_risk += (3 - responses["q15"]) * 25
    
    # Determine risk persona
    risk_scores = {
        "password_risk": min(100, password_risk),
        "phishing_risk": min(100, phishing_risk),
        "device_risk": min(100, device_risk),
        "compliance_risk": min(100, compliance_risk),
        "reporting_risk": min(100, reporting_risk)
    }
    
    # Find highest risk area
    highest_risk_area = max(risk_scores, key=risk_scores.get)
    
    # Assign risk persona based on patterns
    if critical_count >= 2:
        persona = "Critical Risk"
        persona_description = "Multiple critical security vulnerabilities detected. Immediate intervention required."
    elif critical_count == 1 and high_count >= 2:
        persona = "High Risk"
        persona_description = "Significant security gaps present. Priority training recommended."
    elif phishing_risk > 70:
        persona = "Phishing Target"
        persona_description = "Highly susceptible to phishing and social engineering attacks."
    elif password_risk > 70:
        persona = "Password Liability"
        persona_description = "Poor password hygiene creates credential compromise risk."
    elif compliance_risk > 70:
        persona = "Policy Violator"
        persona_description = "Tendency to bypass security policies for convenience."
    elif device_risk > 60:
        persona = "Device Risk"
        persona_description = "Physical and device security practices need improvement."
    elif reporting_risk > 60:
        persona = "Silent Observer"
        persona_description = "Unlikely to report security incidents, enabling threats to persist."
    else:
        persona = "Security Aware"
        persona_description = "Generally follows security best practices with minor improvement areas."
    
    return {
        "risk_persona": persona,
        "persona_description": persona_description,
        "critical_flags": critical_count,
        "high_flags": high_count,
        "risk_scores": risk_scores,
        "highest_risk_area": highest_risk_area.replace("_", " ").title(),
        "vulnerability_index": round((password_risk * 0.25 + phishing_risk * 0.30 + device_risk * 0.15 + compliance_risk * 0.20 + reporting_risk * 0.10), 1)
    }

def calculate_enhanced_scores(responses: Dict[str, int]) -> Dict[str, Any]:
    """Enhanced scoring with weighted calculations and risk detection"""
    categories = {"awareness": [], "behavior": [], "reporting": []}
    weighted_scores = {"awareness": 0, "behavior": 0, "reporting": 0}
    weight_sums = {"awareness": 0, "behavior": 0, "reporting": 0}
    
    for q in SURVEY_QUESTIONS:
        qid = q["id"]
        if qid in responses:
            option_idx = responses[qid]
            base_weight = q["risk_weight"]
            multiplier = RISK_WEIGHT_MULTIPLIERS.get(qid, 1.0)
            
            # Calculate weighted score (0-100 scale)
            raw_score = (option_idx / 3) * 100
            weighted_score = raw_score * base_weight * multiplier
            
            categories[q["category"]].append(raw_score)
            weighted_scores[q["category"]] += weighted_score
            weight_sums[q["category"]] += base_weight * multiplier
    
    # Calculate weighted averages
    awareness_score = weighted_scores["awareness"] / weight_sums["awareness"] if weight_sums["awareness"] > 0 else 0
    behavior_score = weighted_scores["behavior"] / weight_sums["behavior"] if weight_sums["behavior"] > 0 else 0
    reporting_score = weighted_scores["reporting"] / weight_sums["reporting"] if weight_sums["reporting"] > 0 else 0
    
    # Detect risk flags
    risk_flags = detect_risk_flags(responses)
    framework_domain_scores = calculate_framework_domain_scores(responses)
    aligned_overall_score = calculate_framework_overall_score(framework_domain_scores)
    
    # Apply penalty for critical flags (each critical flag reduces score)
    critical_count = sum(1 for f in risk_flags if f["severity"] == "critical")
    high_count = sum(1 for f in risk_flags if f["severity"] == "high")
    
    # Penalty calculation: critical flags have more impact
    penalty = (critical_count * 8) + (high_count * 4)
    
    # Weighted overall score with penalties
    overall_score = max(0, aligned_overall_score - penalty)
    maturity_band = get_maturity_band(overall_score)
    risk_level = determine_company_risk_level(overall_score, critical_count)
    
    # Calculate risk profile
    risk_profile = calculate_risk_profile(responses, risk_flags)
    
    return {
        "awareness_score": round(awareness_score, 1),
        "behavior_score": round(behavior_score, 1),
        "reporting_score": round(reporting_score, 1),
        "overall_score": round(overall_score, 1),
        "risk_level": risk_level,
        "risk_flags": risk_flags,
        "risk_profile": risk_profile,
        "penalty_applied": penalty,
        "maturity_level": maturity_band["level"],
        "maturity_summary": maturity_band["description"],
        "maturity_next_focus": maturity_band["next_focus"],
        "framework_domain_scores": framework_domain_scores,
        "framework_note": FRAMEWORK_NOTE,
    }

def calculate_scores(responses: Dict[str, int]) -> Dict[str, Any]:
    """Calculate all scores from survey responses - enhanced version"""
    return calculate_enhanced_scores(responses)

def calculate_risk_heatmap(responses_list: List[dict]) -> Dict[str, float]:
    """Calculate enhanced risk heatmap from all responses"""
    heatmap = {
        "password_reuse": 0,
        "phishing_susceptibility": 0,
        "device_security": 0,
        "incident_reporting": 0,
        "policy_compliance": 0,
        "social_engineering": 0,
        "credential_hygiene": 0
    }
    
    if not responses_list:
        return heatmap
    
    count = len(responses_list)
    
    for resp in responses_list:
        r = resp.get("responses", {})
        
        # Password reuse risk (q5) - inverted: higher = more risk
        if "q5" in r:
            heatmap["password_reuse"] += ((3 - r["q5"]) / 3) * 100
        
        # Phishing susceptibility (q11, q12) - combined score
        phishing_score = 0
        phishing_count = 0
        if "q11" in r:
            phishing_score += ((3 - r["q11"]) / 3) * 100
            phishing_count += 1
        if "q12" in r:
            phishing_score += ((3 - r["q12"]) / 3) * 100
            phishing_count += 1
        if phishing_count > 0:
            heatmap["phishing_susceptibility"] += phishing_score / phishing_count
        
        # Device security (q8, q9, q10) - combined
        device_score = 0
        device_count = 0
        if "q8" in r:
            device_score += ((3 - r["q8"]) / 3) * 100
            device_count += 1
        if "q9" in r:
            device_score += ((3 - r["q9"]) / 3) * 100
            device_count += 1
        if "q10" in r:
            device_score += ((3 - r["q10"]) / 3) * 100
            device_count += 1
        if device_count > 0:
            heatmap["device_security"] += device_score / device_count
        
        # Incident reporting (q13, q14, q15) - combined
        reporting_score = 0
        reporting_count = 0
        if "q13" in r:
            reporting_score += ((3 - r["q13"]) / 3) * 100
            reporting_count += 1
        if "q14" in r:
            reporting_score += ((3 - r["q14"]) / 3) * 100
            reporting_count += 1
        if "q15" in r:
            reporting_score += ((3 - r["q15"]) / 3) * 100
            reporting_count += 1
        if reporting_count > 0:
            heatmap["incident_reporting"] += reporting_score / reporting_count
        
        # Policy compliance (q16, q17)
        compliance_score = 0
        compliance_count = 0
        if "q16" in r:
            compliance_score += ((3 - r["q16"]) / 3) * 100
            compliance_count += 1
        if "q17" in r:
            compliance_score += ((3 - r["q17"]) / 3) * 100
            compliance_count += 1
        if compliance_count > 0:
            heatmap["policy_compliance"] += compliance_score / compliance_count
        
        # Social engineering awareness (q1, q4)
        se_score = 0
        se_count = 0
        if "q1" in r:
            se_score += ((3 - r["q1"]) / 3) * 100
            se_count += 1
        if "q4" in r:
            se_score += ((3 - r["q4"]) / 3) * 100
            se_count += 1
        if se_count > 0:
            heatmap["social_engineering"] += se_score / se_count
        
        # Credential hygiene (q5, q6, q7, q17)
        cred_score = 0
        cred_count = 0
        for qid in ["q5", "q6", "q7", "q17"]:
            if qid in r:
                cred_score += ((3 - r[qid]) / 3) * 100
                cred_count += 1
        if cred_count > 0:
            heatmap["credential_hygiene"] += cred_score / cred_count
    
    return {k: round(v / count, 1) for k, v in heatmap.items()}


async def calculate_phishing_program_posture(company_id: str) -> Dict[str, Any]:
    recipients = await db.phishing_campaign_recipients.find(
        {"company_id": company_id, "sent_at": {"$ne": None}},
        {"_id": 0}
    ).to_list(10000)

    if not recipients:
        return {
            "measured": False,
            "open_rate": None,
            "click_rate": None,
            "report_rate": None,
            "resilience_score": None,
            "score_modifier": 0.0,
            "summary": "Phishing simulation evidence has not been captured yet, so maturity is based on survey evidence only.",
        }

    total = len(recipients)
    opened = sum(1 for recipient in recipients if recipient.get("opened_at"))
    clicked = sum(1 for recipient in recipients if recipient.get("clicked_at"))
    reported = sum(1 for recipient in recipients if recipient.get("reported_at"))

    open_rate = round((opened / total) * 100, 1)
    click_rate = round((clicked / total) * 100, 1)
    report_rate = round((reported / total) * 100, 1)
    resilience_score = clamp_score(((100 - click_rate) * 0.65) + (report_rate * 0.35))
    score_modifier = round((resilience_score - 50) * 0.12, 1)

    if click_rate >= 35:
        summary = "Phishing exercise results show a material click-through problem that should be treated as a priority human-risk signal."
    elif report_rate >= click_rate:
        summary = "Phishing exercise results show healthy reporting behavior and improving human detection capability."
    else:
        summary = "Phishing exercise results indicate mixed resilience: some users detect the lure, but reporting behavior should improve faster than click behavior."

    return {
        "measured": True,
        "open_rate": open_rate,
        "click_rate": click_rate,
        "report_rate": report_rate,
        "resilience_score": resilience_score,
        "score_modifier": score_modifier,
        "summary": summary,
    }

def identify_high_risk_employees(employees: List[dict], responses: List[dict]) -> List[Dict[str, Any]]:
    """Identify employees with critical/high risk profiles"""
    high_risk_list = []
    
    employee_map = {e["id"]: e for e in employees}
    
    for resp in responses:
        emp_id = resp.get("employee_id")
        if emp_id not in employee_map:
            continue
        
        emp = employee_map[emp_id]
        risk_profile = resp.get("risk_profile", {})
        risk_flags = resp.get("risk_flags", [])
        
        critical_count = risk_profile.get("critical_flags", 0)
        high_count = risk_profile.get("high_flags", 0)
        
        # Include if has any critical flags or multiple high flags
        if critical_count > 0 or high_count >= 2:
            top_risks = [f["title"] for f in risk_flags[:3]]
            
            high_risk_list.append({
                "employee_id": emp_id,
                "name": emp.get("name", "Unknown"),
                "department": emp.get("department", "Unknown"),
                "overall_score": resp.get("overall_score", 0),
                "risk_level": resp.get("risk_level", "Unknown"),
                "risk_persona": risk_profile.get("risk_persona", "Unknown"),
                "critical_flags": critical_count,
                "high_flags": high_count,
                "vulnerability_index": risk_profile.get("vulnerability_index", 0),
                "top_risks": top_risks
            })
    
    # Sort by vulnerability index (highest first)
    high_risk_list.sort(key=lambda x: x.get("vulnerability_index", 0), reverse=True)
    
    return high_risk_list[:10]  # Top 10 highest risk

def aggregate_behavioral_red_flags(responses: List[dict]) -> List[Dict[str, Any]]:
    """Aggregate common red flags across all employees"""
    flag_counts = {}
    
    for resp in responses:
        risk_flags = resp.get("risk_flags", [])
        for flag in risk_flags:
            flag_id = flag.get("flag_id")
            if flag_id not in flag_counts:
                flag_counts[flag_id] = {
                    "flag_id": flag_id,
                    "title": flag.get("title"),
                    "severity": flag.get("severity"),
                    "description": flag.get("description"),
                    "recommendation": flag.get("recommendation"),
                    "affected_count": 0,
                    "percentage": 0
                }
            flag_counts[flag_id]["affected_count"] += 1
    
    total = len(responses) if responses else 1
    
    # Calculate percentages and sort by severity and count
    red_flags = list(flag_counts.values())
    for flag in red_flags:
        flag["percentage"] = round((flag["affected_count"] / total) * 100, 1)
    
    # Sort: critical first, then by affected count
    severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    red_flags.sort(key=lambda x: (severity_order.get(x["severity"], 4), -x["affected_count"]))
    
    return red_flags

# ===================== AUTH ROUTES =====================

@api_router.post("/auth/register", response_model=TokenResponse)
async def register_company(data: CompanyCreate, request: Request):
    password_error = validate_password_strength(data.password)
    if password_error:
        raise HTTPException(status_code=400, detail=password_error)

    normalized_email = data.email.lower()

    # Check if company exists
    existing = await db.companies.find_one({"email": normalized_email})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    company_id = str(uuid.uuid4())
    company = {
        "id": company_id,
        "company_name": data.company_name,
        "email": normalized_email,
        "password_hash": hash_password(data.password),
        "mfa_enabled": False,
        "mfa_enforced": True,
        "mfa_secret_encrypted": None,
        "mfa_backup_codes": [],
        "mfa_temp_secret_encrypted": None,
        "mfa_temp_backup_codes": [],
        "password_updated_at": datetime.now(timezone.utc).isoformat(),
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.companies.insert_one(company)

    await db.subscriptions.update_one(
        {"company_id": company_id},
        {
            "$set": {
                "id": str(uuid.uuid4()),
                "company_id": company_id,
                "paystack_customer_code": None,
                "paystack_subscription_code": None,
                "paystack_email_token": None,
                "plan_id": "free",
                "status": "active",
                "current_period_start": company["created_at"],
                "current_period_end": (datetime.now(timezone.utc) + timedelta(days=36500)).isoformat(),
                "cancel_at_period_end": False,
                "trial_start": None,
                "trial_end": None,
                "metadata": {"source": "registration_default"},
                "created_at": company["created_at"],
                "updated_at": company["created_at"],
            }
        },
        upsert=True,
    )

    schedule_email_task(
        send_welcome_email(
            company_name=data.company_name,
            recipient_email=normalized_email,
            dashboard_url=f"{build_app_base_url(request)}/dashboard",
            company_id=company_id,
        )
    )

    await log_auth_event(db, "register.success", "success", normalized_email, company_id, get_request_ip(request), {"company_name": data.company_name})
    
    session_id = await create_auth_session(db, company_id, request, mfa_verified=False)
    access_token = create_access_token({"sub": company_id, "sid": session_id})
    
    return TokenResponse(
        access_token=access_token,
        company=build_company_response(company)
    )

@api_router.post("/auth/login", response_model=CompanyLoginResponse)
async def login_company(data: CompanyLogin, request: Request):
    normalized_email = data.email.lower()
    ip_address = get_request_ip(request)
    await enforce_auth_rate_limit(db, normalized_email, ip_address, "login")

    company = await db.companies.find_one({"email": normalized_email}, {"_id": 0})
    if not company or not verify_password(data.password, company["password_hash"]):
        await log_auth_event(db, "login.failed", "failed", normalized_email, company.get("id") if company else None, ip_address, {"reason": "invalid_credentials"})
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if company.get("mfa_enabled"):
        challenge_token = await create_mfa_login_challenge(db, company["id"], company["email"])
        await log_auth_event(db, "login.mfa_required", "success", normalized_email, company["id"], ip_address, {})
        return CompanyLoginResponse(mfa_required=True, mfa_token=challenge_token)
    
    session_id = await create_auth_session(db, company["id"], request, mfa_verified=False)
    access_token = create_access_token({"sub": company["id"], "sid": session_id})
    await log_auth_event(db, "login.success", "success", normalized_email, company["id"], ip_address, {"mfa_enabled": company.get("mfa_enabled", False)})
    
    return CompanyLoginResponse(
        access_token=access_token,
        company=build_company_response(company),
        mfa_setup_required=company.get("mfa_enforced", True) and not company.get("mfa_enabled", False),
    )

@api_router.post("/auth/mfa/verify-login", response_model=TokenResponse)
async def verify_mfa_login(data: VerifyMFALoginRequest, request: Request):
    ip_address = get_request_ip(request)
    challenge = await get_valid_mfa_login_challenge(db, data.mfa_token)
    if not challenge:
        raise HTTPException(status_code=400, detail="The verification request is invalid or expired.")

    await enforce_auth_rate_limit(db, challenge["email"], ip_address, "mfa")
    company = await db.companies.find_one({"id": challenge["company_id"]}, {"_id": 0})
    if not company or not company.get("mfa_secret_encrypted"):
        raise HTTPException(status_code=400, detail="MFA is not configured for this account.")

    decrypted_secret = decrypt_sensitive_value(company["mfa_secret_encrypted"])
    is_valid = verify_totp_code(decrypted_secret, data.code)
    updated_backup_codes = None

    if not is_valid:
        updated_backup_codes = consume_backup_code(data.code, company.get("mfa_backup_codes", []))
        is_valid = updated_backup_codes is not None

    if not is_valid:
        await log_auth_event(db, "mfa.failed", "failed", challenge["email"], company["id"], ip_address, {"reason": "invalid_code"})
        raise HTTPException(status_code=401, detail="Invalid verification code")

    if updated_backup_codes is not None:
        await db.companies.update_one({"id": company["id"]}, {"$set": {"mfa_backup_codes": updated_backup_codes}})
        company["mfa_backup_codes"] = updated_backup_codes

    await db.mfa_login_challenges.update_one({"id": challenge["id"]}, {"$set": {"used_at": datetime.now(timezone.utc).isoformat()}})
    await log_auth_event(db, "mfa.success", "success", challenge["email"], company["id"], ip_address, {"used_backup_code": updated_backup_codes is not None})

    session_id = await create_auth_session(db, company["id"], request, mfa_verified=True)
    access_token = create_access_token({"sub": company["id"], "sid": session_id})
    return TokenResponse(access_token=access_token, company=build_company_response(company))

@api_router.post("/auth/logout")
async def logout_current_session(company: dict = Depends(get_current_company)):
    current_session_id = company.get("current_session_id")
    if current_session_id:
        await revoke_auth_session(db, current_session_id)
        await log_auth_event(db, "session.logout", "success", company["email"], company["id"], "authenticated-user", {"session_id": current_session_id})
    return {"message": "Logged out successfully."}

@api_router.get("/auth/mfa/status", response_model=MFAStatusResponse)
async def get_mfa_status(company: dict = Depends(get_current_company)):
    return MFAStatusResponse(
        enabled=company.get("mfa_enabled", False),
        enforced=company.get("mfa_enforced", True),
        backup_codes_remaining=get_remaining_backup_codes(company.get("mfa_backup_codes", [])),
    )

@api_router.post("/auth/mfa/setup/init", response_model=MFASetupInitResponse)
async def init_mfa_setup(company: dict = Depends(get_current_company)):
    setup = create_totp_setup(company["email"])
    backup_codes = generate_backup_codes()

    await db.companies.update_one(
        {"id": company["id"]},
        {"$set": {
            "mfa_temp_secret_encrypted": encrypt_sensitive_value(setup["secret"]),
            "mfa_temp_backup_codes": hash_backup_codes(backup_codes),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }}
    )

    await log_auth_event(db, "mfa.setup_init", "success", company["email"], company["id"], "authenticated-user", {})
    return MFASetupInitResponse(qr_code_data_url=setup["qr_code_data_url"], manual_entry_key=setup["secret"], backup_codes=backup_codes)

@api_router.post("/auth/mfa/setup/confirm", response_model=MFAStatusResponse)
async def confirm_mfa_setup(data: ConfirmMFASetupRequest, company: dict = Depends(get_current_company)):
    encrypted_temp_secret = company.get("mfa_temp_secret_encrypted")
    if not encrypted_temp_secret:
        raise HTTPException(status_code=400, detail="Start MFA setup before confirming it.")

    secret = decrypt_sensitive_value(encrypted_temp_secret)
    if not verify_totp_code(secret, data.code):
        await log_auth_event(db, "mfa.setup_confirm", "failed", company["email"], company["id"], "authenticated-user", {"reason": "invalid_code"})
        raise HTTPException(status_code=400, detail="Invalid authenticator code")

    await db.companies.update_one(
        {"id": company["id"]},
        {"$set": {
            "mfa_enabled": True,
            "mfa_enforced": True,
            "mfa_secret_encrypted": encrypted_temp_secret,
            "mfa_backup_codes": company.get("mfa_temp_backup_codes", []),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }, "$unset": {"mfa_temp_secret_encrypted": "", "mfa_temp_backup_codes": ""}}
    )

    await log_auth_event(db, "mfa.enabled", "success", company["email"], company["id"], "authenticated-user", {})
    return MFAStatusResponse(
        enabled=True,
        enforced=True,
        backup_codes_remaining=get_remaining_backup_codes(company.get("mfa_temp_backup_codes", [])),
    )

@api_router.post("/auth/mfa/disable", response_model=MFAStatusResponse)
async def disable_mfa(data: DisableMFARequest, company: dict = Depends(get_current_company)):
    if not verify_password(data.password, company["password_hash"]):
        raise HTTPException(status_code=401, detail="Password verification failed")

    secret = company.get("mfa_secret_encrypted")
    if not secret:
        raise HTTPException(status_code=400, detail="MFA is not enabled for this account.")

    is_valid = verify_totp_code(decrypt_sensitive_value(secret), data.code)
    updated_backup_codes = None
    if not is_valid:
        updated_backup_codes = consume_backup_code(data.code, company.get("mfa_backup_codes", []))
        is_valid = updated_backup_codes is not None

    if not is_valid:
        await log_auth_event(db, "mfa.disabled", "failed", company["email"], company["id"], "authenticated-user", {"reason": "invalid_code"})
        raise HTTPException(status_code=400, detail="Invalid MFA code or backup code")

    await db.companies.update_one(
        {"id": company["id"]},
        {"$set": {
            "mfa_enabled": False,
            "mfa_enforced": False,
            "mfa_secret_encrypted": None,
            "mfa_backup_codes": updated_backup_codes or [],
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }}
    )

    await log_auth_event(db, "mfa.disabled", "success", company["email"], company["id"], "authenticated-user", {"used_backup_code": updated_backup_codes is not None})
    return MFAStatusResponse(enabled=False, enforced=False, backup_codes_remaining=0)

@api_router.post("/auth/forgot-password")
async def forgot_password(data: ForgotPasswordRequest, request: Request):
    normalized_email = data.email.lower()
    generic_message = {"message": "If an account exists for that email, a password reset link has been sent."}
    company = await db.companies.find_one({"email": normalized_email}, {"_id": 0})

    await log_auth_event(db, "password_reset.requested", "success", normalized_email, company.get("id") if company else None, get_request_ip(request), {"email_exists": bool(company)})

    if company:
        reset_token = await create_password_reset_record(db, company["id"], normalized_email)
        reset_url = f"{build_app_base_url(request)}/reset-password?token={reset_token}"
        schedule_email_task(send_password_reset_email(normalized_email, reset_url, company_id=company["id"]))

    return generic_message

@api_router.get("/auth/reset-password/validate")
async def validate_reset_password_token(token: str):
    record = await get_valid_password_reset_record(db, token)
    return {"valid": bool(record)}

@api_router.post("/auth/reset-password")
async def reset_password(data: ResetPasswordRequest, request: Request):
    password_error = validate_password_strength(data.password)
    if password_error:
        raise HTTPException(status_code=400, detail=password_error)

    record = await get_valid_password_reset_record(db, data.token)
    if not record:
        raise HTTPException(status_code=400, detail="This password reset link is invalid or has expired.")

    company = await db.companies.find_one({"id": record["company_id"]}, {"_id": 0})
    if not company:
        raise HTTPException(status_code=400, detail="This password reset link is invalid or has expired.")

    await db.companies.update_one(
        {"id": company["id"]},
        {"$set": {
            "password_hash": hash_password(data.password),
            "password_updated_at": datetime.now(timezone.utc).isoformat(),
        }}
    )
    await db.password_reset_tokens.update_one({"id": record["id"]}, {"$set": {"used_at": datetime.now(timezone.utc).isoformat()}})
    await db.auth_sessions.update_many({"company_id": company["id"], "revoked_at": None}, {"$set": {"revoked_at": datetime.now(timezone.utc).isoformat()}})
    await log_auth_event(db, "password_reset.completed", "success", company["email"], company["id"], get_request_ip(request), {})

    return {"message": "Your password has been reset successfully."}

@api_router.get("/auth/sessions", response_model=AuthSessionListResponse)
async def get_auth_sessions(company: dict = Depends(get_current_company)):
    sessions = await db.auth_sessions.find(
        {"company_id": company["id"], "revoked_at": None},
        {"_id": 0}
    ).sort("last_active_at", -1).to_list(50)

    current_session_id = company.get("current_session_id")
    current_ip = None
    for session in sessions:
        if session["id"] == current_session_id:
            current_ip = session.get("ip_address")
            break

    items = []
    for session in sessions:
        risk_flags = []
        if session.get("ip_address") != current_ip:
            risk_flags.append("new-location")
        if session.get("mfa_verified") is False:
            risk_flags.append("password-only")
        items.append(AuthSessionResponse(
            id=session["id"],
            device_name=session.get("device_name", "Unknown device"),
            browser=session.get("browser", "Unknown browser"),
            os=session.get("os", "Unknown OS"),
            ip_address=session.get("ip_address", "unknown"),
            mfa_verified=session.get("mfa_verified", False),
            created_at=session.get("created_at"),
            last_active_at=session.get("last_active_at"),
            is_current=session["id"] == current_session_id,
            risk_flags=risk_flags,
        ))

    return AuthSessionListResponse(current_session_id=current_session_id, items=items)

@api_router.post("/auth/sessions/{session_id}/revoke")
async def revoke_other_session(session_id: str, company: dict = Depends(get_current_company)):
    session = await db.auth_sessions.find_one({"id": session_id, "company_id": company["id"], "revoked_at": None}, {"_id": 0})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    await revoke_auth_session(db, session_id)
    await log_auth_event(db, "session.revoked", "success", company["email"], company["id"], "authenticated-user", {"session_id": session_id})
    return {"message": "Session revoked successfully."}

@api_router.post("/auth/sessions/revoke-all")
async def revoke_all_other_sessions(company: dict = Depends(get_current_company)):
    current_session_id = company.get("current_session_id")
    await db.auth_sessions.update_many(
        {"company_id": company["id"], "revoked_at": None, "id": {"$ne": current_session_id}},
        {"$set": {"revoked_at": datetime.now(timezone.utc).isoformat()}}
    )
    await log_auth_event(db, "session.revoke_all", "success", company["email"], company["id"], "authenticated-user", {"current_session_id": current_session_id})
    return {"message": "All other sessions have been revoked."}

@api_router.get("/auth/me", response_model=CompanyResponse)
async def get_current_company_info(company: dict = Depends(get_current_company)):
    return build_company_response(company)


@api_router.get("/phishing/templates", response_model=List[PhishingTemplateResponse])
async def get_phishing_templates(company: dict = Depends(get_current_company)):
    access = await check_subscription_access(company["id"], "phishing_simulation", db)
    if not access["allowed"]:
        raise HTTPException(status_code=403, detail=access["message"])
    return [PhishingTemplateResponse(**template) for template in list_phishing_templates()]


@api_router.get("/phishing/campaigns", response_model=List[PhishingCampaignResponse])
async def list_phishing_campaigns(company: dict = Depends(get_current_company)):
    access = await check_subscription_access(company["id"], "phishing_simulation", db)
    if not access["allowed"]:
        raise HTTPException(status_code=403, detail=access["message"])
    campaigns = await db.phishing_campaigns.find({"company_id": company["id"]}, {"_id": 0}).sort("created_at", -1).to_list(200)
    responses = []
    for campaign in campaigns:
      recipients = await db.phishing_campaign_recipients.find({"campaign_id": campaign["id"]}, {"_id": 0}).sort("employee_name", 1).to_list(5000)
      responses.append(build_phishing_campaign_response(campaign, recipients))
    return responses


@api_router.post("/phishing/campaigns", response_model=PhishingCampaignResponse)
async def create_phishing_campaign(data: PhishingCampaignCreate, request: Request, company: dict = Depends(get_current_company)):
    access = await check_subscription_access(company["id"], "phishing_simulation", db)
    if not access["allowed"]:
        raise HTTPException(status_code=403, detail=access["message"])
    if not data.target_employee_ids:
        raise HTTPException(status_code=400, detail="Select at least one employee for this campaign.")

    try:
        template = get_phishing_template(data.template_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid phishing template selected.")

    employees = await db.employees.find(
        {"company_id": company["id"], "id": {"$in": data.target_employee_ids}},
        {"_id": 0}
    ).to_list(5000)
    if len(employees) != len(set(data.target_employee_ids)):
        raise HTTPException(status_code=400, detail="Some selected employees could not be found.")

    campaign_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    campaign = {
        "id": campaign_id,
        "company_id": company["id"],
        "name": data.name,
        "template_id": data.template_id,
        "status": "draft",
        "created_at": now,
        "updated_at": now,
        "sent_at": None,
    }

    recipients = []
    for employee in employees:
        recipients.append({
            "id": str(uuid.uuid4()),
            "campaign_id": campaign_id,
            "company_id": company["id"],
            "employee_id": employee["id"],
            "employee_name": employee["name"],
            "employee_email": employee["email"],
            "department": employee.get("department", "Unknown"),
            "tracking_token": base64.urlsafe_b64encode(uuid.uuid4().bytes).decode().rstrip("="),
            "delivery_status": "pending",
            "delivery_error": None,
            "provider_message_id": None,
            "opened_at": None,
            "clicked_at": None,
            "reported_at": None,
            "sent_at": None,
            "created_at": now,
            "updated_at": now,
        })

    await db.phishing_campaigns.insert_one(campaign)
    if recipients:
        await db.phishing_campaign_recipients.insert_many(recipients)

    if data.send_immediately:
        return await send_phishing_campaign_messages(campaign, company, request)

    await log_auth_event(db, "phishing_campaign.created", "success", company["email"], company["id"], get_request_ip(request), {"campaign_id": campaign_id, "template": template["name"]})
    return build_phishing_campaign_response(campaign, recipients)


@api_router.post("/phishing/campaigns/{campaign_id}/send", response_model=PhishingCampaignResponse)
async def send_phishing_campaign(campaign_id: str, request: Request, company: dict = Depends(get_current_company)):
    access = await check_subscription_access(company["id"], "phishing_simulation", db)
    if not access["allowed"]:
        raise HTTPException(status_code=403, detail=access["message"])
    campaign = await get_phishing_campaign_or_404(campaign_id, company["id"])
    response = await send_phishing_campaign_messages(campaign, company, request)
    await log_auth_event(db, "phishing_campaign.sent", "success", company["email"], company["id"], get_request_ip(request), {"campaign_id": campaign_id})
    return response


@api_router.get("/phishing/campaigns/{campaign_id}", response_model=PhishingCampaignResponse)
async def get_phishing_campaign_detail(campaign_id: str, company: dict = Depends(get_current_company)):
    access = await check_subscription_access(company["id"], "phishing_simulation", db)
    if not access["allowed"]:
        raise HTTPException(status_code=403, detail=access["message"])
    campaign = await get_phishing_campaign_or_404(campaign_id, company["id"])
    recipients = await db.phishing_campaign_recipients.find(
        {"campaign_id": campaign_id, "company_id": company["id"]},
        {"_id": 0}
    ).sort("employee_name", 1).to_list(5000)
    return build_phishing_campaign_response(campaign, recipients)


@api_router.get("/phishing/simulations/{tracking_token}", response_model=PhishingSimulationLandingResponse)
async def get_phishing_simulation(tracking_token: str):
    recipient = await db.phishing_campaign_recipients.find_one({"tracking_token": tracking_token}, {"_id": 0})
    if not recipient:
        raise HTTPException(status_code=404, detail="Simulation link not found")

    campaign = await db.phishing_campaigns.find_one({"id": recipient["campaign_id"]}, {"_id": 0})
    company = await db.companies.find_one({"id": recipient["company_id"]}, {"_id": 0})
    if not campaign or not company:
        raise HTTPException(status_code=404, detail="Simulation data unavailable")

    if not recipient.get("clicked_at"):
        clicked_at = datetime.now(timezone.utc).isoformat()
        await db.phishing_campaign_recipients.update_one({"id": recipient["id"]}, {"$set": {"clicked_at": clicked_at, "updated_at": clicked_at}})
        recipient["clicked_at"] = clicked_at

    training = build_training_content(campaign["template_id"], recipient["employee_name"], company["company_name"])
    return PhishingSimulationLandingResponse(
        campaign_name=campaign["name"],
        template_name=str(get_phishing_template(campaign["template_id"])["name"]),
        employee_name=recipient["employee_name"],
        company_name=company["company_name"],
        difficulty=training["difficulty"],
        category=training["category"],
        scenario=training["scenario"],
        red_flags=training["red_flags"],
        learning_points=training["learning_points"],
        already_reported=bool(recipient.get("reported_at")),
    )


@api_router.post("/phishing/simulations/{tracking_token}/report")
async def report_phishing_simulation(tracking_token: str):
    recipient = await db.phishing_campaign_recipients.find_one({"tracking_token": tracking_token}, {"_id": 0})
    if not recipient:
        raise HTTPException(status_code=404, detail="Simulation link not found")

    if recipient.get("reported_at"):
        return {"message": "You already reported this simulation.", "reported": True}

    reported_at = datetime.now(timezone.utc).isoformat()
    update_fields = {"reported_at": reported_at, "updated_at": reported_at}
    if not recipient.get("clicked_at"):
        update_fields["clicked_at"] = reported_at
    await db.phishing_campaign_recipients.update_one({"id": recipient["id"]}, {"$set": update_fields})
    return {"message": "Great catch — this report has been logged.", "reported": True}


@api_router.get("/phishing/track/open/{tracking_token}")
async def track_phishing_open(tracking_token: str):
    recipient = await db.phishing_campaign_recipients.find_one({"tracking_token": tracking_token}, {"_id": 0})
    if recipient and not recipient.get("opened_at"):
        opened_at = datetime.now(timezone.utc).isoformat()
        await db.phishing_campaign_recipients.update_one({"id": recipient["id"]}, {"$set": {"opened_at": opened_at, "updated_at": opened_at}})

    transparent_gif = base64.b64decode("R0lGODlhAQABAIABAP///wAAACwAAAAAAQABAAACAkQBADs=")
    return Response(content=transparent_gif, media_type="image/gif")

# ===================== EMPLOYEE ROUTES =====================

@api_router.post("/employees", response_model=EmployeeResponse)
async def create_employee(data: EmployeeCreate, request: Request, company: dict = Depends(get_current_company)):
    plan_context = await get_company_plan_context(company["id"], db)
    max_employees = plan_context["plan"].get("max_employees", -1)
    current_employee_count = await db.employees.count_documents({"company_id": company["id"]})

    if max_employees != -1 and current_employee_count >= max_employees:
        raise HTTPException(
            status_code=403,
            detail=f"Your current plan allows up to {max_employees} employees. Upgrade to add more."
        )

    employee_id = str(uuid.uuid4())
    survey_link = f"/survey/{employee_id}"
    
    employee = {
        "id": employee_id,
        "company_id": company["id"],
        "name": data.name,
        "email": data.email,
        "department": data.department,
        "survey_completed": False,
        "survey_link": survey_link,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.employees.insert_one(employee)

    schedule_email_task(
        send_survey_invite_email(
            employee_name=data.name,
            company_name=company["company_name"],
            recipient_email=data.email,
            survey_url=f"{build_app_base_url(request)}{survey_link}",
            company_id=company["id"],
        )
    )
    
    return EmployeeResponse(**employee)

@api_router.get("/employees", response_model=List[EmployeeResponse])
async def get_employees(company: dict = Depends(get_current_company)):
    employees = await db.employees.find({"company_id": company["id"]}, {"_id": 0}).to_list(1000)
    return [EmployeeResponse(**e) for e in employees]

@api_router.delete("/employees/{employee_id}")
async def delete_employee(employee_id: str, company: dict = Depends(get_current_company)):
    result = await db.employees.delete_one({"id": employee_id, "company_id": company["id"]})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Employee not found")
    await db.survey_responses.delete_many({"employee_id": employee_id})
    return {"message": "Employee deleted"}

# ===================== BULK CSV IMPORT =====================

class BulkEmployeeData(BaseModel):
    employees: List[Dict[str, str]]  # List of {name, email, department}

@api_router.post("/employees/bulk-import", response_model=BulkImportResult)
async def bulk_import_employees(data: BulkEmployeeData, request: Request, company: dict = Depends(get_current_company)):
    """
    Bulk import employees from CSV data.
    Expected format: List of objects with name, email, department fields.
    """
    results = {
        "total_processed": len(data.employees),
        "successful": 0,
        "failed": 0,
        "errors": [],
        "employees_created": []
    }

    plan_context = await get_company_plan_context(company["id"], db)
    max_employees = plan_context["plan"].get("max_employees", -1)
    current_employee_count = await db.employees.count_documents({"company_id": company["id"]})
    created_this_import = 0

    if max_employees != -1 and current_employee_count >= max_employees:
        raise HTTPException(
            status_code=403,
            detail=f"Your current plan allows up to {max_employees} employees. Upgrade to import more."
        )
    
    # Get existing emails to avoid duplicates
    existing_employees = await db.employees.find(
        {"company_id": company["id"]}, 
        {"email": 1, "_id": 0}
    ).to_list(10000)
    existing_emails = {e["email"].lower() for e in existing_employees}
    
    for idx, emp_data in enumerate(data.employees):
        try:
            if max_employees != -1 and (current_employee_count + created_this_import) >= max_employees:
                results["errors"].append({
                    "row": str(idx + 1),
                    "error": f"Employee limit reached for your current plan ({max_employees} max)."
                })
                results["failed"] += 1
                continue

            # Validate required fields
            name = emp_data.get("name", "").strip()
            email = emp_data.get("email", "").strip().lower()
            department = emp_data.get("department", "").strip()
            
            if not name:
                results["errors"].append({"row": str(idx + 1), "error": "Name is required"})
                results["failed"] += 1
                continue
            
            if not email:
                results["errors"].append({"row": str(idx + 1), "error": "Email is required"})
                results["failed"] += 1
                continue
            
            # Basic email validation
            if "@" not in email or "." not in email:
                results["errors"].append({"row": str(idx + 1), "error": f"Invalid email format: {email}"})
                results["failed"] += 1
                continue
            
            if not department:
                department = "Unassigned"
            
            # Check for duplicates
            if email in existing_emails:
                results["errors"].append({"row": str(idx + 1), "error": f"Email already exists: {email}"})
                results["failed"] += 1
                continue
            
            # Create employee
            employee_id = str(uuid.uuid4())
            survey_link = f"/survey/{employee_id}"
            
            employee = {
                "id": employee_id,
                "company_id": company["id"],
                "name": name,
                "email": email,
                "department": department,
                "survey_completed": False,
                "survey_link": survey_link,
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            
            await db.employees.insert_one(employee)
            existing_emails.add(email)
            
            results["successful"] += 1
            created_this_import += 1
            results["employees_created"].append(EmployeeResponse(**employee))

            schedule_email_task(
                send_survey_invite_email(
                    employee_name=name,
                    company_name=company["company_name"],
                    recipient_email=email,
                    survey_url=f"{build_app_base_url(request)}{survey_link}",
                    company_id=company["id"],
                )
            )
            
        except Exception as e:
            results["errors"].append({"row": str(idx + 1), "error": str(e)})
            results["failed"] += 1
    
    return BulkImportResult(**results)

@api_router.get("/employees/csv-template")
async def get_csv_template():
    """
    Returns the expected CSV format for bulk import.
    """
    return {
        "format": "CSV with headers",
        "required_columns": ["name", "email", "department"],
        "optional_columns": [],
        "example_rows": [
            {"name": "John Doe", "email": "john.doe@company.com", "department": "Engineering"},
            {"name": "Jane Smith", "email": "jane.smith@company.com", "department": "Marketing"},
            {"name": "Bob Wilson", "email": "bob.wilson@company.com", "department": "Finance"}
        ],
        "departments_suggested": [
            "Engineering", "Marketing", "Sales", "Finance", 
            "Human Resources", "Operations", "Customer Support", 
            "Legal", "IT", "Other"
        ],
        "notes": [
            "Email addresses must be unique",
            "Department field will default to 'Unassigned' if empty",
            "Maximum 500 employees per import"
        ]
    }

# ===================== TREND ANALYSIS =====================

@api_router.get("/analytics/trends", response_model=TrendAnalysis)
async def get_trend_analysis(company: dict = Depends(get_current_company)):
    """
    Get historical trend analysis for weekly and monthly periods.
    """
    responses = await db.survey_responses.find(
        {"company_id": company["id"]}, 
        {"_id": 0}
    ).to_list(10000)
    
    employees = await db.employees.find(
        {"company_id": company["id"]}, 
        {"_id": 0}
    ).to_list(10000)
    
    now = datetime.now(timezone.utc)
    
    # Calculate weekly trends (last 4 weeks)
    weekly_trends = []
    for week_offset in range(4, 0, -1):
        week_start = now - timedelta(weeks=week_offset)
        week_end = now - timedelta(weeks=week_offset - 1)
        
        week_responses = [
            r for r in responses 
            if week_start <= datetime.fromisoformat(r["submitted_at"].replace("Z", "+00:00")) < week_end
        ]
        
        if week_responses:
            avg_overall = sum(r["overall_score"] for r in week_responses) / len(week_responses)
            avg_awareness = sum(r["scores"]["awareness"] for r in week_responses) / len(week_responses)
            avg_behavior = sum(r["scores"]["behavior"] for r in week_responses) / len(week_responses)
            avg_reporting = sum(r["scores"]["reporting"] for r in week_responses) / len(week_responses)
            
            # Determine risk level
            if avg_overall >= 75:
                risk_level = "Low"
            elif avg_overall >= 50:
                risk_level = "Medium"
            else:
                risk_level = "High"
        else:
            avg_overall = avg_awareness = avg_behavior = avg_reporting = 0
            risk_level = "Unknown"
        
        # Calculate participation for that week
        employees_at_time = [e for e in employees if datetime.fromisoformat(e["created_at"].replace("Z", "+00:00")) < week_end]
        participation = (len(week_responses) / len(employees_at_time) * 100) if employees_at_time else 0
        
        weekly_trends.append(TrendDataPoint(
            period=f"Week {5 - week_offset}",
            date=week_start.strftime("%Y-%m-%d"),
            overall_score=round(avg_overall, 1),
            awareness_score=round(avg_awareness, 1),
            behavior_score=round(avg_behavior, 1),
            reporting_score=round(avg_reporting, 1),
            participation_rate=round(participation, 1),
            responses_count=len(week_responses),
            risk_level=risk_level
        ))
    
    # Calculate monthly trends (last 6 months)
    monthly_trends = []
    for month_offset in range(6, 0, -1):
        month_start = now - timedelta(days=30 * month_offset)
        month_end = now - timedelta(days=30 * (month_offset - 1))
        
        month_responses = [
            r for r in responses 
            if month_start <= datetime.fromisoformat(r["submitted_at"].replace("Z", "+00:00")) < month_end
        ]
        
        if month_responses:
            avg_overall = sum(r["overall_score"] for r in month_responses) / len(month_responses)
            avg_awareness = sum(r["scores"]["awareness"] for r in month_responses) / len(month_responses)
            avg_behavior = sum(r["scores"]["behavior"] for r in month_responses) / len(month_responses)
            avg_reporting = sum(r["scores"]["reporting"] for r in month_responses) / len(month_responses)
            
            if avg_overall >= 75:
                risk_level = "Low"
            elif avg_overall >= 50:
                risk_level = "Medium"
            else:
                risk_level = "High"
        else:
            avg_overall = avg_awareness = avg_behavior = avg_reporting = 0
            risk_level = "Unknown"
        
        employees_at_time = [e for e in employees if datetime.fromisoformat(e["created_at"].replace("Z", "+00:00")) < month_end]
        participation = (len(month_responses) / len(employees_at_time) * 100) if employees_at_time else 0
        
        monthly_trends.append(TrendDataPoint(
            period=month_start.strftime("%b %Y"),
            date=month_start.strftime("%Y-%m-%d"),
            overall_score=round(avg_overall, 1),
            awareness_score=round(avg_awareness, 1),
            behavior_score=round(avg_behavior, 1),
            reporting_score=round(avg_reporting, 1),
            participation_rate=round(participation, 1),
            responses_count=len(month_responses),
            risk_level=risk_level
        ))
    
    # Calculate score changes
    current_score = weekly_trends[-1].overall_score if weekly_trends else 0
    prev_week_score = weekly_trends[-2].overall_score if len(weekly_trends) >= 2 else current_score
    prev_month_score = monthly_trends[-2].overall_score if len(monthly_trends) >= 2 else current_score
    
    score_change_weekly = round(current_score - prev_week_score, 1)
    score_change_monthly = round(current_score - prev_month_score, 1)
    
    # Determine trend direction
    if score_change_monthly > 5:
        trend_direction = "improving"
    elif score_change_monthly < -5:
        trend_direction = "declining"
    else:
        trend_direction = "stable"
    
    # Generate insights
    insights = []
    if current_score > 0:
        if trend_direction == "improving":
            insights.append(f"Your security culture score has improved by {abs(score_change_monthly)} points over the past month.")
        elif trend_direction == "declining":
            insights.append(f"Your security culture score has declined by {abs(score_change_monthly)} points. Consider additional training.")
        else:
            insights.append("Your security culture score has remained stable over the past month.")
        
        # Add category-specific insights
        if weekly_trends and weekly_trends[-1].awareness_score < 50:
            insights.append("Awareness scores are below average. Consider phishing awareness training.")
        if weekly_trends and weekly_trends[-1].behavior_score < 50:
            insights.append("Behavior scores indicate risky practices. Focus on password and device security training.")
        if weekly_trends and weekly_trends[-1].reporting_score < 50:
            insights.append("Reporting culture is weak. Encourage incident reporting and clarify procedures.")
        if weekly_trends and weekly_trends[-1].participation_rate < 70:
            insights.append("Survey participation is low. Send reminders to increase engagement.")
    else:
        insights.append("No survey data available yet. Start by inviting employees to take the assessment.")
    
    return TrendAnalysis(
        weekly_trends=weekly_trends,
        monthly_trends=monthly_trends,
        score_change_weekly=score_change_weekly,
        score_change_monthly=score_change_monthly,
        trend_direction=trend_direction,
        insights=insights
    )

# ===================== SURVEY ROUTES =====================

@api_router.get("/survey/questions")
async def get_survey_questions():
    return SURVEY_QUESTIONS

@api_router.get("/survey/employee/{employee_id}")
async def get_employee_for_survey(employee_id: str):
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    company = await db.companies.find_one({"id": employee["company_id"]}, {"_id": 0})
    
    return {
        "employee": employee,
        "company_name": company["company_name"] if company else "Unknown"
    }

@api_router.post("/survey/submit/{employee_id}", response_model=SurveyResponseModel)
async def submit_survey(employee_id: str, submission: SurveySubmission):
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    if employee["survey_completed"]:
        raise HTTPException(status_code=400, detail="Survey already completed")
    
    # Use enhanced scoring
    scores = calculate_enhanced_scores(submission.responses)
    
    response_id = str(uuid.uuid4())
    survey_response = {
        "id": response_id,
        "employee_id": employee_id,
        "company_id": employee["company_id"],
        "responses": submission.responses,
        "scores": {
            "awareness": scores["awareness_score"],
            "behavior": scores["behavior_score"],
            "reporting": scores["reporting_score"]
        },
        "overall_score": scores["overall_score"],
        "risk_level": scores["risk_level"],
        "risk_flags": scores.get("risk_flags", []),
        "risk_profile": scores.get("risk_profile", {}),
        "framework_domains": scores.get("framework_domain_scores", {}),
        "maturity_level": scores.get("maturity_level"),
        "maturity_summary": scores.get("maturity_summary"),
        "submitted_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.survey_responses.insert_one(survey_response)
    await db.employees.update_one({"id": employee_id}, {"$set": {"survey_completed": True}})

    company = await db.companies.find_one({"id": employee["company_id"]}, {"_id": 0})
    if company:
        schedule_email_task(
            send_survey_completion_email(
                company_name=company["company_name"],
                recipient_email=company["email"],
                employee_name=employee["name"],
                risk_level=scores["risk_level"],
                company_id=company["id"],
            )
        )
    
    return SurveyResponseModel(**survey_response)

@api_router.get("/survey/responses", response_model=List[SurveyResponseModel])
async def get_survey_responses(company: dict = Depends(get_current_company)):
    responses = await db.survey_responses.find({"company_id": company["id"]}, {"_id": 0}).to_list(1000)
    return [SurveyResponseModel(**r) for r in responses]

# ===================== DASHBOARD ROUTES =====================

@api_router.get("/dashboard/stats", response_model=DashboardStats)
async def get_dashboard_stats(company: dict = Depends(get_current_company)):
    employees = await db.employees.find({"company_id": company["id"]}, {"_id": 0}).to_list(1000)
    responses = await db.survey_responses.find({"company_id": company["id"]}, {"_id": 0}).to_list(1000)
    
    total_employees = len(employees)
    completed_surveys = len(responses)
    participation_rate = (completed_surveys / total_employees * 100) if total_employees > 0 else 0
    
    # Calculate average scores
    if responses:
        avg_awareness = sum(r["scores"]["awareness"] for r in responses) / len(responses)
        avg_behavior = sum(r["scores"]["behavior"] for r in responses) / len(responses)
        avg_reporting = sum(r["scores"]["reporting"] for r in responses) / len(responses)
        avg_overall = sum(r["overall_score"] for r in responses) / len(responses)
    else:
        avg_awareness = avg_behavior = avg_reporting = avg_overall = 0

    aligned_domains = aggregate_framework_domain_scores(responses)
    aligned_overall = calculate_framework_overall_score(aligned_domains) if aligned_domains else avg_overall
    phishing_program = await calculate_phishing_program_posture(company["id"])
    
    # Enhanced risk level calculation
    critical_count = sum(1 for r in responses for f in r.get("risk_flags", []) if f.get("severity") == "critical")
    high_flag_count = sum(1 for r in responses for f in r.get("risk_flags", []) if f.get("severity") == "high")
    company_penalty = min(20, critical_count * 6 + high_flag_count * 2)
    adjusted_overall = clamp_score(aligned_overall - company_penalty + phishing_program.get("score_modifier", 0.0)) if responses else 0.0
    maturity_band = get_maturity_band(adjusted_overall)
    
    risk_level = determine_company_risk_level(adjusted_overall, critical_count)
    
    # Department breakdown with enhanced risk analysis
    department_risks = {}
    for emp in employees:
        dept = emp["department"]
        if dept not in department_risks:
            department_risks[dept] = {
                "employees": 0, 
                "completed": 0, 
                "scores": [], 
                "risk": "Unknown",
                "critical_flags": 0,
                "high_risk_count": 0
            }
        department_risks[dept]["employees"] += 1
    
    for resp in responses:
        emp = next((e for e in employees if e["id"] == resp["employee_id"]), None)
        if emp:
            dept = emp["department"]
            department_risks[dept]["completed"] += 1
            department_risks[dept]["scores"].append(resp["overall_score"])
            # Count critical flags per department
            dept_critical = sum(1 for f in resp.get("risk_flags", []) if f.get("severity") == "critical")
            department_risks[dept]["critical_flags"] += dept_critical
            if resp.get("risk_level") in ["High", "Critical", "Medium-High"]:
                department_risks[dept]["high_risk_count"] += 1
    
    for dept, data in department_risks.items():
        if data["scores"]:
            avg = sum(data["scores"]) / len(data["scores"])
            data["avg_score"] = round(avg, 1)
            # Enhanced department risk calculation
            critical_ratio = data["critical_flags"] / max(data["completed"], 1)
            if critical_ratio > 0.3 or avg < 40:
                data["risk"] = "High"
            elif critical_ratio > 0.1 or avg < 55:
                data["risk"] = "Medium"
            else:
                data["risk"] = "Low"
        del data["scores"]
    
    # Enhanced risk heatmap
    risk_heatmap = calculate_risk_heatmap(responses)
    if phishing_program.get("measured"):
        risk_heatmap["phishing_simulation_click_rate"] = phishing_program["click_rate"]
        risk_heatmap["phishing_simulation_report_rate"] = phishing_program["report_rate"]
        risk_heatmap["phishing_program_resilience"] = phishing_program["resilience_score"]
    
    # Identify high-risk employees
    high_risk_employees = identify_high_risk_employees(employees, responses)
    
    # Aggregate behavioral red flags
    behavioral_red_flags = aggregate_behavioral_red_flags(responses)
    
    # Risk distribution
    risk_distribution = {"Low": 0, "Low-Medium": 0, "Medium": 0, "Medium-High": 0, "High": 0, "Critical": 0}
    for resp in responses:
        rl = resp.get("risk_level", "Unknown")
        if rl in risk_distribution:
            risk_distribution[rl] += 1
    
    # Calculate vulnerability index (company-wide)
    if responses:
        vulnerability_scores = [r.get("risk_profile", {}).get("vulnerability_index", 50) for r in responses]
        vulnerability_index = sum(vulnerability_scores) / len(vulnerability_scores)
    else:
        vulnerability_index = 0
    
    return DashboardStats(
        overall_score=adjusted_overall,
        awareness_score=round(avg_awareness, 1),
        behavior_score=round(avg_behavior, 1),
        reporting_score=round(avg_reporting, 1),
        participation_rate=round(participation_rate, 1),
        risk_level=risk_level,
        total_employees=total_employees,
        completed_surveys=completed_surveys,
        department_risks=department_risks,
        risk_heatmap=risk_heatmap,
        critical_risk_count=critical_count,
        high_risk_employees=high_risk_employees,
        risk_distribution=risk_distribution,
        behavioral_red_flags=behavioral_red_flags,
        vulnerability_index=round(vulnerability_index, 1),
        risk_trend_indicator="stable",  # Would need historical data for actual trend
        maturity_level=maturity_band["level"],
        maturity_summary=maturity_band["description"],
        framework_note=FRAMEWORK_NOTE,
        aligned_domains=aligned_domains,
        phishing_program=phishing_program,
    )

# ===================== AI REPORT GENERATION =====================

async def generate_ai_report(company: dict, stats: DashboardStats, responses: List[dict]) -> Dict[str, Any]:
    """Generate AI-powered audit report using Claude"""
    try:
        from anthropic import AsyncAnthropic

        api_key = os.environ.get('ANTHROPIC_API_KEY')
        if not api_key:
            raise HTTPException(status_code=500, detail="AI service not configured")

        client = AsyncAnthropic(api_key=api_key)
        system_message = (
            "You are a cybersecurity culture expert. Generate professional audit reports "
            "analyzing organizational cybersecurity culture based on survey data. Be specific, actionable, "
            "and professional. Format your response as a structured report."
        )

        prompt = f"""Generate a detailed cybersecurity culture audit report for {company['company_name']}.

IMPORTANT POSITIONING:
- Map findings to ISO/IEC 27001 people-awareness and human security controls and NIST Cybersecurity Framework principles as guidance only.
- Do NOT present this as a formal certification, attestation, or legal compliance opinion.
- Use an audit-ready but practical tone.

SURVEY DATA:
- Overall Culture Score: {stats.overall_score}/100
- Risk Level: {stats.risk_level}
- Maturity Level: {stats.maturity_level}
- Awareness Score: {stats.awareness_score}/100
- Behavior Score: {stats.behavior_score}/100
- Reporting Culture Score: {stats.reporting_score}/100
- Survey Participation: {stats.participation_rate}%
- Total Employees: {stats.total_employees}
- Completed Surveys: {stats.completed_surveys}

DEPARTMENT BREAKDOWN:
{stats.department_risks}

RISK HEATMAP:
- Password Reuse Risk: {stats.risk_heatmap.get('password_reuse', 0)}%
- Phishing Susceptibility: {stats.risk_heatmap.get('phishing_susceptibility', 0)}%
- Device Security: {stats.risk_heatmap.get('device_security', 0)}%
- Incident Reporting: {stats.risk_heatmap.get('incident_reporting', 0)}%
- Policy Compliance: {stats.risk_heatmap.get('policy_compliance', 0)}%

FRAMEWORK-ALIGNED DOMAIN SCORES:
{stats.aligned_domains}

PHISHING SIMULATION EVIDENCE:
{stats.phishing_program}

Please provide the report in the following JSON structure:
{{
    "framework_notice": "Brief statement that this is guidance aligned to ISO/IEC 27001 and NIST CSF, not certification",
    "executive_summary": "Brief 2-3 sentence summary of findings",
    "maturity_assessment": {{"level": "maturity level", "summary": "short explanation", "next_focus": "next maturity step"}},
    "control_domain_scores": [
        {{"domain": "domain name", "score": 0, "maturity": "level", "iso_reference": "reference", "nist_reference": "reference", "finding": "short interpretation"}}
    ],
    "key_findings": ["finding1", "finding2", "finding3"],
    "human_risk_factors": [
        {{"risk": "risk name", "severity": "High/Medium/Low", "description": "details"}}
    ],
    "phishing_program_findings": {{"summary": "what phishing evidence shows", "click_rate": 0, "report_rate": 0}},
    "awareness_gaps": ["gap1", "gap2"],
    "behavior_insights": ["insight1", "insight2"],
    "department_analysis": {{"dept_name": "analysis"}},
    "framework_alignment": [
        {{"theme": "theme", "iso_reference": "reference", "nist_reference": "reference", "status": "Aligned/Needs improvement", "commentary": "details"}}
    ],
    "recommendations": [
        {{"priority": 1, "title": "recommendation", "description": "details", "training_type": "training name", "mapped_control": "ISO/NIST mapping"}}
    ],
    "improvement_roadmap": ["phase1", "phase2", "phase3"]
}}"""

        message = await client.messages.create(
            model=os.environ.get('AI_MODEL', 'claude-sonnet-5'),
            max_tokens=4000,
            system=system_message,
            messages=[{"role": "user", "content": prompt}],
        )
        response = "".join(block.text for block in message.content if getattr(block, "type", "") == "text")
        
        # Parse JSON from response
        import json
        import re
        
        # Try to extract JSON from the response
        json_match = re.search(r'\{[\s\S]*\}', response)
        if json_match:
            report_content = json.loads(json_match.group())
        else:
            # Fallback structure
            report_content = {
                "executive_summary": response[:500] if len(response) > 500 else response,
                "key_findings": ["Analysis pending"],
                "human_risk_factors": [],
                "awareness_gaps": [],
                "behavior_insights": [],
                "department_analysis": {},
                "recommendations": [],
                "improvement_roadmap": []
            }
        
        return normalize_report_content(report_content, stats)
        
    except Exception as e:
        logger.error(f"AI Report generation failed: {str(e)}")
        # Return a fallback report
        return normalize_report_content({
            "framework_notice": FRAMEWORK_NOTE,
            "executive_summary": f"CultureShield AI analysis for {company['company_name']} shows an overall cybersecurity culture score of {stats.overall_score}/100 with {stats.risk_level} risk level.",
            "key_findings": [
                f"Overall culture score: {stats.overall_score}/100",
                f"Survey participation rate: {stats.participation_rate}%",
                f"Primary risk level: {stats.risk_level}",
                f"Maturity level: {stats.maturity_level}"
            ],
            "maturity_assessment": {
                "level": stats.maturity_level,
                "summary": stats.maturity_summary,
                "next_focus": get_maturity_band(stats.overall_score)["next_focus"],
            },
            "control_domain_scores": [
                {
                    "domain": domain["label"],
                    "score": domain["score"],
                    "maturity": domain["maturity_level"],
                    "iso_reference": domain["iso_reference"],
                    "nist_reference": domain["nist_reference"],
                    "finding": domain["focus"],
                }
                for domain in stats.aligned_domains.values()
            ],
            "human_risk_factors": [
                {"risk": "Password Practices", "severity": "Medium" if stats.risk_heatmap.get('password_reuse', 50) > 30 else "Low", "description": "Password reuse patterns detected"},
                {"risk": "Phishing Susceptibility", "severity": "Medium" if stats.risk_heatmap.get('phishing_susceptibility', 50) > 35 else "Low", "description": "Threat recognition and verification behaviors should improve"}
            ],
            "phishing_program_findings": {
                "summary": stats.phishing_program.get("summary"),
                "click_rate": stats.phishing_program.get("click_rate"),
                "report_rate": stats.phishing_program.get("report_rate"),
            },
            "awareness_gaps": [
                f"Awareness score at {stats.awareness_score}% indicates room for improvement",
                "Security policy knowledge varies across departments",
                "Role-specific recognition of suspicious requests needs reinforcement"
            ],
            "behavior_insights": [
                f"Behavior score: {stats.behavior_score}%",
                "Device security practices need reinforcement",
                "Human security behavior should be validated through regular exercises"
            ],
            "department_analysis": stats.department_risks,
            "framework_alignment": [
                {
                    "theme": domain["label"],
                    "iso_reference": domain["iso_reference"],
                    "nist_reference": domain["nist_reference"],
                    "status": "Aligned" if domain["score"] >= 65 else "Needs improvement",
                    "commentary": domain["focus"],
                }
                for domain in stats.aligned_domains.values()
            ],
            "recommendations": [
                {"priority": 1, "title": "Role-based phishing resilience program", "description": "Use recurring simulations and short refreshers to improve click resistance and reporting speed.", "training_type": "Phishing Awareness", "mapped_control": "ISO A.6.3 / NIST Detect-Respond"},
                {"priority": 2, "title": "Password and credential hygiene reinforcement", "description": "Strengthen password-manager use, authentication hygiene, and remote-access discipline.", "training_type": "Password Security", "mapped_control": "ISO A.6.7 / NIST Protect"},
                {"priority": 3, "title": "Incident reporting rehearsal", "description": "Reinforce how and when employees escalate suspicious messages, policy exceptions, and security concerns.", "training_type": "Incident Reporting", "mapped_control": "ISO A.6.8 / NIST Respond"}
            ],
            "improvement_roadmap": [
                "Phase 1: Establish role-based awareness baseline and reporting expectations",
                "Phase 2: Validate behavior through phishing exercises and targeted coaching",
                "Phase 3: Measure maturity trends and integrate human-risk evidence into governance review"
            ]
        }, stats)


def normalize_report_content(report_content: Dict[str, Any], stats: DashboardStats) -> Dict[str, Any]:
    normalized = dict(report_content or {})
    normalized.setdefault("framework_notice", FRAMEWORK_NOTE)
    normalized.setdefault("executive_summary", f"CultureShield AI shows an overall human-security score of {stats.overall_score}/100.")
    normalized.setdefault("maturity_assessment", {
        "level": stats.maturity_level,
        "summary": stats.maturity_summary,
        "next_focus": get_maturity_band(stats.overall_score)["next_focus"],
    })
    normalized.setdefault("control_domain_scores", [
        {
            "domain": domain["label"],
            "score": domain["score"],
            "maturity": domain["maturity_level"],
            "iso_reference": domain["iso_reference"],
            "nist_reference": domain["nist_reference"],
            "finding": domain["focus"],
        }
        for domain in stats.aligned_domains.values()
    ])
    normalized.setdefault("key_findings", [])
    normalized.setdefault("human_risk_factors", [])
    normalized.setdefault("phishing_program_findings", {
        "summary": stats.phishing_program.get("summary"),
        "click_rate": stats.phishing_program.get("click_rate"),
        "report_rate": stats.phishing_program.get("report_rate"),
    })
    normalized.setdefault("awareness_gaps", [])
    normalized.setdefault("behavior_insights", [])
    normalized.setdefault("department_analysis", {})
    normalized.setdefault("framework_alignment", [
        {
            "theme": domain["label"],
            "iso_reference": domain["iso_reference"],
            "nist_reference": domain["nist_reference"],
            "status": "Aligned" if domain["score"] >= 65 else "Needs improvement",
            "commentary": domain["focus"],
        }
        for domain in stats.aligned_domains.values()
    ])
    normalized.setdefault("recommendations", [])
    normalized.setdefault("improvement_roadmap", [])
    return normalized

@api_router.post("/reports/generate", response_model=AuditReportResponse)
async def generate_audit_report(request: Request, company: dict = Depends(get_current_company)):
    report_access = await check_subscription_access(company["id"], "ai_report", db)
    if not report_access["allowed"]:
        raise HTTPException(status_code=403, detail=report_access["message"])

    audit_access = await check_subscription_access(company["id"], "audit", db)
    if not audit_access["allowed"]:
        raise HTTPException(status_code=403, detail=audit_access["message"])

    responses = await db.survey_responses.find({"company_id": company["id"]}, {"_id": 0}).to_list(1000)
    
    if not responses:
        raise HTTPException(status_code=400, detail="No survey responses to analyze")
    
    # Get dashboard stats
    stats_response = await get_dashboard_stats(company)
    
    # Generate AI report
    report_content = await generate_ai_report(company, stats_response, responses)
    
    report_id = str(uuid.uuid4())
    report = {
        "id": report_id,
        "company_id": company["id"],
        "report_content": report_content,
        "stats": {
            "overall_score": stats_response.overall_score,
            "awareness_score": stats_response.awareness_score,
            "behavior_score": stats_response.behavior_score,
            "reporting_score": stats_response.reporting_score,
            "risk_level": stats_response.risk_level,
            "maturity_level": stats_response.maturity_level,
            "maturity_summary": stats_response.maturity_summary,
            "framework_note": stats_response.framework_note,
            "aligned_domains": stats_response.aligned_domains,
            "phishing_program": stats_response.phishing_program,
            "department_risks": stats_response.department_risks,
            "risk_heatmap": stats_response.risk_heatmap
        },
        "generated_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.audit_reports.insert_one(report)

    if audit_access.get("billing_source") == "one_time_purchase":
        await consume_audit_credit(company["id"], db)

    schedule_email_task(
        send_report_ready_email(
            company_name=company["company_name"],
            recipient_email=company["email"],
            overall_score=stats_response.overall_score,
            report_url=f"{build_app_base_url(request)}/reports/{report_id}",
            company_id=company["id"],
        )
    )
    
    return AuditReportResponse(
        id=report_id,
        company_id=company["id"],
        report_content=report_content,
        generated_at=report["generated_at"]
    )

@api_router.get("/reports", response_model=List[AuditReportResponse])
async def get_reports(company: dict = Depends(get_current_company)):
    reports = await db.audit_reports.find({"company_id": company["id"]}, {"_id": 0}).to_list(100)
    return [AuditReportResponse(**r) for r in reports]

@api_router.get("/reports/{report_id}", response_model=AuditReportResponse)
async def get_report(report_id: str, company: dict = Depends(get_current_company)):
    report = await db.audit_reports.find_one({"id": report_id, "company_id": company["id"]}, {"_id": 0})
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return AuditReportResponse(**report)

def clean_text_for_pdf(text: str) -> str:
    """Clean text for PDF generation by replacing Unicode characters"""
    if not text:
        return ""
    # Replace common Unicode characters with ASCII equivalents
    replacements = {
        '\u201c': '"',  # Left double quotation mark
        '\u201d': '"',  # Right double quotation mark
        '\u2018': "'",  # Left single quotation mark
        '\u2019': "'",  # Right single quotation mark
        '–': '-',  # En dash
        '—': '-',  # Em dash
        '•': '-',  # Bullet point
        '…': '...',  # Ellipsis
    }
    
    for unicode_char, ascii_char in replacements.items():
        text = text.replace(unicode_char, ascii_char)
    
    # Remove any remaining non-ASCII characters
    text = ''.join(char if ord(char) < 128 else '?' for char in text)
    
    # Limit line length to prevent wrapping issues
    if len(text) > 80:
        text = text[:77] + "..."
    
    return text

def sanitize_text_for_pdf(text):
    """Remove or replace unicode characters that Arial font doesn't support"""
    if not text:
        return ""
    # Replace common unicode characters
    replacements = {
        '\u201c': '"', '\u201d': '"', '\u2018': "'", '\u2019': "'",
        '–': '-', '—': '-', '…': '...', '•': '*',
        '\xa0': ' ', '\n': ' ', '\r': ' ', '\t': ' '
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    # Remove any remaining non-ASCII characters
    text = ''.join(c if ord(c) < 128 else '?' for c in text)
    return text.strip()


def build_board_summary_actions(stats: DashboardStats) -> List[Dict[str, str]]:
    domain_actions = sorted(
        list(stats.aligned_domains.values()),
        key=lambda domain: domain.get("score", 0)
    )[:2]

    actions = []
    for index, domain in enumerate(domain_actions, start=1):
        actions.append({
            "priority": str(index),
            "title": f"Strengthen {domain.get('label', 'priority control area')}",
            "detail": (
                f"Leadership should sponsor improvements in {domain.get('label', 'this domain').lower()} "
                f"because the current score is {domain.get('score', 0)}/100. "
                f"This maps to {domain.get('iso_reference', 'ISO guidance')} and {domain.get('nist_reference', 'NIST guidance')}."
            ),
        })

    if stats.phishing_program.get("measured"):
        actions.append({
            "priority": str(len(actions) + 1),
            "title": "Use phishing evidence in board oversight",
            "detail": (
                f"Observed phishing resilience shows a {stats.phishing_program.get('click_rate')}% click rate and "
                f"a {stats.phishing_program.get('report_rate')}% report rate. Track this alongside maturity as a leading indicator."
            ),
        })
    else:
        actions.append({
            "priority": str(len(actions) + 1),
            "title": "Add behavioral evidence beyond surveys",
            "detail": "Run recurring phishing simulations so the board can compare stated awareness with observed user behavior.",
        })

    return actions[:3]


@api_router.get("/board-summary/pdf")
async def get_board_summary_pdf(company: dict = Depends(get_current_company)):
    stats = await get_dashboard_stats(company)
    reports_count = await db.audit_reports.count_documents({"company_id": company["id"]})
    board_actions = build_board_summary_actions(stats)
    top_departments = sorted(
        [
            {"name": name, **details}
            for name, details in stats.department_risks.items()
        ],
        key=lambda department: (department.get("critical_flags", 0), department.get("high_risk_count", 0)),
        reverse=True,
    )[:3]

    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)

    pdf.set_font("Arial", "B", 18)
    pdf.cell(0, 12, "CultureShield AI", ln=True, align="C")
    pdf.set_font("Arial", "B", 15)
    pdf.cell(0, 10, "Standards Alignment Summary", ln=True, align="C")
    pdf.ln(8)

    pdf.set_font("Arial", "", 11)
    pdf.cell(0, 7, f"Company: {sanitize_text_for_pdf(company.get('company_name', 'Unknown'))}", ln=True)
    pdf.cell(0, 7, f"Prepared: {datetime.now(timezone.utc).date().isoformat()}", ln=True)
    pdf.ln(6)

    pdf.set_font("Arial", "B", 13)
    pdf.cell(0, 9, "Executive Snapshot", ln=True)
    pdf.set_font("Arial", "", 11)
    pdf.cell(0, 7, f"Overall Score: {stats.overall_score}/100", ln=True)
    pdf.cell(0, 7, f"Risk Level: {sanitize_text_for_pdf(stats.risk_level)}", ln=True)
    pdf.cell(0, 7, f"Maturity Level: {sanitize_text_for_pdf(stats.maturity_level)}", ln=True)
    pdf.cell(0, 7, f"Participation: {stats.participation_rate}%", ln=True)
    pdf.cell(0, 7, f"Audit Reports Available: {reports_count}", ln=True)
    pdf.ln(5)

    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 8, "Standards Notice", ln=True)
    pdf.set_font("Arial", "", 10)
    pdf.multi_cell(0, 5, sanitize_text_for_pdf(stats.framework_note))
    pdf.ln(4)

    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 8, "Control Domain Scores", ln=True)
    pdf.set_font("Arial", "", 10)
    for domain in stats.aligned_domains.values():
        label = sanitize_text_for_pdf(domain.get("label", "Domain"))
        iso_ref = sanitize_text_for_pdf(domain.get("iso_reference", ""))
        nist_ref = sanitize_text_for_pdf(domain.get("nist_reference", ""))
        maturity = sanitize_text_for_pdf(domain.get("maturity_level", ""))
        score = domain.get("score", 0)
        pdf.set_x(pdf.l_margin)
        pdf.multi_cell(180, 5, f"- {label}: {score}/100 ({maturity})")
        pdf.set_x(pdf.l_margin)
        pdf.multi_cell(180, 5, f"  {iso_ref} | {nist_ref}")
    pdf.ln(4)

    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 8, "Board Action Priorities", ln=True)
    pdf.set_font("Arial", "", 10)
    for action in board_actions:
        pdf.set_font("Arial", "B", 10)
        pdf.cell(0, 6, f"{action['priority']}. {sanitize_text_for_pdf(action['title'])}", ln=True)
        pdf.set_font("Arial", "", 10)
        pdf.set_x(pdf.l_margin)
        pdf.multi_cell(180, 5, sanitize_text_for_pdf(action["detail"]))
        pdf.ln(1)

    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 8, "Top Human-Risk Signals", ln=True)
    pdf.set_font("Arial", "", 10)
    for risk_flag in stats.behavioral_red_flags[:4]:
        pdf.set_x(pdf.l_margin)
        pdf.multi_cell(180, 5, f"- {sanitize_text_for_pdf(risk_flag.get('title', 'Risk flag'))}: {sanitize_text_for_pdf(risk_flag.get('description', ''))}")
    pdf.ln(4)

    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 8, "Department Spotlight", ln=True)
    pdf.set_font("Arial", "", 10)
    if top_departments:
        for department in top_departments:
            pdf.set_x(pdf.l_margin)
            pdf.multi_cell(
                180,
                5,
                f"- {sanitize_text_for_pdf(department['name'])}: {department.get('risk', 'Unknown')} risk, {department.get('employees', 0)} employees, {department.get('critical_flags', 0)} critical flags, avg score {department.get('avg_score', 0)}"
            )
    else:
        pdf.set_x(pdf.l_margin)
        pdf.multi_cell(180, 5, "No department-level spotlight available yet.")
    pdf.ln(4)

    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 8, "Phishing Evidence", ln=True)
    pdf.set_font("Arial", "", 10)
    pdf.set_x(pdf.l_margin)
    pdf.multi_cell(180, 5, sanitize_text_for_pdf(stats.phishing_program.get("summary", "Phishing evidence not measured yet.")))
    if stats.phishing_program.get("measured"):
        pdf.cell(0, 6, f"Open Rate: {stats.phishing_program.get('open_rate')}%", ln=True)
        pdf.cell(0, 6, f"Click Rate: {stats.phishing_program.get('click_rate')}%", ln=True)
        pdf.cell(0, 6, f"Report Rate: {stats.phishing_program.get('report_rate')}%", ln=True)
    pdf.ln(6)

    pdf.set_font("Arial", "I", 9)
    pdf.set_x(pdf.l_margin)
    pdf.multi_cell(180, 5, "Generated by CultureShield AI for executive leadership review. This summary is intended for management insight, not formal certification.")

    pdf_bytes = pdf.output()
    return Response(
        content=bytes(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=CultureShield_Board_Summary_{company['id'][:8]}.pdf"},
    )

@api_router.get("/reports/{report_id}/pdf")
async def get_report_pdf(report_id: str, company: dict = Depends(get_current_company)):
    report = await db.audit_reports.find_one({"id": report_id, "company_id": company["id"]}, {"_id": 0})
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    
    # Generate simple PDF
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    
    # Title
    pdf.set_font("Arial", "B", 20)
    pdf.cell(0, 15, "CultureShield AI", ln=True, align="C")
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, "Cybersecurity Culture Audit Report", ln=True, align="C")
    pdf.ln(10)
    
    # Company info
    pdf.set_font("Arial", "", 12)
    company_name = sanitize_text_for_pdf(company.get('company_name', 'Unknown'))
    pdf.cell(0, 8, f"Company: {company_name}", ln=True)
    pdf.cell(0, 8, f"Report Date: {report['generated_at'][:10]}", ln=True)
    pdf.ln(10)
    
    # Scores section
    stats = report.get("stats", {})
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, "Cybersecurity Culture Score", ln=True)
    
    pdf.set_font("Arial", "B", 24)
    score = stats.get("overall_score", 0)
    risk_level = sanitize_text_for_pdf(stats.get('risk_level', 'Unknown'))
    pdf.cell(0, 15, f"{score}/100 - {risk_level} Risk", ln=True)
    pdf.ln(5)
    
    # Sub-scores
    pdf.set_font("Arial", "", 11)
    pdf.cell(0, 8, f"Awareness Score: {stats.get('awareness_score', 0)}/100", ln=True)
    pdf.cell(0, 8, f"Behavior Score: {stats.get('behavior_score', 0)}/100", ln=True)
    pdf.cell(0, 8, f"Reporting Culture Score: {stats.get('reporting_score', 0)}/100", ln=True)
    pdf.cell(0, 8, f"Maturity Level: {sanitize_text_for_pdf(stats.get('maturity_level', 'Initial'))}", ln=True)
    pdf.ln(10)
    
    content = report.get("report_content", {})

    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 8, "Standards Alignment Notice", ln=True)
    pdf.set_font("Arial", "", 10)
    notice = sanitize_text_for_pdf(content.get("framework_notice") or stats.get("framework_note", FRAMEWORK_NOTE))
    pdf.multi_cell(0, 5, notice[:280])
    pdf.ln(4)

    maturity = content.get("maturity_assessment", {})
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 8, "Maturity Assessment", ln=True)
    pdf.set_font("Arial", "", 10)
    maturity_line = sanitize_text_for_pdf(f"{maturity.get('level', stats.get('maturity_level', 'Initial'))}: {maturity.get('summary', stats.get('maturity_summary', ''))}")
    pdf.multi_cell(0, 5, maturity_line[:220])
    pdf.ln(4)

    domain_scores = content.get("control_domain_scores", [])[:4]
    if domain_scores:
        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 8, "Control Domain Scores", ln=True)
        pdf.set_font("Arial", "", 10)
        for domain in domain_scores:
            domain_label = sanitize_text_for_pdf(str(domain.get("domain", "Domain")))
            domain_score = domain.get("score", 0)
            domain_maturity = sanitize_text_for_pdf(str(domain.get("maturity", "")))
            pdf.cell(0, 6, f"- {domain_label}: {domain_score}/100 ({domain_maturity})", ln=True)
        pdf.ln(4)
    
    # Executive Summary
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, "Executive Summary", ln=True)
    pdf.set_font("Arial", "", 11)
    summary = sanitize_text_for_pdf(content.get("executive_summary", "No summary available"))
    # Truncate for cell
    if len(summary) > 200:
        summary = summary[:200] + "..."
    pdf.multi_cell(0, 6, summary)
    pdf.ln(8)

    phishing_findings = content.get("phishing_program_findings", {})
    if phishing_findings and phishing_findings.get("summary"):
        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 8, "Phishing Evidence", ln=True)
        pdf.set_font("Arial", "", 10)
        phishing_summary = sanitize_text_for_pdf(str(phishing_findings.get("summary", "")))
        pdf.multi_cell(0, 5, phishing_summary[:220])
        click_rate = phishing_findings.get("click_rate")
        report_rate = phishing_findings.get("report_rate")
        if click_rate is not None or report_rate is not None:
            pdf.cell(0, 6, f"Click Rate: {click_rate if click_rate is not None else 'N/A'}% | Report Rate: {report_rate if report_rate is not None else 'N/A'}%", ln=True)
        pdf.ln(4)
    
    # Key Findings
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, "Key Findings", ln=True)
    pdf.set_font("Arial", "", 11)
    findings = content.get("key_findings", [])
    for i, finding in enumerate(findings[:5]):
        clean_finding = sanitize_text_for_pdf(str(finding))
        if len(clean_finding) > 100:
            clean_finding = clean_finding[:100] + "..."
        pdf.cell(0, 6, f"  * {clean_finding}", ln=True)
    pdf.ln(8)
    
    # Recommendations
    pdf.add_page()
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, "Recommendations", ln=True)
    pdf.set_font("Arial", "", 11)
    recommendations = content.get("recommendations", [])
    for i, rec in enumerate(recommendations[:5]):
        if isinstance(rec, dict):
            title = sanitize_text_for_pdf(rec.get('title', ''))
            if len(title) > 60:
                title = title[:60] + "..."
            pdf.set_font("Arial", "B", 11)
            pdf.cell(0, 8, f"{i+1}. {title}", ln=True)
            pdf.set_font("Arial", "", 11)
            desc = sanitize_text_for_pdf(rec.get('description', ''))
            if len(desc) > 100:
                desc = desc[:100] + "..."
            pdf.cell(0, 6, f"   {desc}", ln=True)
            if rec.get("training_type"):
                training = sanitize_text_for_pdf(rec.get("training_type", ""))
                pdf.cell(0, 6, f"   Training: {training}", ln=True)
            pdf.ln(2)
    
    # Footer
    pdf.ln(20)
    pdf.set_font("Arial", "I", 10)
    pdf.cell(0, 8, "Generated by CultureShield AI - Cybersecurity Culture Assessment Platform", ln=True, align="C")
    
    # Generate PDF bytes
    pdf_bytes = pdf.output()
    
    return Response(
        content=bytes(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=CultureShield_Audit_Report_{report_id[:8]}.pdf"}
    )

# ===================== HEALTH CHECK =====================

@api_router.get("/")
async def root():
    return {"message": "CultureShield AI API", "status": "healthy"}

@api_router.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now(timezone.utc).isoformat()}

# Include the router in the main app
app.include_router(api_router)

from billing_routes import billing_router

app.include_router(billing_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
