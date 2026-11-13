"""Platform authentication routes (PA-0.5).

Mounted under ``/api/platform`` by the composition layer (PA-0.14). Tokens are
only ever delivered as cookies.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Request, Response, status
from pydantic import BaseModel, Field
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import hash_password, hash_token, validate_password_policy
from app.db.session import get_db
from app.modules.platform.constants import PLATFORM_REFRESH_COOKIE
from app.modules.platform.deps import PlatformActor, get_platform_admin
from app.modules.platform.models import (
    PlatformAdmin,
    PlatformOneTimeToken,
    PlatformRefreshToken,
)
from app.modules.platform.schemas import (
    AuthSuccessOut,
    LoginChallengeOut,
    LoginRequest,
    MfaCodeRequest,
    MfaEnrollStartOut,
    MfaEnrollStartRequest,
    PlatformMeOut,
    PlatformSessionOut,
    PlatformSessionsOut,
    StepUpOut,
    StepUpRequest,
)
from app.modules.platform.schemas_admin import InviteAcceptRequest
from app.modules.platform.services import auth
from app.modules.platform.services.audit import write_platform_audit
from app.modules.tenancy.services import platform_directory
from app.modules.platform.services.cookies import (
    clear_auth_cookies,
    set_access_cookie,
    set_auth_cookies,
)
from app.shared.errors import AppError

router = APIRouter(prefix="/auth", tags=["platform-auth"])


@router.post("/login", response_model=LoginChallengeOut)
def login(
    payload: LoginRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> LoginChallengeOut:
    challenge = auth.authenticate(
        db,
        email=str(payload.email),
        password=payload.password,
        request=request,
    )
    return LoginChallengeOut(
        enrollment_required=challenge.enrollment_required,
        ticket=challenge.ticket,
        expires_in=challenge.expires_in,
    )


@router.post("/mfa/enroll/start", response_model=MfaEnrollStartOut)
def start_mfa_enrollment(
    payload: MfaEnrollStartRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> MfaEnrollStartOut:
    secret, uri = auth.start_enrollment(db, ticket=payload.ticket, request=request)
    return MfaEnrollStartOut(
        secret=secret,
        provisioning_uri=uri,
        issuer=settings.platform_totp_issuer,
    )


@router.post("/mfa/enroll/verify", response_model=AuthSuccessOut)
def verify_mfa_enrollment(
    payload: MfaCodeRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> AuthSuccessOut:
    result = auth.verify_enrollment(
        db,
        ticket=payload.ticket,
        code=payload.code,
        request=request,
    )
    set_auth_cookies(response, result.session)
    return AuthSuccessOut(
        admin=result.session.admin,
        expires_in=result.session.expires_in,
        recovery_codes=result.recovery_codes,
        csrf_token=result.session.csrf_token,
    )


# ---------------------------------------------------------------------------
# Session-based MFA enrollment (settings flow — no login challenge ticket)
# ---------------------------------------------------------------------------


class MfaEnrollSessionStartOut(BaseModel):
    secret: str
    provisioning_uri: str
    issuer: str


class MfaEnrollSessionVerifyRequest(BaseModel):
    code: str = Field(min_length=1, max_length=32)


class MfaEnrollSessionVerifyOut(BaseModel):
    ok: bool
    recovery_codes: list[str] | None = None
    csrf_token: str | None = None


@router.post("/mfa/enroll/start-session", response_model=MfaEnrollSessionStartOut)
def start_mfa_enrollment_session(
    request: Request,
    actor: PlatformActor = Depends(get_platform_admin),
    db: Session = Depends(get_db),
) -> MfaEnrollSessionStartOut:
    """Start MFA enrollment for the currently authenticated admin (settings flow)."""
    secret, uri = auth.start_enrollment_for_admin(db, admin_id=actor.admin_id, request=request)
    return MfaEnrollSessionStartOut(
        secret=secret,
        provisioning_uri=uri,
        issuer=settings.platform_totp_issuer,
    )


@router.post("/mfa/enroll/verify-session", response_model=MfaEnrollSessionVerifyOut)
def verify_mfa_enrollment_session(
    payload: MfaEnrollSessionVerifyRequest,
    request: Request,
    response: Response,
    actor: PlatformActor = Depends(get_platform_admin),
    db: Session = Depends(get_db),
) -> MfaEnrollSessionVerifyOut:
    """Complete MFA enrollment for the currently authenticated admin (settings flow)."""
    result = auth.verify_enrollment_for_admin(
        db,
        admin_id=actor.admin_id,
        code=payload.code,
        request=request,
    )
    set_auth_cookies(response, result.session)
    return MfaEnrollSessionVerifyOut(
        ok=True,
        recovery_codes=result.recovery_codes,
        csrf_token=result.session.csrf_token,
    )


@router.post("/mfa/verify", response_model=AuthSuccessOut)
def verify_mfa_code(
    payload: MfaCodeRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> AuthSuccessOut:
    result = auth.verify_mfa(
        db,
        ticket=payload.ticket,
        code=payload.code,
        request=request,
    )
    set_auth_cookies(response, result.session)
    return AuthSuccessOut(
        admin=result.session.admin,
        expires_in=result.session.expires_in,
        csrf_token=result.session.csrf_token,
    )


@router.post("/refresh", response_model=AuthSuccessOut)
def refresh(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> AuthSuccessOut:
    raw_refresh = request.cookies.get(PLATFORM_REFRESH_COOKIE)
    if not raw_refresh:
        clear_auth_cookies(response)
        raise AppError(401, "AUTH_REQUIRED", "Unauthorized", "Sign in again.")
    try:
        issued = auth.refresh_session(db, raw_refresh=raw_refresh, request=request)
    except AppError:
        clear_auth_cookies(response)
        raise
    set_auth_cookies(response, issued)
    return AuthSuccessOut(
        admin=issued.admin,
        expires_in=issued.expires_in,
        csrf_token=issued.csrf_token,
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> None:
    raw_refresh = request.cookies.get(PLATFORM_REFRESH_COOKIE)
    auth.logout(db, raw_refresh=raw_refresh, request=request)
    clear_auth_cookies(response)


@router.post("/step-up", response_model=StepUpOut)
def step_up(
    payload: StepUpRequest,
    request: Request,
    response: Response,
    actor: PlatformActor = Depends(get_platform_admin),
    db: Session = Depends(get_db),
) -> StepUpOut:
    result = auth.step_up(
        db,
        admin_id=actor.admin_id,
        password=payload.password,
        code=payload.code,
        request=request,
    )
    set_access_cookie(response, result.access_token, result.expires_in)
    return StepUpOut(
        expires_in=result.expires_in,
        step_up_expires_in=result.step_up_expires_in,
    )


@router.get("/me", response_model=PlatformMeOut)
def me(actor: PlatformActor = Depends(get_platform_admin)) -> PlatformMeOut:
    return PlatformMeOut(
        id=actor.admin_id,
        email=actor.email,
        display_name=actor.display_name,
        role=actor.role,
        mfa_enabled=actor.mfa_enabled,
        permissions=sorted(actor.permissions),
    )


@router.get("/sessions", response_model=PlatformSessionsOut)
def sessions(
    request: Request,
    actor: PlatformActor = Depends(get_platform_admin),
    db: Session = Depends(get_db),
) -> PlatformSessionsOut:
    rows = auth.list_sessions(
        db,
        admin_id=actor.admin_id,
        current_refresh=request.cookies.get(PLATFORM_REFRESH_COOKIE),
    )
    return PlatformSessionsOut(
        sessions=[PlatformSessionOut(**row) for row in rows]
    )


@router.post("/sessions/{family_id}/revoke", status_code=status.HTTP_204_NO_CONTENT)
def revoke_session(
    family_id: UUID,
    request: Request,
    actor: PlatformActor = Depends(get_platform_admin),
    db: Session = Depends(get_db),
) -> None:
    auth.revoke_session(
        db,
        admin_id=actor.admin_id,
        family_id=family_id,
        request=request,
    )


@router.post("/sessions/revoke-all")
def revoke_all_sessions(
    request: Request,
    actor: PlatformActor = Depends(get_platform_admin),
    db: Session = Depends(get_db),
) -> dict:
    count = auth.revoke_all_sessions(db, admin_id=actor.admin_id, request=request)
    return {"revoked_sessions": count}


# ---------------------------------------------------------------------------
# Public one-time-token flows (invitations and password resets)
# ---------------------------------------------------------------------------


def _consume_token(
    db: Session, token: str, purposes: tuple[str, ...]
) -> PlatformOneTimeToken:
    row = db.scalar(
        select(PlatformOneTimeToken).where(
            PlatformOneTimeToken.token_hash == hash_token(token),
            PlatformOneTimeToken.purpose.in_(purposes),
            PlatformOneTimeToken.used_at.is_(None),
            PlatformOneTimeToken.expires_at > datetime.now(UTC),
        )
    )
    if row is None:
        # Never reveal whether the token existed, expired, or was used.
        raise AppError(404, "INVITATION_NOT_FOUND", "Not found", "This link is no longer valid.")
    return row


@router.get("/invitations/{token}")
def invitation_details(token: str, db: Session = Depends(get_db)) -> dict:
    row = _consume_token(db, token, ("OWNER_INVITE", "STAFF_INVITE", "ADMIN_INVITE"))
    tenant_name = None
    if row.restaurant_id:
        tenant = platform_directory.get_tenant(db, row.restaurant_id)
        tenant_name = tenant["name"] if tenant else None
    return {
        "email": row.email,
        "purpose": row.purpose,
        "tenant_name": tenant_name,
        "expires_at": row.expires_at,
    }


@router.post("/invitations/{token}/accept")
def accept_invitation(
    token: str,
    payload: InviteAcceptRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> dict:
    row = _consume_token(db, token, ("OWNER_INVITE", "STAFF_INVITE", "ADMIN_INVITE"))
    valid, errors = validate_password_policy(payload.password)
    if not valid:
        raise AppError(422, "PASSWORD_POLICY", "Invalid input", "; ".join(errors))

    password_hash = hash_password(payload.password)
    now = datetime.now(UTC)
    if row.purpose in ("OWNER_INVITE", "STAFF_INVITE"):
        if row.restaurant_id is None:
            raise AppError(404, "INVITATION_NOT_FOUND", "Not found", "This link is no longer valid.")
        platform_directory.accept_owner_invitation(
            db,
            email=row.email,
            restaurant_id=row.restaurant_id,
            display_name=payload.display_name,
            password_hash=password_hash,
        )
        action = (
            "OWNER_INVITE_ACCEPTED"
            if row.purpose == "OWNER_INVITE"
            else "STAFF_INVITE_ACCEPTED"
        )
    else:
        admin = db.get(PlatformAdmin, row.platform_admin_id) if row.platform_admin_id else None
        if admin is None:
            raise AppError(404, "INVITATION_NOT_FOUND", "Not found", "This link is no longer valid.")
        admin.password_hash = password_hash
        admin.status = "ACTIVE"
        admin.password_changed_at = now
        admin.token_version += 1
        db.execute(
            update(PlatformRefreshToken)
            .where(
                PlatformRefreshToken.admin_id == admin.id,
                PlatformRefreshToken.revoked_at.is_(None),
            )
            .values(revoked_at=now, revoked_reason="PASSWORD_CHANGED")
        )
        action = "PLATFORM_USER_INVITE_ACCEPTED"

    row.used_at = now
    write_platform_audit(
        db,
        action=action,
        entity_type="platform_one_time_token",
        entity_id=str(row.id),
        actor_email=row.email,
        restaurant_id=row.restaurant_id,
        reason="invitation accepted",
        request=request,
    )
    db.commit()
    return {"ok": True}


@router.post("/password-reset/{token}/accept")
def accept_password_reset(
    token: str,
    payload: InviteAcceptRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> dict:
    row = _consume_token(db, token, ("ADMIN_PASSWORD_RESET",))
    valid, errors = validate_password_policy(payload.password)
    if not valid:
        raise AppError(422, "PASSWORD_POLICY", "Invalid input", "; ".join(errors))
    admin = db.get(PlatformAdmin, row.platform_admin_id) if row.platform_admin_id else None
    if admin is None:
        raise AppError(404, "INVITATION_NOT_FOUND", "Not found", "This link is no longer valid.")
    now = datetime.now(UTC)
    admin.password_hash = hash_password(payload.password)
    admin.password_changed_at = now
    admin.token_version += 1
    db.execute(
        update(PlatformRefreshToken)
        .where(
            PlatformRefreshToken.admin_id == admin.id,
            PlatformRefreshToken.revoked_at.is_(None),
        )
        .values(revoked_at=now, revoked_reason="PASSWORD_CHANGED")
    )
    row.used_at = now
    write_platform_audit(
        db,
        action="PLATFORM_USER_PASSWORD_RESET_ACCEPTED",
        entity_type="platform_admin",
        entity_id=str(admin.id),
        actor_email=admin.email,
        reason="password reset accepted",
        request=request,
    )
    db.commit()
    return {"ok": True}
