from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.security import (
    create_access_token,
    create_refresh_token,
    is_account_locked,
    record_failed_login,
    record_successful_login,
    verify_password,
)
from app.modules.identity.models import User
from app.modules.identity.schemas import LoginResponse, MembershipOut, MeOut, MFAChallengeResponse
from app.modules.tenancy.models import Restaurant, RestaurantMembership
from app.modules.tenancy.permissions import ROLE_PERMISSIONS
from app.shared import tenant_access
from app.shared.errors import AppError


def _membership_out(membership: RestaurantMembership) -> MembershipOut:
    restaurant: Restaurant = membership.restaurant
    return MembershipOut(
        id=membership.id,
        restaurant_id=membership.restaurant_id,
        restaurant_name=restaurant.name,
        role=membership.role,
        permissions=sorted(ROLE_PERMISSIONS.get(membership.role, set())),
    )


def me_from_membership(user: User, membership: RestaurantMembership, all_memberships: list[RestaurantMembership] | None = None, active_branch_id: UUID | None = None) -> MeOut:
    memberships = all_memberships if all_memberships is not None else [membership]
    return MeOut(
        id=user.id,
        email=user.email,
        display_name=user.display_name,
        membership=_membership_out(membership),
        memberships=[_membership_out(m) for m in memberships],
        active_branch_id=active_branch_id,
    )


async def login(db: Session, email: str, password: str) -> LoginResponse | MFAChallengeResponse:
    user = db.scalar(
        select(User)
        .options(selectinload(User.memberships).selectinload(RestaurantMembership.restaurant))
        .where(User.email == email.strip().lower())
    )
    if user is not None and is_account_locked(user.id):
        raise AppError(
            429,
            "ACCOUNT_LOCKED",
            "Too many failed attempts",
            "Account temporarily locked. Try again later.",
        )
    if user is None or not verify_password(password, user.password_hash):
        if user is not None:
            record_failed_login(user.id)
        raise AppError(401, "INVALID_CREDENTIALS", "Unauthorized", "Invalid email or password.")
    if user.status != "ACTIVE":
        raise AppError(403, "ACCOUNT_DISABLED", "Forbidden", "This account is not active.")

    membership = next((m for m in user.memberships if m.status == "ACTIVE"), None)
    if membership is None:
        raise AppError(403, "NO_MEMBERSHIP", "Forbidden", "No active restaurant membership.")

    active_memberships = [m for m in user.memberships if m.status == "ACTIVE"]

    # Suspension blocks new sign-ins. The in-flight allowlist applies only to
    # staff who were already authenticated before the suspension (PA D-6).
    tenant_access.ensure_tenant_active(
        status=membership.restaurant.status,
        archived_at=membership.restaurant.archived_at,
    )

    user.last_login_at = datetime.now(UTC)
    record_successful_login(user.id)
    db.commit()

    # Check if MFA is enabled
    if user.mfa_enabled:
        # Return MFA challenge - create a short-lived MFA token
        mfa_token = create_access_token(
            user_id=user.id,
            membership_id=membership.id,
            restaurant_id=membership.restaurant_id,
            token_version=membership.token_version,
            realm="staff-mfa",  # Different realm for MFA challenge
        )
        return MFAChallengeResponse(
            mfa_token=mfa_token,
            user_id=user.id,
            membership_id=membership.id,
            restaurant_id=membership.restaurant_id,
        )

    token = create_access_token(
        user_id=user.id,
        membership_id=membership.id,
        restaurant_id=membership.restaurant_id,
        token_version=membership.token_version,
    )
    refresh_token = await create_refresh_token(
        user_id=user.id,
        membership_id=membership.id,
        restaurant_id=membership.restaurant_id,
        token_version=membership.token_version,
    )
    return LoginResponse(access_token=token, refresh_token=refresh_token, user=me_from_membership(user, membership, active_memberships))
