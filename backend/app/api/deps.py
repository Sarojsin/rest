from collections.abc import Callable
from uuid import UUID

import jwt
from fastapi import Depends, Header
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.security import decode_access_token
from app.db.session import get_db
from app.modules.identity.models import User
from app.modules.tenancy.middleware import tenant_context
from app.modules.tenancy.models import RestaurantMembership
from app.modules.tenancy.permissions import ROLE_PERMISSIONS
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
    if membership.user.status != "ACTIVE":
        raise AppError(403, "ACCOUNT_DISABLED", "Forbidden", "This account is not active.")
    return Actor(user=membership.user, membership=membership)


def require_permission(permission: str) -> Callable[[Actor], Actor]:
    def dependency(actor: Actor = Depends(get_actor)) -> Actor:
        actor.require(permission)
        return actor

    return dependency