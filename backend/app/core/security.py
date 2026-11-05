import hashlib
import secrets
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from app.core.config import settings
from app.shared.errors import AppError

# Account lockout tracking (in production, use Redis for persistence)
# Key: "lockout:{user_id}", Value: {"failed_attempts": int, "locked_until": datetime}
lockout_store: dict = defaultdict(lambda: {"failed_attempts": 0, "locked_until": None})

password_hasher = PasswordHasher()
# Password policy constants
MIN_PASSWORD_LENGTH = 8
MAX_PASSWORD_LENGTH = 128
REQUIRE_UPPERCASE = True
REQUIRE_LOWERCASE = True
REQUIRE_NUMBER = True
REQUIRE_SPECIAL = True
MAX_FAILED_LOGIN_ATTEMPTS = 5
LOCKOUT_DURATION_MINUTES = 30


def hash_password(password: str) -> str:
    return password_hasher.hash(password)


def is_account_locked(user_id: UUID) -> bool:
    """Check if user account is currently locked out."""
    lockout_key = f"lockout:{user_id}"
    lockout_data = lockout_store.get(lockout_key)
    if not lockout_data:
        return False

    locked_until = lockout_data.get("locked_until")
    if not locked_until:
        # Not locked yet — keep counting failed attempts.
        return False

    if datetime.now(UTC) > locked_until:
        # Lockout expired, forget the entry entirely.
        lockout_store.pop(lockout_key, None)
        return False

    return True


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return password_hasher.verify(password_hash, password)
    except VerifyMismatchError:
        return False


def validate_password_policy(password: str) -> tuple[bool, list[str]]:
    """Validate password against policy requirements.
    
    Returns (is_valid, list_of_errors)
    """
    errors: list[str] = []
    
    if len(password) < MIN_PASSWORD_LENGTH:
        errors.append(f"Password must be at least {MIN_PASSWORD_LENGTH} characters")
    if len(password) > MAX_PASSWORD_LENGTH:
        errors.append(f"Password must be at most {MAX_PASSWORD_LENGTH} characters")
    
    if REQUIRE_UPPERCASE and not any(c.isupper() for c in password):
        errors.append("Password must contain at least one uppercase letter")
    
    if REQUIRE_LOWERCASE and not any(c.islower() for c in password):
        errors.append("Password must contain at least one lowercase letter")
    
    if REQUIRE_NUMBER and not any(c.isdigit() for c in password):
        errors.append("Password must contain at least one number")
    
    if REQUIRE_SPECIAL and not any(c in "!@#$%^&*()-_=+[]{}|;:'\",.<>?/`~" for c in password):
        errors.append("Password must contain at least one special character")
    
    return len(errors) == 0, errors


def record_failed_login(user_id: UUID) -> dict:
    """Record a failed login attempt and return lockout status."""
    lockout_key = f"lockout:{user_id}"
    data = lockout_store[lockout_key]
    data["failed_attempts"] += 1
    
    if data["failed_attempts"] >= MAX_FAILED_LOGIN_ATTEMPTS:
        from datetime import UTC, timedelta
        data["locked_until"] = datetime.now(UTC) + timedelta(minutes=LOCKOUT_DURATION_MINUTES)
        data["failed_attempts"] = 0  # Reset counter after lockout
        return {"locked": True, "duration_minutes": LOCKOUT_DURATION_MINUTES}
    
    return {"locked": False, "attempts": data["failed_attempts"]}


def record_successful_login(user_id: UUID) -> None:
    """Reset failed login counter after successful authentication."""
    lockout_key = f"lockout:{user_id}"
    lockout_store[lockout_key] = {"failed_attempts": 0, "locked_until": None}


def hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def new_token(nbytes: int = 32) -> str:
    return secrets.token_urlsafe(nbytes)


def create_access_token(
    *,
    user_id: UUID,
    membership_id: UUID,
    restaurant_id: UUID,
    tenant_id: UUID | None = None,
    realm: str = "staff",
    token_version: int = 0,
) -> str:
    expires = datetime.now(UTC) + timedelta(minutes=settings.access_token_minutes)
    payload = {
        "sub": str(user_id),
        "mid": str(membership_id),
        "rid": str(restaurant_id),
        "tenant_id": str(tenant_id) if tenant_id else None,
        "realm": realm,
        "ver": token_version,
        "exp": expires,
        "iat": datetime.now(UTC),
    }
    return jwt.encode(payload, settings.secret_key, algorithm="HS256")


def decode_access_token(token: str, *, expected_realm: str = "staff") -> dict:
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
        # Validate that the token has required claims
        if "sub" not in payload or "mid" not in payload or "rid" not in payload:
            raise jwt.InvalidTokenError("Missing required claims in token")
        if payload.get("realm") != expected_realm:
            raise AppError(
                401,
                "WRONG_REALM",
                "Unauthorized",
                "This token is not valid for this application.",
            )
        return payload
    except jwt.ExpiredSignatureError as exc:
        raise AppError(
            401, "TOKEN_EXPIRED", "Unauthorized", "Session expired. Sign in again."
        ) from exc
    except jwt.InvalidTokenError as exc:
        raise AppError(
            401, "INVALID_TOKEN", "Unauthorized", "Authentication is required."
        ) from exc


def create_platform_access_token(
    *,
    admin_id: UUID,
    role: str,
    token_version: int,
    auth_time: datetime | None = None,
    step_up_at: datetime | None = None,
) -> str:
    """Mint a platform-realm access token.

    Signed with ``platform_secret_key`` only. Deliberately carries no
    ``mid``/``rid``: tenant scope is always an explicit target ID on the
    request, never ambient in the token.
    """
    if not settings.platform_signing_key:
        raise RuntimeError("PLATFORM_SECRET_KEY is not configured")

    now = datetime.now(UTC)
    payload = {
        "sub": str(admin_id),
        "realm": "platform",
        "role": role,
        "ver": token_version,
        "jti": str(uuid4()),
        "auth_time": int((auth_time or now).timestamp()),
        "step_up_at": int(step_up_at.timestamp()) if step_up_at else None,
        "exp": now + timedelta(minutes=settings.platform_access_token_minutes),
        "iat": now,
    }
    return jwt.encode(payload, settings.platform_signing_key, algorithm="HS256")


def decode_platform_access_token(token: str) -> dict:
    if not settings.platform_signing_key:
        raise RuntimeError("PLATFORM_SECRET_KEY is not configured")

    try:
        payload = jwt.decode(token, settings.platform_signing_key, algorithms=["HS256"])
    except jwt.ExpiredSignatureError as exc:
        raise AppError(
            401, "TOKEN_EXPIRED", "Unauthorized", "Session expired. Sign in again."
        ) from exc
    except jwt.InvalidTokenError as exc:
        raise AppError(
            401, "INVALID_TOKEN", "Unauthorized", "Authentication is required."
        ) from exc

    if payload.get("realm") != "platform":
        raise AppError(
            401,
            "WRONG_REALM",
            "Unauthorized",
            "This token is not valid for this application.",
        )
    if "sub" not in payload or "ver" not in payload:
        raise AppError(
            401, "INVALID_TOKEN", "Unauthorized", "Authentication is required."
        )
    return payload
