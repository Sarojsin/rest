from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class LoyaltyAccount(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "loyalty_accounts"

    __table_args__ = (
        UniqueConstraint("restaurant_id", "membership_id", name="uq_loyalty_accounts_restaurant_membership"),
    )

    restaurant_id: Mapped[UUID] = mapped_column(
        ForeignKey("restaurants.id"), nullable=False
    )
    membership_id: Mapped[UUID] = mapped_column(
        ForeignKey("restaurant_memberships.id"), nullable=False
    )
    points_balance: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_earned: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_redeemed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    lifetime_spend_minor: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    tier: Mapped[str] = mapped_column(
        String(32), nullable=False, default="STANDARD"
    )  # STANDARD, SILVER, GOLD, PLATINUM
    last_earned_at: Mapped[datetime | None] = mapped_column(nullable=True)
    last_redeemed_at: Mapped[datetime | None] = mapped_column(nullable=True)

    restaurant: Mapped["Restaurant"] = relationship(back_populates="loyalty_accounts")


class LoyaltyTransaction(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "loyalty_transactions"

    membership_id: Mapped[UUID] = mapped_column(
        ForeignKey("restaurant_memberships.id"), nullable=False
    )
    type: Mapped[str] = mapped_column(
        String(16), nullable=False
    )  # EARN, REDEEM
    points: Mapped[int] = mapped_column(Integer, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    reference_id: Mapped[UUID] = mapped_column(
        ForeignKey("orders.id"), nullable=True
    )  # Reference to order_id
    created_at: Mapped[datetime] = mapped_column(nullable=False)


class Coupon(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "coupons"

    __table_args__ = (
        UniqueConstraint("restaurant_id", "code", name="uq_coupons_restaurant_code"),
    )

    restaurant_id: Mapped[UUID] = mapped_column(
        ForeignKey("restaurants.id"), nullable=False
    )
    code: Mapped[str] = mapped_column(String(32), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    discount_type: Mapped[str] = mapped_column(
        String(16), nullable=False
    )  # PERCENT, FIXED
    discount_value: Mapped[int] = mapped_column(Integer, nullable=False)
    minimum_spend_minor: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    maximum_redeem_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    current_redeem_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    valid_from: Mapped[datetime] = mapped_column(nullable=False)
    valid_until: Mapped[datetime | None] = mapped_column(nullable=True)
    usage_limit_per_customer: Mapped[int | None] = mapped_column(Integer, nullable=True)


class CouponRedemption(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "coupon_redemptions"

    coupon_id: Mapped[UUID] = mapped_column(
        ForeignKey("coupons.id"), nullable=False
    )
    membership_id: Mapped[UUID] = mapped_column(
        ForeignKey("restaurant_memberships.id"), nullable=False
    )
    order_id: Mapped[UUID] = mapped_column(
        ForeignKey("orders.id"), nullable=False
    )
    discount_amount_minor: Mapped[int] = mapped_column(Integer, nullable=False)
    redeemed_at: Mapped[datetime] = mapped_column(nullable=False)