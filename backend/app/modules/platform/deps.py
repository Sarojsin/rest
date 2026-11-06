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
from app.modules.platform.services.entitlements import (
    check_feature_enabled,
    check_limit_available,
    consume_limit,
    get_effective_entitlements,
)
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


# ---------------------------------------------------------------------------
# Tenant entitlement enforcement dependencies (Plan 02)
# ---------------------------------------------------------------------------


def require_tenant_feature(feature_key: str) -> Callable[..., PlatformActor]:
    """Dependency that requires a feature to be enabled for the target tenant.

    The target tenant is identified by the ``tenant_id`` query parameter or
    path parameter named ``tenant_id`` or ``restaurant_id``.
    """

    def dependency(
        actor: PlatformActor = Depends(get_platform_admin),
        db: Session = Depends(get_db),
        tenant_id: UUID | None = None,
        restaurant_id: UUID | None = None,
    ) -> PlatformActor:
        target_id = tenant_id or restaurant_id
        if target_id is None:
            raise AppError(
                422,
                "MISSING_TENANT_ID",
                "Invalid input",
                "tenant_id or restaurant_id is required.",
            )
        if not check_feature_enabled(
            db, restaurant_id=target_id, feature_key=feature_key
        ):
            raise AppError(
                403,
                "FEATURE_NOT_ENABLED",
                "Forbidden",
                f"Feature {feature_key} is not enabled for this tenant.",
                extra={"feature_key": feature_key, "tenant_id": str(target_id)},
            )
        return actor

    return dependency


def require_tenant_limit(
    limit_key: str, increment: int = 1
) -> Callable[..., PlatformActor]:
    """Dependency that requires a limit to be available for the target tenant.

    Checks current + increment <= plan limit. Does NOT consume the limit;
    use consume_tenant_limit if you also need to record the usage.
    """

    def dependency(
        actor: PlatformActor = Depends(get_platform_admin),
        db: Session = Depends(get_db),
        tenant_id: UUID | None = None,
        restaurant_id: UUID | None = None,
    ) -> PlatformActor:
        target_id = tenant_id or restaurant_id
        if target_id is None:
            raise AppError(
                422,
                "MISSING_TENANT_ID",
                "Invalid input",
                "tenant_id or restaurant_id is required.",
            )
        if not check_limit_available(
            db, restaurant_id=target_id, limit_key=limit_key, increment=increment
        ):
            raise AppError(
                409,
                "SEAT_LIMIT_REACHED",
                "Conflict",
                f"Limit {limit_key} has been reached for this tenant.",
                extra={"limit_key": limit_key, "tenant_id": str(target_id)},
            )
        return actor

    return dependency


def consume_tenant_limit(
    limit_key: str, increment: int = 1
) -> Callable[..., PlatformActor]:
    """Dependency that atomically consumes a limit for the target tenant.

    Increments the usage counter and verifies it stays within the plan limit.
    Records a usage event. This is the dependency to use when creating a new
    staff member, branch, table, etc.
    """

    def dependency(
        actor: PlatformActor = Depends(get_platform_admin),
        db: Session = Depends(get_db),
        tenant_id: UUID | None = None,
        restaurant_id: UUID | None = None,
    ) -> PlatformActor:
        target_id = tenant_id or restaurant_id
        if target_id is None:
            raise AppError(
                422,
                "MISSING_TENANT_ID",
                "Invalid input",
                "tenant_id or restaurant_id is required.",
            )
        if not consume_limit(
            db,
            restaurant_id=target_id,
            limit_key=limit_key,
            increment=increment,
            actor_admin_id=actor.admin_id,
            reason=f"consume via {limit_key} endpoint",
        ):
            raise AppError(
                409,
                "SEAT_LIMIT_REACHED",
                "Conflict",
                f"Limit {limit_key} has been reached for this tenant.",
                extra={"limit_key": limit_key, "tenant_id": str(target_id)},
            )
        return actor

    return dependency


def get_tenant_entitlements(
    db: Session = Depends(get_db),
    tenant_id: UUID | None = None,
    restaurant_id: UUID | None = None,
) -> dict | None:
    """Dependency that returns the effective entitlements for a tenant.

    Returns None if no active subscription.
    """
    target_id = tenant_id or restaurant_id
    if target_id is None:
        raise AppError(
            422,
            "MISSING_TENANT_ID",
            "Invalid input",
            "tenant_id or restaurant_id is required.",
        )
    return get_effective_entitlements(db, restaurant_id=target_id)
