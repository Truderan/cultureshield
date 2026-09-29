import asyncio
import logging
import os
import re
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone

import resend
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

logger = logging.getLogger(__name__)

RESEND_API_KEY = os.environ.get("RESEND_API_KEY")
SENDER_EMAIL = os.environ.get("SENDER_EMAIL")

if RESEND_API_KEY:
    resend.api_key = RESEND_API_KEY

EMAIL_PATTERN = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")


def sanitize_email_error(message: str) -> str:
    if "You can only send testing emails to your own email address" in message:
        return "Resend is currently in testing mode. To deliver emails to other recipients, verify a sending domain and use a sender address from that domain."

    return EMAIL_PATTERN.sub("[redacted-email]", message)


def render_email_template(
    title: str,
    intro: str,
    bullets: Optional[List[str]] = None,
    cta_label: Optional[str] = None,
    cta_url: Optional[str] = None,
    closing_note: str = "Sent by CultureShield AI",
) -> str:
    bullet_html = ""
    if bullets:
        items = "".join(
            f"<li style='margin:0 0 10px;color:#475569;line-height:1.6;'>{bullet}</li>" for bullet in bullets
        )
        bullet_html = f"<ul style='padding-left:20px;margin:24px 0;'>{items}</ul>"

    cta_html = ""
    if cta_label and cta_url:
        cta_html = (
            "<div style='margin:28px 0;'>"
            f"<a href='{cta_url}' style='display:inline-block;background:#1F3A5F;color:#ffffff;text-decoration:none;padding:14px 22px;border-radius:999px;font-weight:600;'>{cta_label}</a>"
            "</div>"
        )

    return f"""
    <table role='presentation' width='100%' cellspacing='0' cellpadding='0' style='background:#f8fafc;padding:32px 16px;font-family:Arial,sans-serif;'>
      <tr>
        <td align='center'>
          <table role='presentation' width='100%' cellspacing='0' cellpadding='0' style='max-width:640px;background:#ffffff;border:1px solid #e2e8f0;border-radius:24px;padding:40px;'>
            <tr>
              <td>
                <div style='font-size:12px;letter-spacing:0.18em;text-transform:uppercase;color:#00A8E8;font-weight:700;margin-bottom:16px;'>CultureShield AI</div>
                <h1 style='margin:0 0 16px;font-size:32px;line-height:1.2;color:#1F3A5F;'>{title}</h1>
                <p style='margin:0;color:#475569;font-size:16px;line-height:1.7;'>{intro}</p>
                {bullet_html}
                {cta_html}
                <p style='margin:28px 0 0;color:#94a3b8;font-size:13px;line-height:1.6;'>{closing_note}</p>
              </td>
            </tr>
          </table>
        </td>
      </tr>
    </table>
    """


async def send_email(recipient_email: str, subject: str, html_content: str) -> Dict[str, Any]:
    return await send_email_with_metadata(
        recipient_email=recipient_email,
        subject=subject,
        html_content=html_content,
        email_type="general",
    )


async def log_email_activity(
    recipient_email: str,
    subject: str,
    email_type: str,
    status: str,
    provider_message: Optional[str] = None,
    provider_id: Optional[str] = None,
    company_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> None:
    try:
        from server import db

        event = {
            "id": str(uuid.uuid4()),
            "recipient_email": recipient_email,
            "subject": subject,
            "email_type": email_type,
            "status": status,
            "provider": "resend",
            "provider_message": provider_message,
            "provider_id": provider_id,
            "company_id": company_id,
            "metadata": metadata or {},
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        await db.email_events.insert_one(event)
    except Exception as exc:
        logger.error("Failed to log email activity: %s", sanitize_email_error(str(exc)))


async def send_email_with_metadata(
    recipient_email: str,
    subject: str,
    html_content: str,
    email_type: str,
    company_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    if not RESEND_API_KEY or not SENDER_EMAIL:
        logger.warning("Email send skipped - Resend not configured")
        result = {"status": "skipped", "reason": "missing_config"}
        await log_email_activity(recipient_email, subject, email_type, "skipped", provider_message="missing_config", company_id=company_id, metadata=metadata)
        return result

    params = {
        "from": SENDER_EMAIL,
        "to": [recipient_email],
        "subject": subject,
        "html": html_content,
    }

    try:
        email = await asyncio.to_thread(resend.Emails.send, params)
        logger.info("Email sent to %s with id %s", recipient_email, email.get("id"))
        result = {"status": "sent", "email_id": email.get("id")}
        await log_email_activity(recipient_email, subject, email_type, "sent", provider_id=email.get("id"), company_id=company_id, metadata=metadata)
        return result
    except Exception as exc:
        sanitized_error = sanitize_email_error(str(exc))
        logger.error("Failed to send email to %s: %s", recipient_email, sanitized_error)
        result = {"status": "failed", "error": sanitized_error}
        await log_email_activity(recipient_email, subject, email_type, "failed", provider_message=sanitized_error, company_id=company_id, metadata=metadata)
        return result


async def send_welcome_email(
    company_name: str,
    recipient_email: str,
    dashboard_url: Optional[str] = None,
    company_id: Optional[str] = None,
) -> Dict[str, Any]:
    html = render_email_template(
        title=f"Welcome to CultureShield, {company_name}",
        intro="Your organization is ready to start measuring cybersecurity culture across employees, departments, and risk behaviors.",
        bullets=[
            "Invite employees and launch your first survey",
            "Track awareness, behavior, and reporting scores",
            "Generate audit reports and review billing in one place",
        ],
        cta_label="Open dashboard" if dashboard_url else None,
        cta_url=dashboard_url,
        closing_note="If your Resend account is in testing mode, delivery will work only for verified recipient addresses.",
    )
    return await send_email_with_metadata(
        recipient_email=recipient_email,
        subject="Welcome to CultureShield AI",
        html_content=html,
        email_type="welcome_email",
        company_id=company_id,
        metadata={"company_name": company_name},
    )


async def send_survey_invite_email(
    employee_name: str,
    company_name: str,
    recipient_email: str,
    survey_url: Optional[str] = None,
    company_id: Optional[str] = None,
) -> Dict[str, Any]:
    html = render_email_template(
        title=f"Security survey invitation for {employee_name}",
        intro=f"{company_name} has invited you to complete a cybersecurity culture survey. Your responses help identify awareness gaps and reduce human risk.",
        bullets=[
            "The survey covers phishing, passwords, device security, and reporting habits",
            "Responses help the company build a stronger security culture",
            "The assessment only takes a few minutes to complete",
        ],
        cta_label="Start survey" if survey_url else None,
        cta_url=survey_url,
    )
    return await send_email_with_metadata(
        recipient_email=recipient_email,
        subject=f"{company_name} invited you to a security survey",
        html_content=html,
        email_type="survey_invite_email",
        company_id=company_id,
        metadata={"company_name": company_name, "employee_name": employee_name},
    )


async def send_survey_completion_email(
    company_name: str,
    recipient_email: str,
    employee_name: str,
    risk_level: str,
    company_id: Optional[str] = None,
) -> Dict[str, Any]:
    html = render_email_template(
        title="A survey response has been submitted",
        intro=f"{employee_name} completed their CultureShield survey for {company_name}.",
        bullets=[f"Detected risk level: {risk_level}", "You can review updated dashboard metrics and risk heatmaps immediately."],
    )
    return await send_email_with_metadata(
        recipient_email=recipient_email,
        subject="Survey completed in CultureShield",
        html_content=html,
        email_type="survey_completion_email",
        company_id=company_id,
        metadata={"company_name": company_name, "employee_name": employee_name, "risk_level": risk_level},
    )


async def send_report_ready_email(
    company_name: str,
    recipient_email: str,
    overall_score: float,
    report_url: Optional[str] = None,
    company_id: Optional[str] = None,
) -> Dict[str, Any]:
    html = render_email_template(
        title="Your audit report is ready",
        intro=f"CultureShield generated a fresh audit report for {company_name}. Your current overall culture score is {overall_score}/100.",
        bullets=[
            "Review executive summary and key findings",
            "Check your highest-risk behaviors and departments",
            "Share the PDF with stakeholders from the reports area",
        ],
        cta_label="Open report" if report_url else None,
        cta_url=report_url,
    )
    return await send_email_with_metadata(
        recipient_email=recipient_email,
        subject="Your CultureShield report is ready",
        html_content=html,
        email_type="report_ready_email",
        company_id=company_id,
        metadata={"company_name": company_name, "overall_score": overall_score},
    )


async def send_billing_event_email(
    company_name: str,
    recipient_email: str,
    notification_type: str,
    data: Dict[str, Any],
    company_id: Optional[str] = None,
) -> Dict[str, Any]:
    subjects = {
        "payment_success": "Payment received successfully",
        "payment_failed": "Payment attempt failed",
        "subscription_cancelled": "Subscription update confirmed",
        "subscription_resumed": "Subscription resumed",
        "plan_changed": "Your CultureShield plan changed",
        "abandoned_cart_scheduled": "Your checkout is waiting",
    }

    bullet_map = {
        "payment_success": [
            f"Plan: {data.get('plan', 'CultureShield plan')}",
            f"Amount: {data.get('amount', 'N/A')}",
        ],
        "payment_failed": ["We could not process the latest payment attempt.", "Please review your payment method in the billing portal."],
        "subscription_cancelled": ["Your subscription change has been recorded.", "Access remains available until the current billing period ends unless cancelled immediately."],
        "subscription_resumed": ["Recurring billing is active again.", "Your billing access and plan benefits remain available."],
        "plan_changed": [f"Previous plan: {data.get('old_plan', 'N/A')}", f"New plan: {data.get('new_plan', 'N/A')}"],
        "abandoned_cart_scheduled": [f"Plan selected: {data.get('plan_id', 'N/A')}", f"Amount: {data.get('amount', 'N/A')}"],
    }

    intro_map = {
        "payment_success": f"{company_name}, your latest CultureShield payment was recorded successfully.",
        "payment_failed": f"{company_name}, we could not complete the latest CultureShield payment attempt.",
        "subscription_cancelled": f"{company_name}, your CultureShield subscription was updated.",
        "subscription_resumed": f"{company_name}, your CultureShield subscription is active again.",
        "plan_changed": f"{company_name}, your CultureShield billing plan has been updated.",
        "abandoned_cart_scheduled": f"{company_name}, you started a CultureShield checkout but did not finish it yet.",
    }

    html = render_email_template(
        title=subjects.get(notification_type, "CultureShield billing update"),
        intro=intro_map.get(notification_type, f"{company_name}, there is a new billing event in your account."),
        bullets=bullet_map.get(notification_type, ["Review your billing portal for the latest details."]),
        closing_note="Delivery depends on Resend account permissions and verified recipients in testing mode.",
    )
    return await send_email_with_metadata(
        recipient_email=recipient_email,
        subject=subjects.get(notification_type, "CultureShield billing update"),
        html_content=html,
        email_type="billing_event_email",
        company_id=company_id,
        metadata={"company_name": company_name, "notification_type": notification_type, **data},
    )


async def send_password_reset_email(
    recipient_email: str,
    reset_url: str,
    company_id: Optional[str] = None,
) -> Dict[str, Any]:
    html = render_email_template(
        title="Reset your CultureShield password",
        intro="You requested to reset your password. Click the button below to set a new password. This link expires in 20 minutes and can only be used once.",
        bullets=[
            "If you did not request this reset, you can safely ignore this email.",
            "For your security, do not share the reset link with anyone.",
        ],
        cta_label="Reset password",
        cta_url=reset_url,
    )
    return await send_email_with_metadata(
        recipient_email=recipient_email,
        subject="Reset Your CultureShield Password",
        html_content=html,
        email_type="password_reset_email",
        company_id=company_id,
        metadata={"reset_url": reset_url},
    )


async def send_phishing_simulation_email(
    recipient_email: str,
    subject: str,
    html_content: str,
    company_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    return await send_email_with_metadata(
        recipient_email=recipient_email,
        subject=subject,
        html_content=html_content,
        email_type="phishing_simulation_email",
        company_id=company_id,
        metadata=metadata,
    )