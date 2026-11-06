"""Staff membership administration (PA-07).

Lives in the API composition layer because it combines the tenancy identity
tables with the platform usage/entitlement service. Keeping it here preserves
the frozen cross-module coupling inventory (the only sanctioned edge is
``platform -> tenancy : services.platform_directory``).
"""

from __future__ import annotations

import secrets
from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import Actor, require_permission_on_active_tenant
from app.core.security import hash_password, hash_token, new_token
from app.db.session import get_db
from app.modules.audit.services import record_audit
from app.modules.branches.models import Branch
from app.modules.identity.models import User
from app.modules.platform.models import PlatformOneTimeToken
from app.modules.platform.services.entitlements import (
    consume_limit,
    get_effective_entitlements,
    get_usage_status,
    release_limit,
)
from app.modules.tenancy.models import RestaurantMembership, RestaurantMembershipBranch
from app.modules.tenancy.schemas_memberships import (
    MembershipInviteOut,
    MembershipInviteRequest,
    MembershipListOut,
    MembershipOut,
)
from app.shared.errors import AppError

router = APIRouter(tags=["memberships"])

# Tenant role -> plan limit key (plural, matching platform_plan_limits).
ROLE_LIMIT_KEYS = {
    "manager": "managers",
    "waiter": "waiters",
    "kitchen": "kitchen",
    "cashier": "cashier",
}

_INVITE_TTL = timedelta(hours=72)
_ACTIVE_MEMBERSHIP_STATUSES = ("INVITED", "ACTIVE", "SUSPENDED")


def _membership_out(
    membership: RestaurantMembership, user: User, branch_ids: list[UUID] | None = None
) -> MembershipOut:
    return MembershipOut(
        id=membership.id,
        user_id=user.id,
        email=user.email,
        display_name=user.display_name,
        role=membership.role,
        status=membership.status,
        created_at=membership.created_at,
        branch_ids=branch_ids or [],
    )


def _seat_summary(db: Session, restaurant_id: UUID) -> dict | None:
    usage = get_usage_status(db, restaurant_id=restaurant_id)
    if usage is None:
        return None
    return usage["usage"]


@router.get("/restaurant_memberships", response_model=MembershipListOut)
def list_memberships(
    actor: Actor = Depends(
        require_permission_on_active_tenant("staff.manage")
    ),
    db: Session = Depends(get_db),
) -> MembershipListOut:
    """List staff memberships and the tenant's remaining plan seats."""
    rows = (
        db.scalars(
            select(RestaurantMembership)
            .options(selectinload(RestaurantMembership.user))
            .where(
                RestaurantMembership.restaurant_id == actor.restaurant_id,
                RestaurantMembership.status != "REMOVED",
            )
            .order_by(RestaurantMembership.role, RestaurantMembership.created_at)
        )
        .all()
    )
    # Load branch scopes for each membership
    membership_ids = [row.id for row in rows]
    branch_scope_map: dict[UUID, list[UUID]] = {mid: [] for mid in membership_ids}
    if membership_ids:
        scope_rows = db.scalars(
            select(RestaurantMembershipBranch).where(
                RestaurantMembershipBranch.membership_id.in_(membership_ids)
            )
        ).all()
        for sr in scope_rows:
            branch_scope_map.setdefault(sr.membership_id, []).append(sr.branch_id)

    return MembershipListOut(
        items=[
            _membership_out(row, row.user, branch_scope_map.get(row.id))
            for row in rows
        ],
        seats=_seat_summary(db, actor.restaurant_id),
    )


@router.post(
    "/restaurant_memberships/invite",
    response_model=MembershipInviteOut,
    status_code=status.HTTP_201_CREATED,
)
def invite_membership(
    payload: MembershipInviteRequest,
    actor: Actor = Depends(
        require_permission_on_active_tenant("staff.manage")
    ),
    db: Session = Depends(get_db),
) -> MembershipInviteOut:
    """Invite a staff member, consuming one role seat atomically.

    Owners cannot be invited through this endpoint: a tenant has exactly one
    primary owner, created when the tenant is provisioned. The raw invitation
    token is returned once; only its hash is stored.
    """
    email = str(payload.email).strip().lower()
    role = payload.role
    limit_key = ROLE_LIMIT_KEYS[role]
    branch_id = payload.branch_id

    # If a branch_id is provided, validate it belongs to this restaurant.
    if branch_id is not None:
        branch = db.scalar(
            select(Branch).where(
                Branch.id == branch_id,
                Branch.restaurant_id == actor.restaurant_id,
            )
        )
        if branch is None:
            raise AppError(
                400,
                "BRANCH_NOT_FOUND",
                "Not found",
                "Branch not found or does not belong to this restaurant.",
            )

    # Consume the seat first. If any later step fails the whole request
    # transaction is rolled back when the session closes, so the counter cannot
    # leak. ``consume_limit`` takes SELECT ... FOR UPDATE on the usage row.
    entitlements = get_effective_entitlements(db, restaurant_id=actor.restaurant_id)
    if entitlements is not None:
        if not consume_limit(
            db,
            restaurant_id=actor.restaurant_id,
            limit_key=limit_key,
            reason=f"staff invite: {role}",
        ):
            raise AppError(
                409,
                "SEAT_LIMIT_REACHED",
                "Conflict",
                f"Your plan's {role} seat limit has been reached.",
                extra={"limit_key": limit_key},
            )

    user = db.scalar(select(User).where(func.lower(User.email) == email))
    membership: RestaurantMembership | None = None
    if user is not None:
        membership = db.scalar(
            select(RestaurantMembership).where(
                RestaurantMembership.restaurant_id == actor.restaurant_id,
                RestaurantMembership.user_id == user.id,
            )
        )
        if membership is not None and membership.status != "REMOVED":
            raise AppError(
                409,
                "MEMBERSHIP_EXISTS",
                "Conflict",
                "That person is already on your team.",
            )
        if membership is None:
            # A global identity that belongs to another restaurant must not be
            # silently attached here; that would be an account-takeover path.
            raise AppError(
                409,
                "EMAIL_IN_USE",
                "Conflict",
                "An account with that email already exists.",
            )
        membership.role = role
        membership.status = "INVITED"
        membership.token_version += 1
    else:
        display_name = payload.name.strip() or email.split("@")[0]
        user = User(
            email=email,
            # Unusable random password until the invitation is accepted.
            password_hash=hash_password(secrets.token_urlsafe(48)),
            display_name=display_name,
            status="INVITED",
        )
        db.add(user)
        db.flush()
        membership = RestaurantMembership(
            restaurant_id=actor.restaurant_id,
            user_id=user.id,
            role=role,
            status="INVITED",
            token_version=0,
        )
        db.add(membership)
        db.flush()

    # Create branch scope link if a branch was specified.
    branch_ids: list[UUID] = []
    if branch_id is not None:
        db.add(
            RestaurantMembershipBranch(
                membership_id=membership.id,
                branch_id=branch_id,
            )
        )
        branch_ids.append(branch_id)

    raw_token = new_token(32)
    expires_at = datetime.now(UTC) + _INVITE_TTL
    db.add(
        PlatformOneTimeToken(
            token_hash=hash_token(raw_token),
            purpose="STAFF_INVITE",
            email=email,
            restaurant_id=actor.restaurant_id,
            expires_at=expires_at,
            created_by_admin_id=None,
        )
    )

    record_audit(
        db,
        restaurant_id=actor.restaurant_id,
        action="memberships.invite",
        entity_type="restaurant_membership",
        entity_id=str(membership.id),
        actor_user_id=actor.user.id,
        actor_membership_id=actor.membership.id,
        detail=f"email={email};role={role};branch_id={branch_id}",
    )
    db.commit()
    db.refresh(membership)

    return MembershipInviteOut(
        **_membership_out(membership, user, branch_ids).model_dump(),
        invitation_token=raw_token,
        invitation_expires_at=expires_at,
    )


@router.delete(
    "/restaurant_memberships/{membership_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def revoke_membership(
    membership_id: UUID,
    actor: Actor = Depends(
        require_permission_on_active_tenant("staff.manage")
    ),
    db: Session = Depends(get_db),
) -> Response:
    """Remove a staff member and release their seat.

    Soft-deletes the membership (``REMOVED``) so historical audit rows and
    order attribution keep their foreign keys. Token versions are bumped so
    any outstanding access token is rejected immediately.
    """
    membership = db.scalar(
        select(RestaurantMembership).where(
            RestaurantMembership.id == membership_id,
            RestaurantMembership.restaurant_id == actor.restaurant_id,
        )
    )
    if membership is None or membership.status == "REMOVED":
        raise AppError(
            404, "MEMBERSHIP_NOT_FOUND", "Not found", "Team member was not found."
        )

    if membership.role == "owner":
        if actor.membership.role != "owner":
            raise AppError(
                403,
                "FORBIDDEN",
                "Forbidden",
                "Only an owner can remove another owner.",
            )
        if membership.id == actor.membership.id:
            raise AppError(
                409,
                "CANNOT_REMOVE_SELF",
                "Conflict",
                "You cannot remove your own owner membership.",
            )
        owner_count = db.scalar(
            select(func.count())
            .select_from(RestaurantMembership)
            .where(
                RestaurantMembership.restaurant_id == actor.restaurant_id,
                RestaurantMembership.role == "owner",
                RestaurantMembership.status != "REMOVED",
            )
        )
        if int(owner_count or 0) <= 1:
            raise AppError(
                409,
                "LAST_OWNER",
                "Conflict",
                "A restaurant must keep at least one owner.",
            )

    entitlement = get_effective_entitlements(db, restaurant_id=actor.restaurant_id)
    if entitlement is not None:
        release_limit(
            db,
            restaurant_id=actor.restaurant_id,
            limit_key=ROLE_LIMIT_KEYS.get(membership.role, "owners"),
            reason=f"staff removed: {membership.role}",
        )

    membership.status = "REMOVED"
    membership.token_version += 1
    record_audit(
        db,
        restaurant_id=actor.restaurant_id,
        action="memberships.revoke",
        entity_type="restaurant_membership",
        entity_id=str(membership.id),
        actor_user_id=actor.user.id,
        actor_membership_id=actor.membership.id,
        detail=f"role={membership.role}",
    )
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
