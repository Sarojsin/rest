"""Platform authentication and authorization dependencies (PA-0.4).

The platform realm reads its access token from the HttpOnly
``platform_access`` cookie only. It never accepts ``Authorization`` headers,
query strings, or JS-visible storage.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import decode_platform_access_token
from app.db.session import get_db
from app.modules.platform.constants import PLATFORM_ACCESS_COOKIE
from app.modules.platform.models import PlatformAdmin
from app.modules.platform.permissions import PLATFORM_PERMISSIONS, permissions_for
from app.shared.errors import AppError


def _unauthorized(code: str = "AUTH_REQUIRED", detail: str = "Authentication is required."):
    return AppError(401, code, "Unauthorized", detail)


def _as_utc(value) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=UTC)
    return datetime.fromtimestamp(int(value), tz=UTC)


@dataclass(frozen=True)
class PlatformActor:
    admin_id: UUID
    email: str
    display_name: str
    role: str
    permissions: frozenset[str]
    token_version: int
    auth_time: datetime | None
    step_up_at: datetime | None
    mfa_enabled: bool


def get_platform_admin(
    request: Request,
    db: Session = Depends(get_db),
) -> PlatformActor:
    """Resolve the platform admin from the HttpOnly access cookie."""
    token = request.cookies.get(PLATFORM_ACCESS_COOKIE)
    if not token:
        raise _unauthorized()

    payload = decode_platform_access_token(token)

    try:
        admin_id = UUID(str(payload["sub"]))
    except (KeyError, ValueError) as exc:
        raise _unauthorized("INVALID_TOKEN") from exc

    admin = db.get(PlatformAdmin, admin_id)
    if admin is None or admin.status != "ACTIVE":
        # Same shape as an invalid token: cross-realm/disabled must not reveal
        # whether the account exists.
        raise _unauthorized("INVALID_TOKEN")
    if int(payload.get("ver", -1)) != admin.token_version:
        raise _unauthorized("TOKEN_REVOKED", "Session is no longer valid.")
    if payload.get("role") != admin.role:
        # A role change invalidates existing sessions.
        raise _unauthorized("TOKEN_REVOKED", "Session is no longer valid.")

    return PlatformActor(
        admin_id=admin.id,
        email=admin.email,
        display_name=admin.display_name,
        role=admin.role,
        permissions=permissions_for(admin.role),
        token_version=admin.token_version,
        auth_time=_as_utc(payload.get("auth_time")),
        step_up_at=_as_utc(payload.get("step_up_at")),
        mfa_enabled=admin.mfa_enabled_at is not None,
    )


def require_platform_permission(permission: str) -> Callable[..., PlatformActor]:
    """Build a dependency that requires one known platform permission."""
    if permission not in PLATFORM_PERMISSIONS:
        raise ValueError(f"Unknown platform permission: {permission}")

    def dependency(actor: PlatformActor = Depends(get_platform_admin)) -> PlatformActor:
        if permission not in actor.permissions:
            raise AppError(
                403,
                "FORBIDDEN",
                "Forbidden",
                "You do not have permission to perform this action.",
            )
        return actor

    return dependency


def require_platform_step_up(
    actor: PlatformActor = Depends(get_platform_admin),
) -> PlatformActor:
    """Require a fresh MFA assertion before a sensitive platform action."""
    window = timedelta(minutes=settings.platform_step_up_minutes)
    if actor.step_up_at is None or datetime.now(UTC) - actor.step_up_at > window:
        raise AppError(
            401,
            "STEP_UP_REQUIRED",
            "Unauthorized",
            "Re-authenticate to continue.",
            extra={"max_age_seconds": int(window.total_seconds())},
        )
    return actor
