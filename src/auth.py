"""Authentication, Role-Based Access Control (RBAC), and Session Security.

Provides:
- PBKDF2-HMAC-SHA256 password hashing with unique random salts.
- Cryptographically signed JSON Web Token (JWT) creation and verification using
  HMAC-SHA256 (standard library implementation, zero external dependency).
- Role-based authorization dependencies for FastAPI endpoints (Student vs. Advisor).
- Institutional email domain enforcement: only @iilm.edu addresses are accepted.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import time
from typing import Any

from fastapi import HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src import db


AUTH_SECRET_KEY = os.environ.get("EDUPREDICT_AUTH_SECRET", "edupredict-capstone-jwt-secret-key-2026")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_SECONDS = 86400 * 7  # 7 days

# ── Institutional Email Policy ────────────────────────────────────────────────
ALLOWED_EMAIL_DOMAIN = os.environ.get("IILM_EMAIL_DOMAIN", "iilm.edu")
# Demo accounts that bypass domain enforcement (internal use only)
_DEMO_EMAILS = {"aarav.sharma@iilm.edu", "dr.mehta@iilm.edu"}

security_bearer = HTTPBearer(auto_error=False)


def validate_iilm_email(email: str) -> None:
    """Raise HTTP 400 if the email address is not from the allowed institutional domain."""
    email = email.strip().lower()
    if not email.endswith(f"@{ALLOWED_EMAIL_DOMAIN}"):
        raise HTTPException(
            status_code=400,
            detail=(
                f"Only institutional @{ALLOWED_EMAIL_DOMAIN} email addresses are accepted. "
                "Please use your IILM University email to register."
            ),
        )


def hash_password(password: str, salt: str | None = None) -> str:
    """Hash password using PBKDF2-HMAC-SHA256 with 100,000 iterations."""
    if not salt:
        salt = secrets.token_hex(16)
    pw_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        100_000,
    ).hex()
    return f"{salt}${pw_hash}"


def verify_password(plain_password: str, stored_hash: str) -> bool:
    """Verify plain password against stored salt$hash string."""
    try:
        salt, expected_hash = stored_hash.split("$", 1)
        actual_hash = hashlib.pbkdf2_hmac(
            "sha256",
            plain_password.encode("utf-8"),
            salt.encode("utf-8"),
            100_000,
        ).hex()
        return hmac.compare_digest(actual_hash, expected_hash)
    except Exception:
        return False


def _base64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("utf-8").rstrip("=")


def _base64url_decode(s: str) -> bytes:
    padding = "=" * ((4 - len(s) % 4) % 4)
    return base64.urlsafe_b64decode(s + padding)


def create_access_token(user_id: int, email: str, role: str, full_name: str) -> str:
    """Generate a standard HS256-signed JWT token."""
    header = {"alg": JWT_ALGORITHM, "typ": "JWT"}
    now = int(time.time())
    payload = {
        "sub": str(user_id),
        "email": email,
        "role": role,
        "name": full_name,
        "iat": now,
        "exp": now + JWT_EXPIRATION_SECONDS,
    }

    header_bytes = json.dumps(header, separators=(",", ":")).encode("utf-8")
    payload_bytes = json.dumps(payload, separators=(",", ":")).encode("utf-8")

    unsigned_token = f"{_base64url_encode(header_bytes)}.{_base64url_encode(payload_bytes)}"
    signature = hmac.new(
        AUTH_SECRET_KEY.encode("utf-8"),
        unsigned_token.encode("utf-8"),
        hashlib.sha256,
    ).digest()

    return f"{unsigned_token}.{_base64url_encode(signature)}"


def decode_access_token(token: str) -> dict[str, Any]:
    """Validate and decode HS256-signed JWT token."""
    parts = token.split(".")
    if len(parts) != 3:
        raise HTTPException(status_code=401, detail="Malformed authorization token.")

    unsigned_token = f"{parts[0]}.{parts[1]}"
    expected_sig = hmac.new(
        AUTH_SECRET_KEY.encode("utf-8"),
        unsigned_token.encode("utf-8"),
        hashlib.sha256,
    ).digest()

    actual_sig = _base64url_decode(parts[2])
    if not hmac.compare_digest(expected_sig, actual_sig):
        raise HTTPException(status_code=401, detail="Invalid token signature.")

    try:
        payload = json.loads(_base64url_decode(parts[1]).decode("utf-8"))
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token payload encoding.")

    if payload.get("exp", 0) < int(time.time()):
        raise HTTPException(status_code=401, detail="Token expired. Please sign in again.")

    return payload


async def get_current_user_optional(
    auth: HTTPAuthorizationCredentials | None = Security(security_bearer),
) -> dict[str, Any] | None:
    """Return user info if token is present, else None (safe for public endpoints)."""
    if not auth or not auth.credentials:
        return None
    try:
        return decode_access_token(auth.credentials)
    except HTTPException:
        return None


async def require_authenticated_user(
    auth: HTTPAuthorizationCredentials | None = Security(security_bearer),
) -> dict[str, Any]:
    """Enforce valid JWT token on protected routes."""
    if not auth or not auth.credentials:
        raise HTTPException(status_code=401, detail="Authentication required. Please sign in.")
    return decode_access_token(auth.credentials)


async def require_advisor_role(
    auth: HTTPAuthorizationCredentials | None = Security(security_bearer),
) -> dict[str, Any]:
    """Enforce Advisor/Faculty authorization on institutional routes."""
    user = await require_authenticated_user(auth)
    if user.get("role") not in {"advisor", "admin"}:
        raise HTTPException(
            status_code=403,
            detail="Faculty Advisor role required to access this resource.",
        )
    return user
