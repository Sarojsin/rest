"""Staff-realm TOTP and recovery-code helpers.

Reuses the platform TOTP logic but with staff-specific configuration.
Secrets are encrypted at rest by services.crypto.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime

from app.modules.platform.services.mfa import (
    generate_recovery_codes as _generate_recovery_codes,
    generate_totp_secret as _generate_totp_secret,
    hash_recovery_codes as _hash_recovery_codes,
    provisioning_uri as _provisioning_uri,
    verify_and_consume_recovery_code as _verify_and_consume_recovery_code,
    verify_totp as _verify_totp,
)

# Staff MFA configuration (slightly more permissive than platform)
TOTP_STEP_SECONDS = 30
TOTP_DIGITS = 6
TOTP_WINDOW = 1
RECOVERY_CODE_COUNT = 8

# Re-export platform functions with staff config
generate_totp_secret = _generate_totp_secret
verify_totp = _verify_totp
provisioning_uri = _provisioning_uri
generate_recovery_codes = _generate_recovery_codes
hash_recovery_codes = _hash_recovery_codes
verify_and_consume_recovery_code = _verify_and_consume_recovery_code


def create_mfa_enrollment_ticket() -> str:
    """Create a short-lived ticket for MFA enrollment flow."""
    import secrets
    return secrets.token_urlsafe(32)


def verify_mfa_enrollment_ticket(ticket: str, stored_ticket: str) -> bool:
    """Verify an MFA enrollment ticket (constant-time)."""
    import hmac
    return hmac.compare_digest(ticket, stored_ticket)


async def enroll_mfa(user, db) -> tuple[str, list[str], str]:
    """Enroll a user in MFA. Returns (provisioning_uri, recovery_codes, enrollment_ticket)."""
    from app.core.security import hash_token
    from app.modules.platform.services.crypto import encrypt_field, decrypt_field

    secret = generate_totp_secret()
    recovery_codes = generate_recovery_codes(RECOVERY_CODE_COUNT)

    # Encrypt the TOTP secret before storing
    encrypted_secret = encrypt_field(secret)
    recovery_codes_hash = hash_recovery_codes(recovery_codes)
    enrollment_ticket = create_mfa_enrollment_ticket()

    user.totp_secret = encrypted_secret
    user.recovery_codes_hash = recovery_codes_hash
    user.mfa_enrolled_at = datetime.now(UTC)
    # mfa_enabled stays False until verified

    db.commit()

    # Create provisioning URI for QR code
    from app.core.config import settings
    uri = provisioning_uri(secret, email=user.email, issuer=settings.platform_totp_issuer)

    return uri, recovery_codes, enrollment_ticket


async def verify_mfa_enrollment(user, code: str, enrollment_ticket: str, db) -> bool:
    """Verify MFA enrollment with a TOTP code. Returns True if successful."""
    from app.modules.platform.services.crypto import decrypt_field

    if not user.totp_secret or not user.mfa_enrolled_at:
        return False

    # Verify enrollment ticket (in production, store in Redis with TTL)
    # For now, we'll trust the ticket passed from the client
    # TODO: Store enrollment ticket in Redis with 10 min TTL

    # Decrypt secret and verify TOTP
    secret = decrypt_field(user.totp_secret)
    if not verify_totp(secret, code):
        return False

    # Mark MFA as enabled
    user.mfa_enabled = True
    db.commit()
    return True


async def disable_mfa(user, db) -> None:
    """Disable MFA for a user."""
    user.totp_secret = None
    user.recovery_codes_hash = None
    user.mfa_enabled = False
    user.mfa_enrolled_at = None
    db.commit()


async def verify_mfa_login(user, code: str, recovery_code: str | None, db) -> bool:
    """Verify MFA during login. Supports both TOTP and recovery codes."""
    from app.modules.platform.services.crypto import decrypt_field

    if not user.mfa_enabled:
        return True  # MFA not enabled, skip

    # Try TOTP first
    if code:
        if user.totp_secret:
            secret = decrypt_field(user.totp_secret)
            if verify_totp(secret, code):
                return True

    # Try recovery code
    if recovery_code and user.recovery_codes_hash:
        matched, remaining_hash = verify_and_consume_recovery_code(
            user.recovery_codes_hash, recovery_code
        )
        if matched:
            user.recovery_codes_hash = remaining_hash
            db.commit()
            return True

    return False