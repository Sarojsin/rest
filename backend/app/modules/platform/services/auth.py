"""Platform authentication service (PA-0.5).

Password verification, TOTP/recovery MFA, short-lived login tickets, rotating
refresh sessions, reuse detection, and session revocation.

No token is ever returned in a response body; the router places them in
HttpOnly cookies.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import jwt
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import (
    create_platform_access_token,
    hash_password,
    hash_token,
    new_token,
    verify_password,
)
from app.modules.platform.models import PlatformAdmin, PlatformRefreshToken
from app.modules.platform.schemas import PlatformAdminOut
from app.modules.platform.services.audit import write_platform_audit
from app.modules.platform.services.crypto import decrypt_secret, encrypt_secret
from app.modules.platform.services.mfa import (
    generate_recovery_codes,
    generate_totp_secret,
    hash_recovery_codes,
    provisioning_uri,
    verify_and_consume_recovery_code,
    verify_totp,
)
from app.shared.errors import AppError

ENROLL_PURPOSE = "mfa_enroll"
VERIFY_PURPOSE = "mfa_verify"

_ACTION_LOGIN_FAILED = "PLATFORM_LOGIN_FAILED"
_ACTION_LOGIN_SUCCESS = "PLATFORM_LOGIN_SUCCESS"
_ACTION_MFA_ENROLLED = "PLATFORM_MFA_ENROLLED"
_ACTION_MFA_FAILED = "PLATFORM_MFA_FAILED"
_ACTION_TOKEN_REFRESHED = "PLATFORM_TOKEN_REFRESHED"
_ACTION_REUSE_DETECTED = "PLATFORM_REFRESH_REUSE_DETECTED"
_ACTION_LOGOUT = "PLATFORM_LOGOUT"
_ACTION_SESSION_REVOKED = "PLATFORM_SESSION_REVOKED"
_ACTION_STEP_UP = "PLATFORM_STEP_UP"
_ACTION_STEP_UP_FAILED = "PLATFORM_STEP_UP_FAILED"

# A real Argon2 hash used to equalize timing for unknown emails.
_DUMMY_HASH = hash_password("not-a-real-platform-password")


@dataclass(frozen=True)
class LoginChallenge:
    enrollment_required: bool
    ticket: str
    expires_in: int


@dataclass(frozen=True)
class IssuedSession:
    access_token: str
    refresh_token: str
    csrf_token: str
    expires_in: int
    refresh_expires_at: datetime
    admin: PlatformAdminOut


@dataclass(frozen=True)
class VerifiedMfa:
    session: IssuedSession
    recovery_codes: list[str] | None = None
    extra: dict = field(default_factory=dict)


@dataclass(frozen=True)
class StepUpResult:
    access_token: str
    expires_in: int
    step_up_expires_in: int


def admin_out(admin: PlatformAdmin) -> PlatformAdminOut:
    return PlatformAdminOut(
        id=admin.id,
        email=admin.email,
        display_name=admin.display_name,
        role=admin.role,
        mfa_enabled=admin.mfa_enabled_at is not None,
    )


def _now() -> datetime:
    return datetime.now(UTC)


def _invalid_credentials() -> AppError:
    return AppError(
        401,
        "INVALID_CREDENTIALS",
        "Unauthorized",
        "Email or password is incorrect.",
    )


def _encode_ticket(*, admin: PlatformAdmin, purpose: str, minutes: int) -> str:
    now = _now()
    payload = {
        "sub": str(admin.id),
        "realm": "platform",
        "purpose": purpose,
        "ver": admin.token_version,
        "exp": now + timedelta(minutes=minutes),
        "iat": now,
    }
    return jwt.encode(payload, settings.platform_secret_key, algorithm="HS256")


def _decode_ticket(ticket: str, *, purpose: str) -> PlatformAdmin:
    try:
        payload = jwt.decode(ticket, settings.platform_secret_key, algorithms=["HS256"])
    except jwt.ExpiredSignatureError as exc:
        raise AppError(401, "TICKET_EXPIRED", "Unauthorized", "Sign in again.") from exc
    except jwt.InvalidTokenError as exc:
        raise AppError(401, "INVALID_TICKET", "Unauthorized", "Sign in again.") from exc

    if payload.get("realm") != "platform" or payload.get("purpose") != purpose:
        raise AppError(401, "INVALID_TICKET", "Unauthorized", "Sign in again.")
    return payload


def _find_admin_from_ticket(db: Session, ticket: str, *, purpose: str) -> PlatformAdmin:
    payload = _decode_ticket(ticket, purpose=purpose)
    try:
        admin_id = UUID(str(payload["sub"]))
    except (KeyError, ValueError) as exc:
        raise AppError(401, "INVALID_TICKET", "Unauthorized", "Sign in again.") from exc

    admin = db.get(PlatformAdmin, admin_id)
    if admin is None or admin.status != "ACTIVE":
        raise AppError(401, "INVALID_TICKET", "Unauthorized", "Sign in again.")
    if int(payload.get("ver", -1)) != admin.token_version:
        raise AppError(401, "TICKET_EXPIRED", "Unauthorized", "Sign in again.")
    return admin


def authenticate(
    db: Session,
    *,
    email: str,
    password: str,
    request=None,
) -> LoginChallenge:
    normalized = email.strip().lower()
    admin = db.scalar(select(PlatformAdmin).where(PlatformAdmin.email == normalized))
    now = _now()

    if admin is None:
        # Equalize timing so unknown emails are not distinguishable.
        verify_password(password, _DUMMY_HASH)
        write_platform_audit(
            db,
            action=_ACTION_LOGIN_FAILED,
            entity_type="platform_admin",
            entity_id="unknown",
            actor_email=normalized,
            reason="unknown email",
            request=request,
        )
        db.commit()
        raise _invalid_credentials()

    if admin.locked_until is not None and admin.locked_until > now:
        write_platform_audit(
            db,
            action=_ACTION_LOGIN_FAILED,
            entity_type="platform_admin",
            entity_id=str(admin.id),
            actor_admin_id=admin.id,
            actor_email=admin.email,
            reason="locked",
            request=request,
        )
        db.commit()
        raise AppError(
            401,
            "INVALID_CREDENTIALS",
            "Unauthorized",
            "Email or password is incorrect.",
        )

    if admin.status != "ACTIVE":
        write_platform_audit(
            db,
            action=_ACTION_LOGIN_FAILED,
            entity_type="platform_admin",
            entity_id=str(admin.id),
            actor_admin_id=admin.id,
            actor_email=admin.email,
            reason=f"status:{admin.status}",
            request=request,
        )
        db.commit()
        raise AppError(
            403,
            "ACCOUNT_DISABLED",
            "Forbidden",
            "This account is disabled.",
        )

    if not verify_password(password, admin.password_hash):
        admin.failed_login_count += 1
        if admin.failed_login_count >= settings.platform_login_max_attempts:
            admin.locked_until = now + timedelta(
                minutes=settings.platform_login_lockout_minutes
            )
            admin.failed_login_count = 0
        write_platform_audit(
            db,
            action=_ACTION_LOGIN_FAILED,
            entity_type="platform_admin",
            entity_id=str(admin.id),
            actor_admin_id=admin.id,
            actor_email=admin.email,
            reason="bad password",
            request=request,
        )
        db.commit()
        raise _invalid_credentials()

    admin.failed_login_count = 0
    admin.locked_until = None
    db.commit()

    if admin.mfa_enabled_at is None:
        minutes = settings.platform_enrollment_ticket_minutes
        return LoginChallenge(
            enrollment_required=True,
            ticket=_encode_ticket(admin=admin, purpose=ENROLL_PURPOSE, minutes=minutes),
            expires_in=minutes * 60,
        )

    minutes = settings.platform_mfa_ticket_minutes
    return LoginChallenge(
        enrollment_required=False,
        ticket=_encode_ticket(admin=admin, purpose=VERIFY_PURPOSE, minutes=minutes),
        expires_in=minutes * 60,
    )


def start_enrollment(
    db: Session,
    *,
    ticket: str,
    request=None,
) -> tuple[str, str]:
    admin = _find_admin_from_ticket(db, ticket, purpose=ENROLL_PURPOSE)
    if admin.mfa_enabled_at is not None:
        raise AppError(
            409,
            "MFA_ALREADY_ENABLED",
            "Conflict",
            "Multi-factor authentication is already enabled.",
        )

    secret = generate_totp_secret()
    # Store encrypted immediately so the secret is not carried in the ticket.
    admin.mfa_secret_encrypted = encrypt_secret(secret)
    db.commit()

    uri = provisioning_uri(secret, email=admin.email, issuer=settings.platform_totp_issuer)
    return secret, uri


def _create_session(
    db: Session,
    *,
    admin: PlatformAdmin,
    request=None,
) -> IssuedSession:
    now = _now()
    raw_refresh = new_token(32)
    refresh_expires = now + timedelta(minutes=settings.platform_refresh_token_minutes)

    row = PlatformRefreshToken(
        admin_id=admin.id,
        token_hash=hash_token(raw_refresh),
        family_id=uuid4(),
        session_started_at=now,
        expires_at=refresh_expires,
        ip=request.client.host if request is not None and request.client else None,
        user_agent=(
            (request.headers.get("user-agent") or "")[:255] or None
            if request is not None
            else None
        ),
    )
    db.add(row)

    admin.last_auth_at = now
    admin.last_login_at = now

    access = create_platform_access_token(
        admin_id=admin.id,
        role=admin.role,
        token_version=admin.token_version,
        auth_time=now,
        step_up_at=now,
    )
    return IssuedSession(
        access_token=access,
        refresh_token=raw_refresh,
        csrf_token=new_token(32),
        expires_in=settings.platform_access_token_minutes * 60,
        refresh_expires_at=refresh_expires,
        admin=admin_out(admin),
    )


def verify_enrollment(
    db: Session,
    *,
    ticket: str,
    code: str,
    request=None,
) -> VerifiedMfa:
    admin = _find_admin_from_ticket(db, ticket, purpose=ENROLL_PURPOSE)
    if admin.mfa_enabled_at is not None:
        raise AppError(409, "MFA_ALREADY_ENABLED", "Conflict", "MFA is already enabled.")
    if not admin.mfa_secret_encrypted:
        raise AppError(
            409,
            "MFA_NOT_STARTED",
            "Conflict",
            "Start MFA enrollment first.",
        )

    secret = decrypt_secret(admin.mfa_secret_encrypted)
    if not verify_totp(secret, code):
        write_platform_audit(
            db,
            action=_ACTION_MFA_FAILED,
            entity_type="platform_admin",
            entity_id=str(admin.id),
            actor_admin_id=admin.id,
            actor_email=admin.email,
            reason="enrollment code rejected",
            request=request,
        )
        db.commit()
        raise AppError(401, "MFA_INVALID", "Unauthorized", "The code is incorrect.")

    recovery_codes = generate_recovery_codes(settings.platform_recovery_code_count)
    now = _now()
    admin.mfa_recovery_codes_hash = hash_recovery_codes(recovery_codes)
    admin.mfa_enabled_at = now

    session = _create_session(db, admin=admin, request=request)
    write_platform_audit(
        db,
        action=_ACTION_MFA_ENROLLED,
        entity_type="platform_admin",
        entity_id=str(admin.id),
        actor_admin_id=admin.id,
        actor_email=admin.email,
        reason="mfa enrolled",
        request=request,
    )
    write_platform_audit(
        db,
        action=_ACTION_LOGIN_SUCCESS,
        entity_type="platform_admin",
        entity_id=str(admin.id),
        actor_admin_id=admin.id,
        actor_email=admin.email,
        reason="mfa enrollment completed",
        request=request,
    )
    db.commit()
    return VerifiedMfa(session=session, recovery_codes=recovery_codes)


def verify_mfa(
    db: Session,
    *,
    ticket: str,
    code: str,
    request=None,
) -> VerifiedMfa:
    admin = _find_admin_from_ticket(db, ticket, purpose=VERIFY_PURPOSE)
    if admin.mfa_enabled_at is None or not admin.mfa_secret_encrypted:
        raise AppError(409, "MFA_NOT_ENROLLED", "Conflict", "MFA is not enabled.")

    secret = decrypt_secret(admin.mfa_secret_encrypted)
    recovery_used = False
    if not verify_totp(secret, code):
        matched, remaining = verify_and_consume_recovery_code(
            admin.mfa_recovery_codes_hash, code
        )
        if not matched:
            write_platform_audit(
                db,
                action=_ACTION_MFA_FAILED,
                entity_type="platform_admin",
                entity_id=str(admin.id),
                actor_admin_id=admin.id,
                actor_email=admin.email,
                reason="mfa code rejected",
                request=request,
            )
            db.commit()
            raise AppError(401, "MFA_INVALID", "Unauthorized", "The code is incorrect.")
        admin.mfa_recovery_codes_hash = remaining
        recovery_used = True

    session = _create_session(db, admin=admin, request=request)
    write_platform_audit(
        db,
        action=_ACTION_LOGIN_SUCCESS,
        entity_type="platform_admin",
        entity_id=str(admin.id),
        actor_admin_id=admin.id,
        actor_email=admin.email,
        reason="mfa verified",
        request=request,
        after={"recovery_code_used": recovery_used},
    )
    db.commit()
    return VerifiedMfa(session=session, extra={"recovery_code_used": recovery_used})


def _revoke_family(db: Session, *, family_id: UUID, reason: str, now: datetime) -> None:
    rows = db.scalars(
        select(PlatformRefreshToken).where(
            PlatformRefreshToken.family_id == family_id,
            PlatformRefreshToken.revoked_at.is_(None),
        )
    ).all()
    for row in rows:
        row.revoked_at = now
        row.revoked_reason = reason


def refresh_session(
    db: Session,
    *,
    raw_refresh: str,
    request=None,
) -> IssuedSession:
    now = _now()
    row = db.scalar(
        select(PlatformRefreshToken)
        .where(PlatformRefreshToken.token_hash == hash_token(raw_refresh))
        .with_for_update()
    )
    if row is None:
        raise AppError(401, "AUTH_REQUIRED", "Unauthorized", "Sign in again.")

    if row.revoked_at is not None:
        raise AppError(401, "TOKEN_REVOKED", "Unauthorized", "Session is no longer valid.")

    if row.rotated_at is not None:
        # A already-rotated token is being replayed: burn the whole family.
        _revoke_family(db, family_id=row.family_id, reason="REUSE_DETECTED", now=now)
        write_platform_audit(
            db,
            action=_ACTION_REUSE_DETECTED,
            entity_type="platform_refresh_token",
            entity_id=str(row.id),
            actor_admin_id=row.admin_id,
            reason="refresh token reuse",
            request=request,
        )
        db.commit()
        raise AppError(401, "TOKEN_REUSE", "Unauthorized", "Sign in again.")

    if row.expires_at <= now:
        row.revoked_at = now
        row.revoked_reason = "EXPIRED"
        db.commit()
        raise AppError(401, "TOKEN_EXPIRED", "Unauthorized", "Sign in again.")

    admin = db.get(PlatformAdmin, row.admin_id)
    if admin is None or admin.status != "ACTIVE":
        _revoke_family(db, family_id=row.family_id, reason="ADMIN_DISABLED", now=now)
        db.commit()
        raise AppError(401, "TOKEN_REVOKED", "Unauthorized", "Session is no longer valid.")

    raw_new = new_token(32)
    absolute_expiry = row.session_started_at + timedelta(
        minutes=settings.platform_refresh_token_minutes
    )
    new_expiry = min(now + timedelta(minutes=settings.platform_refresh_token_minutes), absolute_expiry)

    new_row = PlatformRefreshToken(
        admin_id=admin.id,
        token_hash=hash_token(raw_new),
        family_id=row.family_id,
        session_started_at=row.session_started_at,
        expires_at=new_expiry,
        ip=request.client.host if request is not None and request.client else None,
        user_agent=(
            (request.headers.get("user-agent") or "")[:255] or None
            if request is not None
            else None
        ),
    )
    db.add(new_row)
    db.flush()
    row.rotated_at = now
    row.replaced_by_id = new_row.id

    access = create_platform_access_token(
        admin_id=admin.id,
        role=admin.role,
        token_version=admin.token_version,
        auth_time=now,
        step_up_at=None,
    )
    write_platform_audit(
        db,
        action=_ACTION_TOKEN_REFRESHED,
        entity_type="platform_refresh_token",
        entity_id=str(new_row.id),
        actor_admin_id=admin.id,
        actor_email=admin.email,
        reason="rotated",
        request=request,
    )
    db.commit()
    return IssuedSession(
        access_token=access,
        refresh_token=raw_new,
        csrf_token=new_token(32),
        expires_in=settings.platform_access_token_minutes * 60,
        refresh_expires_at=new_expiry,
        admin=admin_out(admin),
    )


def logout(db: Session, *, raw_refresh: str | None, request=None) -> None:
    if not raw_refresh:
        return
    row = db.scalar(
        select(PlatformRefreshToken).where(
            PlatformRefreshToken.token_hash == hash_token(raw_refresh)
        )
    )
    if row is None:
        return
    _revoke_family(db, family_id=row.family_id, reason="LOGOUT", now=_now())
    write_platform_audit(
        db,
        action=_ACTION_LOGOUT,
        entity_type="platform_admin",
        entity_id=str(row.admin_id),
        actor_admin_id=row.admin_id,
        reason="logout",
        request=request,
    )
    db.commit()


def step_up(db: Session, *, admin_id: UUID, password: str, code: str, request=None) -> StepUpResult:
    admin = db.get(PlatformAdmin, admin_id)
    if admin is None or admin.status != "ACTIVE":
        raise AppError(401, "AUTH_REQUIRED", "Unauthorized", "Sign in again.")

    if not verify_password(password, admin.password_hash):
        write_platform_audit(
            db,
            action=_ACTION_STEP_UP_FAILED,
            entity_type="platform_admin",
            entity_id=str(admin.id),
            actor_admin_id=admin.id,
            actor_email=admin.email,
            reason="bad password",
            request=request,
        )
        db.commit()
        raise _invalid_credentials()

    secret = decrypt_secret(admin.mfa_secret_encrypted or "")
    recovery_used = False
    if not verify_totp(secret, code):
        matched, remaining = verify_and_consume_recovery_code(
            admin.mfa_recovery_codes_hash, code
        )
        if not matched:
            write_platform_audit(
                db,
                action=_ACTION_STEP_UP_FAILED,
                entity_type="platform_admin",
                entity_id=str(admin.id),
                actor_admin_id=admin.id,
                actor_email=admin.email,
                reason="mfa code rejected",
                request=request,
            )
            db.commit()
            raise AppError(401, "MFA_INVALID", "Unauthorized", "The code is incorrect.")
        admin.mfa_recovery_codes_hash = remaining
        recovery_used = True

    now = _now()
    admin.last_auth_at = now
    access = create_platform_access_token(
        admin_id=admin.id,
        role=admin.role,
        token_version=admin.token_version,
        auth_time=now,
        step_up_at=now,
    )
    write_platform_audit(
        db,
        action=_ACTION_STEP_UP,
        entity_type="platform_admin",
        entity_id=str(admin.id),
        actor_admin_id=admin.id,
        actor_email=admin.email,
        reason="step-up verified",
        request=request,
        after={"recovery_code_used": recovery_used},
    )
    db.commit()
    return StepUpResult(
        access_token=access,
        expires_in=settings.platform_access_token_minutes * 60,
        step_up_expires_in=settings.platform_step_up_minutes * 60,
    )


def list_sessions(
    db: Session,
    *,
    admin_id: UUID,
    current_refresh: str | None = None,
) -> list[dict]:
    current_hash = hash_token(current_refresh) if current_refresh else None
    rows = db.scalars(
        select(PlatformRefreshToken)
        .where(
            PlatformRefreshToken.admin_id == admin_id,
            PlatformRefreshToken.revoked_at.is_(None),
            PlatformRefreshToken.rotated_at.is_(None),
            PlatformRefreshToken.expires_at > _now(),
        )
        .order_by(PlatformRefreshToken.session_started_at.desc())
    ).all()
    return [
        {
            "family_id": row.family_id,
            "created_at": row.session_started_at,
            "expires_at": row.expires_at,
            "ip": row.ip,
            "user_agent": row.user_agent,
            "current": current_hash is not None and row.token_hash == current_hash,
        }
        for row in rows
    ]


def revoke_session(
    db: Session,
    *,
    admin_id: UUID,
    family_id: UUID,
    request=None,
) -> None:
    belongs = db.scalar(
        select(PlatformRefreshToken.id).where(
            PlatformRefreshToken.family_id == family_id,
            PlatformRefreshToken.admin_id == admin_id,
        )
    )
    if belongs is None:
        raise AppError(404, "SESSION_NOT_FOUND", "Not found", "Session not found.")
    _revoke_family(db, family_id=family_id, reason="SIGN_OUT_ALL", now=_now())
    write_platform_audit(
        db,
        action=_ACTION_SESSION_REVOKED,
        entity_type="platform_refresh_token_family",
        entity_id=str(family_id),
        actor_admin_id=admin_id,
        reason="session revoked",
        request=request,
    )
    db.commit()


def revoke_all_sessions(db: Session, *, admin_id: UUID, request=None) -> int:
    rows = db.scalars(
        select(PlatformRefreshToken).where(
            PlatformRefreshToken.admin_id == admin_id,
            PlatformRefreshToken.revoked_at.is_(None),
        )
    ).all()
    now = _now()
    families = set()
    for row in rows:
        families.add(row.family_id)
        row.revoked_at = now
        row.revoked_reason = "SIGN_OUT_ALL"
    write_platform_audit(
        db,
        action=_ACTION_SESSION_REVOKED,
        entity_type="platform_admin",
        entity_id=str(admin_id),
        actor_admin_id=admin_id,
        reason="all sessions revoked",
        request=request,
    )
    db.commit()
    return len(families)
