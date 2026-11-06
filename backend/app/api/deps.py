from collections.abc import Callable
from uuid import UUID

import jwt
from fastapi import Depends, Header
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.security import decode_access_token
from app.db.session import get_db
from app.modules.identity.models import User
from app.modules.platform.services.entitlements import (
    consume_limit,
    get_effective_entitlements,
    release_limit,
)
from app.modules.tenancy.middleware import tenant_context
from app.modules.tenancy.models import RestaurantMembership, RestaurantMembershipBranch
from app.modules.tenancy.permissions import ROLE_PERMISSIONS
from app.modules.tenancy.services.tenant_lifecycle import ensure_tenant_active
from app.shared.errors import AppError


def get_tenant_id() -> str | None:
    """Return the current request's tenant_id, if any.

    Intended to be used as a FastAPI dependency via `Depends(get_tenant_id)`
    after `set_tenant_context(request)` has been called (e.g. in middleware).
    """
    return getattr(tenant_context, "tenant_id", None)


def set_tenant_context(request) -> None:
    """Extract tenant_id from x-tenant-id header and store it in module state.

    Call once per request (typically in FastAPI middleware or per-route).
    """
    tid = request.headers.get("x-tenant-id")
    if tid:
        tenant_context.tenant_id = tid
    else:
        tenant_context.tenant_id = None


def clear_tenant_context() -> None:
    """Reset tenant state at request boundary."""
    tenant_context.tenant_id = None


class Actor:
    def __init__(self, user: User, membership: RestaurantMembership) -> None:
        self.user = user
        self.membership = membership

    @property
    def restaurant_id(self) -> UUID:
        return self.membership.restaurant_id

    @property
    def restaurant(self):
        return self.membership.restaurant

    @property
    def permissions(self) -> set[str]:
        return ROLE_PERMISSIONS.get(self.membership.role, set())

    def require(self, permission: str) -> None:
        if permission not in self.permissions:
            raise AppError(
                403, "FORBIDDEN", "Forbidden", "You do not have permission for this action."
            )


def get_actor(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
    tenant_id: str | None = Depends(get_tenant_id),
) -> Actor:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise AppError(401, "UNAUTHORIZED", "Unauthorized", "Authentication is required.")
    token = authorization.split(" ", 1)[1].strip()
    try:
        payload = decode_access_token(token)
    except jwt.ExpiredSignatureError as exc:
        raise AppError(
            401, "TOKEN_EXPIRED", "Unauthorized", "Session expired. Sign in again."
        ) from exc
    except jwt.InvalidTokenError as exc:
        raise AppError(401, "INVALID_TOKEN", "Unauthorized", "Authentication is required.") from exc

    membership = db.scalar(
        select(RestaurantMembership)
        .options(
            selectinload(RestaurantMembership.user),
            selectinload(RestaurantMembership.restaurant),
        )
        .where(RestaurantMembership.id == UUID(payload["mid"]))
    )
    if (
        membership is None
        or membership.status != "ACTIVE"
        or str(membership.user_id) != payload.get("sub")
        or str(membership.restaurant_id) != payload.get("rid")
        # Tenant switch: the membership's restaurant must match the request tenant_id
        or (tenant_id is not None and str(membership.restaurant_id) != tenant_id)
    ):
        raise AppError(401, "UNAUTHORIZED", "Unauthorized", "Authentication is required.")
    # Force logout: a bumped membership version invalidates older tokens.
    if int(payload.get("ver", 0)) != membership.token_version:
        raise AppError(
            401,
            "TOKEN_REVOKED",
            "Unauthorized",
            "Session is no longer valid. Sign in again.",
        )
    if membership.user.status != "ACTIVE":
        raise AppError(403, "ACCOUNT_DISABLED", "Forbidden", "This account is not active.")
    return Actor(user=membership.user, membership=membership)


def require_permission(permission: str) -> Callable[[Actor], Actor]:
    def dependency(actor: Actor = Depends(get_actor)) -> Actor:
        actor.require(permission)
        return actor

    return dependency


def require_active_tenant(actor: Actor = Depends(get_actor)) -> Actor:
    """Block new work for a suspended/cancelled/archived tenant (PA D-6)."""
    ensure_tenant_active(actor.membership.restaurant)
    return actor


def require_permission_on_active_tenant(permission: str) -> Callable[[Actor], Actor]:
    """Permission check plus active-tenant check for write routes."""

    def dependency(
        actor: Actor = Depends(require_permission(permission)),
    ) -> Actor:
        ensure_tenant_active(actor.membership.restaurant)
        return actor

    return dependency


# ---------------------------------------------------------------------------
# Tenant subscription entitlement gates (PA-02)
# ---------------------------------------------------------------------------
#
# These helpers live in the API composition layer so the tenancy module never
# imports the platform module (the only sanctioned cross-module edge is
# ``platform -> tenancy : services.platform_directory``).
#
# Tenants without an active subscription are deliberately ungated: local dev,
# demo datasets and pre-sales tenants keep working while a subscription is
# provisioned. Once a subscription exists it is authoritative â€” including
# TRIALING/PAST_DUE/GRACE statuses, so enforcement is consistent through the
# dunning lifecycle.


def _tenant_entitlements(db: Session, actor: Actor) -> dict | None:
    return get_effective_entitlements(db, restaurant_id=actor.restaurant_id)


def require_tenant_feature(feature_key: str) -> Callable[..., Actor]:
    """Require a plan feature to be enabled for the actor's tenant."""

    def dependency(
        actor: Actor = Depends(require_active_tenant),
        db: Session = Depends(get_db),
    ) -> Actor:
        entitlements = _tenant_entitlements(db, actor)
        if entitlements is not None and not entitlements["features"].get(feature_key, False):
            raise AppError(
                403,
                "FEATURE_NOT_ENABLED",
                "Forbidden",
                "This feature is not included in your current plan.",
                extra={"feature_key": feature_key},
            )
        return actor

    return dependency


def consume_tenant_limit(limit_key: str, increment: int = 1) -> Callable[..., Actor]:
    """Atomically consume one seat/resource slot for the actor's tenant.

    No-op when the tenant has no active subscription, so demo tenants remain
    usable. When a subscription exists the counter is locked (``FOR UPDATE``)
    and the request fails with 409 instead of racing past the plan limit.
    """

    def dependency(
        actor: Actor = Depends(require_active_tenant),
        db: Session = Depends(get_db),
    ) -> Actor:
        entitlements = _tenant_entitlements(db, actor)
        if entitlements is None:
            return actor
        if not consume_limit(
            db,
            restaurant_id=actor.restaurant_id,
            limit_key=limit_key,
            increment=increment,
            reason="tenant endpoint consumption",
        ):
            raise AppError(
                409,
                "SEAT_LIMIT_REACHED",
                "Conflict",
                "Your plan's limit for this resource has been reached.",
                extra={"limit_key": limit_key},
            )
        return actor

    return dependency


def release_tenant_limit(limit_key: str, decrement: int = 1) -> Callable[..., Actor]:
    """Release seats when a tenant-owned resource is removed.

    Floors the counter at zero so removing a resource created before usage
    tracking (or after a manual reconciliation) can never fail the request.
    """

    def dependency(
        actor: Actor = Depends(require_active_tenant),
        db: Session = Depends(get_db),
    ) -> Actor:
        entitlements = _tenant_entitlements(db, actor)
        if entitlements is not None:
            release_limit(
                db,
                restaurant_id=actor.restaurant_id,
                limit_key=limit_key,
                decrement=decrement,
                reason="tenant endpoint release",
            )
        return actor

    return dependency


def require_permission_and_feature(
    permission: str, feature_key: str
) -> Callable[..., Actor]:
    """Permission check plus a plan-feature gate in one dependency."""

    def dependency(
        actor: Actor = Depends(require_permission(permission)),
        db: Session = Depends(get_db),
    ) -> Actor:
        entitlements = _tenant_entitlements(db, actor)
        if entitlements is not None and not entitlements["features"].get(feature_key, False):
            raise AppError(
                403,
                "FEATURE_NOT_ENABLED",
                "Forbidden",
                "This feature is not included in your current plan.",
                extra={"feature_key": feature_key},
            )
        return actor

    return dependency


def require_permission_and_consume_limit(
    permission: str, limit_key: str, increment: int = 1
) -> Callable[..., Actor]:
    """Permission check plus atomic plan-limit consumption in one dependency."""

    def dependency(
        actor: Actor = Depends(require_permission(permission)),
        db: Session = Depends(get_db),
    ) -> Actor:
        entitlements = _tenant_entitlements(db, actor)
        if entitlements is None:
            return actor
        if not consume_limit(
            db,
            restaurant_id=actor.restaurant_id,
            limit_key=limit_key,
            increment=increment,
            reason="tenant endpoint consumption",
        ):
            raise AppError(
                409,
                "SEAT_LIMIT_REACHED",
                "Conflict",
                "Your plan's limit for this resource has been reached.",
                extra={"limit_key": limit_key},
            )
        return actor

    return dependency

def require_branch_access(branch_id: UUID) -> Callable[..., Actor]:
    """Require that the actor has access to the given branch.

    Owner memberships bypass branch scoping (organization-wide access).
    Other roles must have a `restaurant_membership_branch` row linking
    their membership to the branch.
    """

    def dependency(
        actor: Actor = Depends(require_permission_on_active_tenant("staff.manage")),
        db: Session = Depends(get_db),
    ) -> Actor:
        if actor.membership.role == "owner":
            return actor
        has_access = db.scalar(
            select(RestaurantMembershipBranch).where(
                RestaurantMembershipBranch.membership_id == actor.membership.id,
                RestaurantMembershipBranch.branch_id == branch_id,
            )
        )
        if has_access is None:
            raise AppError(
                403,
                "BRANCH_ACCESS_DENIED",
                "Forbidden",
                "You do not have access to this branch.",
            )
        return actor

    return dependency