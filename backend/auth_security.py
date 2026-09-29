import base64
import hashlib
import io
import os
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import pyotp
import qrcode
from cryptography.fernet import Fernet
from dotenv import load_dotenv
from fastapi import HTTPException, Request

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

MFA_ENCRYPTION_KEY = os.environ["MFA_ENCRYPTION_KEY"].encode()
RESET_TOKEN_TTL_MINUTES = int(os.environ["RESET_TOKEN_TTL_MINUTES"])
AUTH_RATE_LIMIT_WINDOW_MINUTES = int(os.environ["AUTH_RATE_LIMIT_WINDOW_MINUTES"])
AUTH_MAX_FAILED_ATTEMPTS = int(os.environ["AUTH_MAX_FAILED_ATTEMPTS"])

fernet = Fernet(MFA_ENCRYPTION_KEY)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def hash_value(raw_value: str) -> str:
    return hashlib.sha256(raw_value.encode()).hexdigest()


def create_random_token(length: int = 32) -> str:
    return secrets.token_urlsafe(length)


def encrypt_sensitive_value(raw_value: str) -> str:
    return fernet.encrypt(raw_value.encode()).decode()


def decrypt_sensitive_value(encrypted_value: str) -> str:
    return fernet.decrypt(encrypted_value.encode()).decode()


def validate_password_strength(password: str) -> Optional[str]:
    checks = [
        (len(password) >= 10, "Password must be at least 10 characters long."),
        (any(char.islower() for char in password), "Password must include a lowercase letter."),
        (any(char.isupper() for char in password), "Password must include an uppercase letter."),
        (any(char.isdigit() for char in password), "Password must include a number."),
        (any(not char.isalnum() for char in password), "Password must include a special character."),
    ]

    for is_valid, message in checks:
        if not is_valid:
            return message

    return None


def generate_backup_codes(count: int = 8) -> List[str]:
    return [f"{secrets.token_hex(2).upper()}-{secrets.token_hex(2).upper()}" for _ in range(count)]


def hash_backup_codes(codes: List[str]) -> List[Dict[str, Optional[str]]]:
    return [{"code_hash": hash_value(code), "used_at": None} for code in codes]


def consume_backup_code(code: str, stored_codes: List[Dict[str, Optional[str]]]) -> Optional[List[Dict[str, Optional[str]]]]:
    normalized_code = code.strip().upper()
    code_hash = hash_value(normalized_code)

    for backup_code in stored_codes:
        if backup_code.get("code_hash") == code_hash and not backup_code.get("used_at"):
            updated_codes = [dict(item) for item in stored_codes]
            for item in updated_codes:
                if item.get("code_hash") == code_hash and not item.get("used_at"):
                    item["used_at"] = utc_now().isoformat()
                    break
            return updated_codes

    return None


def get_remaining_backup_codes(stored_codes: List[Dict[str, Optional[str]]]) -> int:
    return sum(1 for item in stored_codes if not item.get("used_at"))


def create_totp_setup(email: str) -> Dict[str, str]:
    secret = pyotp.random_base32()
    uri = pyotp.TOTP(secret).provisioning_uri(name=email, issuer_name="CultureShield AI")

    qr = qrcode.QRCode(box_size=8, border=2)
    qr.add_data(uri)
    qr.make(fit=True)
    image = qr.make_image(fill_color="#1F3A5F", back_color="white")

    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    qr_base64 = base64.b64encode(buffer.getvalue()).decode()

    return {
        "secret": secret,
        "uri": uri,
        "qr_code_data_url": f"data:image/png;base64,{qr_base64}",
    }


def verify_totp_code(secret: str, code: str) -> bool:
    return pyotp.TOTP(secret).verify(code.strip().replace(" ", ""), valid_window=1)


def get_request_ip(request: Request) -> str:
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def parse_user_agent(user_agent: str) -> Dict[str, str]:
    ua = (user_agent or "").lower()
    browser = "Unknown browser"
    os_name = "Unknown OS"

    if "edg" in ua:
        browser = "Edge"
    elif "chrome" in ua and "edg" not in ua:
        browser = "Chrome"
    elif "safari" in ua and "chrome" not in ua:
        browser = "Safari"
    elif "firefox" in ua:
        browser = "Firefox"

    if "iphone" in ua or "ipad" in ua:
        os_name = "iOS"
    elif "android" in ua:
        os_name = "Android"
    elif "windows" in ua:
        os_name = "Windows"
    elif "mac os" in ua or "macintosh" in ua:
        os_name = "macOS"
    elif "linux" in ua:
        os_name = "Linux"

    return {"browser": browser, "os": os_name}


def build_device_name(user_agent: str) -> str:
    parsed = parse_user_agent(user_agent)
    return f"{parsed['browser']} on {parsed['os']}"


async def log_auth_event(
    db,
    event_type: str,
    status: str,
    email: Optional[str],
    company_id: Optional[str],
    ip_address: str,
    details: Optional[Dict[str, Any]] = None,
) -> None:
    event = {
        "id": str(uuid.uuid4()),
        "event_type": event_type,
        "status": status,
        "email": email,
        "company_id": company_id,
        "ip_address": ip_address,
        "details": details or {},
        "created_at": utc_now().isoformat(),
    }
    await db.auth_events.insert_one(event)


async def enforce_auth_rate_limit(db, email: str, ip_address: str, action: str) -> None:
    cutoff = (utc_now() - timedelta(minutes=AUTH_RATE_LIMIT_WINDOW_MINUTES)).isoformat()
    failed_attempts = await db.auth_events.count_documents(
        {
            "email": email.lower(),
            "ip_address": ip_address,
            "status": "failed",
            "event_type": {"$in": [f"{action}.failed", f"{action}.rate_limited"]},
            "created_at": {"$gte": cutoff},
        }
    )

    if failed_attempts >= AUTH_MAX_FAILED_ATTEMPTS:
        await log_auth_event(db, f"{action}.rate_limited", "failed", email.lower(), None, ip_address, {"failed_attempts": failed_attempts})
        raise HTTPException(status_code=429, detail="Too many failed attempts. Please wait and try again.")


async def create_password_reset_record(db, company_id: str, email: str) -> str:
    plain_token = create_random_token(24)
    now = utc_now()
    record = {
        "id": str(uuid.uuid4()),
        "company_id": company_id,
        "email": email.lower(),
        "token_hash": hash_value(plain_token),
        "used_at": None,
        "expires_at": (now + timedelta(minutes=RESET_TOKEN_TTL_MINUTES)).isoformat(),
        "created_at": now.isoformat(),
    }
    await db.password_reset_tokens.insert_one(record)
    return plain_token


async def get_valid_password_reset_record(db, plain_token: str) -> Optional[Dict[str, Any]]:
    record = await db.password_reset_tokens.find_one({"token_hash": hash_value(plain_token)}, {"_id": 0})
    if not record or record.get("used_at"):
        return None

    if utc_now() > datetime.fromisoformat(record["expires_at"].replace("Z", "+00:00")):
        return None

    return record


async def create_mfa_login_challenge(db, company_id: str, email: str) -> str:
    plain_token = create_random_token(24)
    now = utc_now()
    record = {
        "id": str(uuid.uuid4()),
        "company_id": company_id,
        "email": email.lower(),
        "token_hash": hash_value(plain_token),
        "used_at": None,
        "expires_at": (now + timedelta(minutes=10)).isoformat(),
        "created_at": now.isoformat(),
    }
    await db.mfa_login_challenges.insert_one(record)
    return plain_token


async def get_valid_mfa_login_challenge(db, plain_token: str) -> Optional[Dict[str, Any]]:
    record = await db.mfa_login_challenges.find_one({"token_hash": hash_value(plain_token)}, {"_id": 0})
    if not record or record.get("used_at"):
        return None

    if utc_now() > datetime.fromisoformat(record["expires_at"].replace("Z", "+00:00")):
        return None

    return record


async def create_auth_session(db, company_id: str, request: Request, mfa_verified: bool) -> str:
    session_id = str(uuid.uuid4())
    now = utc_now().isoformat()
    user_agent = request.headers.get("user-agent", "Unknown device")

    session = {
        "id": session_id,
        "company_id": company_id,
        "ip_address": get_request_ip(request),
        "user_agent": user_agent,
        "device_name": build_device_name(user_agent),
        "browser": parse_user_agent(user_agent)["browser"],
        "os": parse_user_agent(user_agent)["os"],
        "mfa_verified": mfa_verified,
        "revoked_at": None,
        "last_active_at": now,
        "created_at": now,
    }
    await db.auth_sessions.insert_one(session)
    return session_id


async def revoke_auth_session(db, session_id: str) -> None:
    await db.auth_sessions.update_one({"id": session_id}, {"$set": {"revoked_at": utc_now().isoformat()}})