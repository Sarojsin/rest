"""Staff force-logout service stub (PA-0.10).

The caller owns the transaction and the audit row. PA-1.2.3 calls these from
the platform tenant routes; PA-0 only fixes the token-version mechanism.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import update
from sqlalchemy.orm import Session

from app.modules.tenancy.models import RestaurantMembership


def force_logout_membership(db: Session, membership: RestaurantMembership) -> int:
    """Invalidate every outstanding token for one membership."""
    membership.token_version += 1
    return membership.token_version


def force_logout_restaurant(db: Session, restaurant_id: UUID) -> int:
    """Invalidate every outstanding staff token for a tenant.

    Returns the number of memberships affected.
    """
    result = db.execute(
        update(RestaurantMembership)
        .where(RestaurantMembership.restaurant_id == restaurant_id)
        .values(token_version=RestaurantMembership.token_version + 1)
    )
    return int(result.rowcount or 0)
