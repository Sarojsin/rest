from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.errors import AppError
from app.core.security import create_access_token, verify_password
from app.domain.permissions import ROLE_PERMISSIONS
from app.models.identity import Restaurant, RestaurantMembership, User
from app.schemas.auth import LoginResponse, MeOut, MembershipOut


def _membership_out(membership: RestaurantMembership) -> MembershipOut:
    restaurant: Restaurant = membership.restaurant
    return MembershipOut(
        id=membership.id,
        restaurant_id=membership.restaurant_id,
        restaurant_name=restaurant.name,
        role=membership.role,
        permissions=sorted(ROLE_PERMISSIONS.get(membership.role, set())),
    )


def me_from_membership(user: User, membership: RestaurantMembership) -> MeOut:
    return MeOut(
        id=user.id,
        email=user.email,
        display_name=user.display_name,
        membership=_membership_out(membership),
    )


def login(db: Session, email: str, password: str) -> LoginResponse:
    user = db.scalar(
        select(User)
        .options(selectinload(User.memberships).selectinload(RestaurantMembership.restaurant))
        .where(User.email == email.strip().lower())
    )
    if user is None or not verify_password(password, user.password_hash):
        raise AppError(401, "INVALID_CREDENTIALS", "Unauthorized", "Invalid email or password.")
    if user.status != "ACTIVE":
        raise AppError(403, "ACCOUNT_DISABLED", "Forbidden", "This account is not active.")

    membership = next((m for m in user.memberships if m.status == "ACTIVE"), None)
    if membership is None:
        raise AppError(403, "NO_MEMBERSHIP", "Forbidden", "No active restaurant membership.")

    user.last_login_at = datetime.now(UTC)
    db.commit()
    token = create_access_token(
        user_id=user.id, membership_id=membership.id, restaurant_id=membership.restaurant_id
    )
    return LoginResponse(access_token=token, user=me_from_membership(user, membership))
