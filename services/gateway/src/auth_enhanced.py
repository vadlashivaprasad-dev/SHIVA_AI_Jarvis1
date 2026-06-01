"""
Enhanced authentication module with refresh tokens, account lockout, and security features.
"""

import base64
import hashlib
import hmac
import json
import os
import time
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from uuid import uuid4

from fastapi import Header, HTTPException, status

from .config import Settings, get_settings
from .schemas import UserPublic


# Account lockout tracking (use Redis in production)
_failed_login_attempts: dict[str, list[float]] = defaultdict(list)
_locked_accounts: dict[str, float] = {}


def hash_password(password: str) -> str:
    """Hash password using PBKDF2 with SHA256."""
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 120_000)
    return f"pbkdf2_sha256${base64.urlsafe_b64encode(salt).decode()}${base64.urlsafe_b64encode(digest).decode()}"


def verify_password(password: str, password_hash: str) -> bool:
    """Verify password against hash."""
    try:
        algorithm, salt_b64, digest_b64 = password_hash.split("$", 2)
    except ValueError:
        return False
    
    if algorithm != "pbkdf2_sha256":
        return False
    
    salt = base64.urlsafe_b64decode(salt_b64.encode())
    expected = base64.urlsafe_b64decode(digest_b64.encode())
    actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 120_000)
    
    return hmac.compare_digest(actual, expected)


def _b64encode(payload: bytes) -> str:
    """Base64 URL-safe encode."""
    return base64.urlsafe_b64encode(payload).decode().rstrip("=")


def _b64decode(payload: str) -> bytes:
    """Base64 URL-safe decode."""
    padding = "=" * (-len(payload) % 4)
    return base64.urlsafe_b64decode(f"{payload}{padding}".encode())


def create_access_token(user: UserPublic, settings: Settings | None = None) -> str:
    """Create JWT access token."""
    current_settings = settings or get_settings()
    
    header = {"alg": "HS256", "typ": "JWT"}
    expires_at = datetime.now(timezone.utc) + timedelta(
        minutes=current_settings.access_token_minutes
    )
    
    payload: dict[str, Any] = {
        "sub": user.id,
        "email": user.email,
        "role": user.role,
        "type": "access",
        "exp": int(expires_at.timestamp()),
        "iat": int(datetime.now(timezone.utc).timestamp()),
        "jti": str(uuid4()),
    }
    
    encoded_header = _b64encode(json.dumps(header, separators=(",", ":")).encode())
    encoded_payload = _b64encode(json.dumps(payload, separators=(",", ":")).encode())
    signing_input = f"{encoded_header}.{encoded_payload}".encode()
    
    signature = hmac.new(
        current_settings.jwt_secret.encode(),
        signing_input,
        hashlib.sha256,
    ).digest()
    
    return f"{encoded_header}.{encoded_payload}.{_b64encode(signature)}"


def create_refresh_token(user: UserPublic, settings: Settings | None = None) -> str:
    """Create JWT refresh token (longer expiry)."""
    current_settings = settings or get_settings()
    
    header = {"alg": "HS256", "typ": "JWT"}
    expires_at = datetime.now(timezone.utc) + timedelta(
        days=current_settings.refresh_token_days
    )
    
    payload: dict[str, Any] = {
        "sub": user.id,
        "email": user.email,
        "type": "refresh",
        "exp": int(expires_at.timestamp()),
        "iat": int(datetime.now(timezone.utc).timestamp()),
        "jti": str(uuid4()),
    }
    
    encoded_header = _b64encode(json.dumps(header, separators=(",", ":")).encode())
    encoded_payload = _b64encode(json.dumps(payload, separators=(",", ":")).encode())
    signing_input = f"{encoded_header}.{encoded_payload}".encode()
    
    signature = hmac.new(
        current_settings.jwt_secret.encode(),
        signing_input,
        hashlib.sha256,
    ).digest()
    
    return f"{encoded_header}.{encoded_payload}.{_b64encode(signature)}"


def decode_access_token(token: str, settings: Settings | None = None) -> dict[str, Any]:
    """Decode and validate JWT token."""
    current_settings = settings or get_settings()
    
    try:
        encoded_header, encoded_payload, encoded_signature = token.split(".", 2)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        ) from exc
    
    signing_input = f"{encoded_header}.{encoded_payload}".encode()
    expected_signature = hmac.new(
        current_settings.jwt_secret.encode(),
        signing_input,
        hashlib.sha256,
    ).digest()
    
    actual_signature = _b64decode(encoded_signature)
    
    if not hmac.compare_digest(expected_signature, actual_signature):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )
    
    payload = json.loads(_b64decode(encoded_payload))
    
    # Allow small clock skew
    leeway_seconds = 10
    if int(payload.get("exp", 0)) < int(datetime.now(timezone.utc).timestamp()) - leeway_seconds:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired"
        )
    
    # Ensure token type is correct
    if payload.get("type") not in ("access", "refresh"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type"
        )
    
    return payload


def get_bearer_payload(authorization: str | None = Header(default=None)) -> dict[str, Any]:
    """Extract and validate bearer token from Authorization header."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token"
        )
    
    token = authorization.removeprefix("Bearer ").strip()
    return decode_access_token(token)


def require_role(payload: dict[str, Any], allowed_roles: set[str]) -> None:
    """Check if user has required role."""
    role = payload.get("role", "user")
    if role not in allowed_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions"
        )


def check_account_lockout(email: str, settings: Settings | None = None) -> None:
    """Check if account is locked due to failed login attempts."""
    current_settings = settings or get_settings()
    
    # Check if account is locked
    if email in _locked_accounts:
        lockout_expiry = _locked_accounts[email]
        if time.time() < lockout_expiry:
            remaining = int(lockout_expiry - time.time())
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Account locked. Try again in {remaining} seconds"
            )
        else:
            # Lockout expired, reset attempts
            del _locked_accounts[email]
            _failed_login_attempts[email] = []


def record_failed_login(email: str, settings: Settings | None = None) -> None:
    """Record failed login attempt and lock account if threshold exceeded."""
    current_settings = settings or get_settings()
    
    now = time.time()
    
    # Remove old attempts (outside 1 hour window)
    _failed_login_attempts[email] = [
        ts for ts in _failed_login_attempts[email]
        if now - ts < 3600
    ]
    
    # Add current failed attempt
    _failed_login_attempts[email].append(now)
    
    # Lock account if threshold exceeded
    if len(_failed_login_attempts[email]) >= current_settings.max_login_attempts:
        lockout_until = now + (current_settings.lockout_duration_minutes * 60)
        _locked_accounts[email] = lockout_until


def record_successful_login(email: str) -> None:
    """Reset failed login attempts on successful login."""
    if email in _failed_login_attempts:
        _failed_login_attempts[email] = []
    if email in _locked_accounts:
        del _locked_accounts[email]


def validate_password_strength(password: str) -> None:
    """Validate password meets security requirements."""
    errors = []
    
    if len(password) < 8:
        errors.append("Password must be at least 8 characters")
    
    if not any(c.isupper() for c in password):
        errors.append("Password must contain uppercase letter")
    
    if not any(c.islower() for c in password):
        errors.append("Password must contain lowercase letter")
    
    if not any(c.isdigit() for c in password):
        errors.append("Password must contain digit")
    
    if not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):
        errors.append("Password must contain special character")
    
    if errors:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="; ".join(errors)
        )


def generate_csrf_token() -> str:
    """Generate a CSRF token."""
    import secrets
    return secrets.token_urlsafe(32)
