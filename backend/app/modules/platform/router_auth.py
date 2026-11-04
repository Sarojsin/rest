"""Platform authentication routes (PA-0.5).

Mounted under ``/api/platform`` by the composition layer (PA-0.14). Tokens are
only ever delivered as cookies.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.modules.platform.constants import PLATFORM_REFRESH_COOKIE
from app.modules.platform.deps import PlatformActor, get_platform_admin
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
from app.modules.platform.services import auth
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
    return AuthSuccessOut(admin=issued.admin, expires_in=issued.expires_in)


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
