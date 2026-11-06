from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Restaurant(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "restaurants"

    name: Mapped[str] = mapped_column(String(160), nullable=False)
    slug: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    # Access state: ACTIVE / SUSPENDED / CANCELLED. Trial is a subscription
    # state, never duplicated here (PA D-5).
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ACTIVE")
    timezone: Mapped[str] = mapped_column(String(64), nullable=False, default="UTC")
    currency_code: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")

    # Lifecycle columns (PA-0.11 / plan 04 Â§2.1). Soft delete only: no row is
    # ever destroyed by the platform in PA-1.
    archived_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    suspended_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    suspended_reason: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    contact_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    contact_phone: Mapped[str | None] = mapped_column(String(40), nullable=True)
    legal_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    settings: Mapped["RestaurantSettings"] = relationship(back_populates="restaurant")
    memberships: Mapped[list["RestaurantMembership"]] = relationship(back_populates="restaurant")
    branches: Mapped[list["Branch"]] = relationship(back_populates="restaurant")  # noqa: F821
    employees: Mapped[list["Employee"]] = relationship(back_populates="restaurant")  # noqa: F821
    loyalty_accounts: Mapped[list["LoyaltyAccount"]] = relationship(  # noqa: F821
        back_populates="restaurant"
    )
    reviews: Mapped[list["Review"]] = relationship(back_populates="restaurant")  # noqa: F821
    subscriptions: Mapped[list["Subscription"]] = relationship(  # noqa: F821
        back_populates="restaurant"
    )


class RestaurantSettings(TimestampMixin, Base):
    __tablename__ = "restaurant_settings"

    restaurant_id: Mapped[UUID] = mapped_column(ForeignKey("restaurants.id"), primary_key=True)
    locale: Mapped[str] = mapped_column(String(16), default="en-US")
    business_day_start_local: Mapped[str] = mapped_column(String(8), default="05:00")
    tax_rate_bps: Mapped[int] = mapped_column(default=1000)
    receipt_header: Mapped[str] = mapped_column(String(160), default="")
    receipt_footer: Mapped[str] = mapped_column(String(160), default="Thank you")
    qr_ordering_enabled: Mapped[bool] = mapped_column(default=True)
    online_payments_enabled: Mapped[bool] = mapped_column(default=False)
    settings_version: Mapped[int] = mapped_column(default=1)
    # Plan 07 M7 (D5): locked-at-launch subdomain label under the platform apex,
    # plus an optional custom domain and per-tenant branding for the QR surface.
    customer_subdomain: Mapped[str | None] = mapped_column(
        String(63), unique=True, nullable=True
    )
    custom_domain: Mapped[str | None] = mapped_column(String(255), nullable=True)
    brand_logo_url: Mapped[str] = mapped_column(String(500), default="")
    brand_accent_hex: Mapped[str] = mapped_column(String(9), default="")
    # Onboarding stage tracking (Plan 10): registered → owner_invited →
    # owner_activated → profile_complete → tables_configured → menu_configured
    # → staff_invited → payments_configured → operational
    onboarding_stage: Mapped[str] = mapped_column(
        String(32), nullable=False, default="registered", server_default="registered"
    )
    onboarding_completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    restaurant: Mapped[Restaurant] = relationship(back_populates="settings")


class RestaurantMembership(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "restaurant_memberships"
    __table_args__ = (
        UniqueConstraint("restaurant_id", "user_id", name="uq_membership_restaurant_user"),
    )

    restaurant_id: Mapped[UUID] = mapped_column(ForeignKey("restaurants.id"), nullable=False)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    role: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ACTIVE")
    # Bumped to invalidate every outstanding staff token for this membership
    # (PA-0.10 / force logout). Tokens without a version are treated as 0.
    token_version: Mapped[int] = mapped_column(nullable=False, default=0)

    restaurant: Mapped[Restaurant] = relationship(back_populates="memberships")
    user: Mapped["User"] = relationship(back_populates="memberships")  # noqa: F821
    branch_scopes: Mapped[list["RestaurantMembershipBranch"]] = relationship(
        back_populates="membership",
        cascade="all, delete-orphan",
    )


class RestaurantMembershipBranch(UUIDPrimaryKeyMixin, Base):
    """Links a staff membership to one or more branches.

    Owner memberships are implicitly organization-wide and do not need a row
    here. A manager/waiter/kitchen/cashier can be scoped to specific branches;
    multiple rows grant access to multiple branches.
    """

    __tablename__ = "restaurant_membership_branch"

    __table_args__ = (
        UniqueConstraint(
            "membership_id",
            "branch_id",
            name="uq_membership_branch_membership_branch",
        ),
    )

    membership_id: Mapped[UUID] = mapped_column(
        ForeignKey("restaurant_memberships.id", ondelete="CASCADE"), nullable=False
    )
    branch_id: Mapped[UUID] = mapped_column(
        ForeignKey("branches.id", ondelete="CASCADE"), nullable=False
    )

    membership: Mapped["RestaurantMembership"] = relationship(
        back_populates="branch_scopes"
    )
    branch: Mapped["Branch"] = relationship()