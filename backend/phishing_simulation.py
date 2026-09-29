from html import escape
from typing import Dict, List


PHISHING_TEMPLATES: Dict[str, Dict[str, object]] = {
    "password_reset_urgent": {
        "id": "password_reset_urgent",
        "name": "Urgent password reset",
        "category": "Credential harvesting",
        "difficulty": "medium",
        "subject": "Urgent: your password expires today",
        "preview_text": "Your access will be limited unless you confirm your password immediately.",
        "scenario": "A rushed password-reset request designed to trigger instinctive clicks.",
        "cta_label": "Confirm your password",
        "sender_name": "IT Security Desk",
        "body": [
            "Our records show your company password is due to expire within the next hour.",
            "To avoid interruption, review the password policy notice and confirm your credentials.",
            "If you do not respond quickly, your collaboration tools may be locked temporarily.",
        ],
        "red_flags": [
            "Creates artificial urgency to force a fast decision",
            "Pushes you to act through an unexpected link",
            "Uses consequences and fear instead of normal IT process",
        ],
        "learning_points": [
            "Real password resets should come through known portals or support channels",
            "Urgent language is a common social-engineering tactic",
            "Pause and verify before entering credentials anywhere",
        ],
    },
    "invoice_review": {
        "id": "invoice_review",
        "name": "Invoice approval request",
        "category": "Finance lure",
        "difficulty": "easy",
        "subject": "Invoice requires your review before 4 PM",
        "preview_text": "An outstanding invoice has been flagged for quick validation.",
        "scenario": "A finance-style lure pushing staff to open a suspicious attachment or link.",
        "cta_label": "Review invoice",
        "sender_name": "Finance Operations",
        "body": [
            "A vendor invoice has been escalated for rapid review before today closes.",
            "Please confirm the payment record and acknowledge the billing note below.",
            "If this request is unfamiliar, slow down and verify with finance directly.",
        ],
        "red_flags": [
            "Unexpected money or invoice requests create pressure",
            "The request asks for quick action without normal context",
            "Sender context can feel internal even when it is suspicious",
        ],
        "learning_points": [
            "Finance-themed phishing often targets speed and authority",
            "Confirm invoice requests through known channels",
            "Watch for urgency, vague descriptions, and unusual links",
        ],
    },
    "shared_document": {
        "id": "shared_document",
        "name": "Shared document alert",
        "category": "Cloud-file lure",
        "difficulty": "hard",
        "subject": "A confidential document was shared with you",
        "preview_text": "Open the secure document review link to see the latest changes.",
        "scenario": "A familiar file-sharing workflow that hides a suspicious click path.",
        "cta_label": "Open shared document",
        "sender_name": "Document Collaboration",
        "body": [
            "A confidential update has been shared for your immediate review.",
            "Open the secure collaboration link to inspect the document and leave your comments.",
            "Attackers often imitate cloud-document notifications because they feel routine.",
        ],
        "red_flags": [
            "Unexpected document notifications exploit everyday collaboration habits",
            "The message may feel familiar even when context is missing",
            "Links should still be verified before you open them",
        ],
        "learning_points": [
            "Routine-looking file-share alerts can still be malicious",
            "Check whether you expected the file before clicking",
            "Use your normal collaboration platform directly if in doubt",
        ],
    },
}


def list_phishing_templates() -> List[dict]:
    return list(PHISHING_TEMPLATES.values())


def get_phishing_template(template_id: str) -> dict:
    template = PHISHING_TEMPLATES.get(template_id)
    if not template:
        raise ValueError("Unknown phishing template")
    return template


def render_phishing_email(template_id: str, employee_name: str, company_name: str, landing_url: str, open_pixel_url: str) -> dict:
    template = get_phishing_template(template_id)
    safe_name = escape(employee_name or "there")
    safe_company = escape(company_name)
    safe_sender = escape(str(template["sender_name"]))

    body_html = "".join(
        f"<p style='margin:0 0 14px;color:#334155;font-size:15px;line-height:1.7;'>{escape(paragraph)}</p>"
        for paragraph in template["body"]
    )

    html = f"""
    <table role='presentation' width='100%' cellpadding='0' cellspacing='0' style='background:#f8fafc;padding:24px 12px;font-family:Arial,sans-serif;'>
      <tr>
        <td align='center'>
          <table role='presentation' width='100%' cellpadding='0' cellspacing='0' style='max-width:620px;background:#ffffff;border:1px solid #dbe4ee;border-radius:20px;overflow:hidden;'>
            <tr>
              <td style='background:#f1f5f9;padding:18px 28px;'>
                <div style='font-size:12px;letter-spacing:0.18em;text-transform:uppercase;color:#64748b;'>{safe_sender}</div>
                <div style='margin-top:6px;font-size:13px;color:#94a3b8;'>Sent to {safe_name} at {safe_company}</div>
              </td>
            </tr>
            <tr>
              <td style='padding:32px 28px;'>
                <h1 style='margin:0 0 18px;color:#0f172a;font-size:28px;line-height:1.2;'>{escape(str(template['subject']))}</h1>
                {body_html}
                <div style='margin:28px 0;'>
                  <a href='{landing_url}' style='display:inline-block;background:#1F3A5F;color:#ffffff;text-decoration:none;padding:14px 22px;border-radius:999px;font-weight:600;'>{escape(str(template['cta_label']))}</a>
                </div>
                <p style='margin:18px 0 0;color:#94a3b8;font-size:12px;line-height:1.6;'>If you were not expecting this request, verify it through your normal company process.</p>
              </td>
            </tr>
          </table>
        </td>
      </tr>
    </table>
    <img src='{open_pixel_url}' alt='' width='1' height='1' style='display:block;border:0;opacity:0;' />
    """

    return {
        "subject": str(template["subject"]),
        "preview_text": str(template["preview_text"]),
        "html": html,
    }


def build_training_content(template_id: str, employee_name: str, company_name: str) -> dict:
    template = get_phishing_template(template_id)
    return {
        "title": str(template["name"]),
        "scenario": str(template["scenario"]),
        "employee_name": employee_name,
        "company_name": company_name,
        "red_flags": list(template["red_flags"]),
        "learning_points": list(template["learning_points"]),
        "difficulty": str(template["difficulty"]),
        "category": str(template["category"]),
    }