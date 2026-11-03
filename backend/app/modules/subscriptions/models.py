from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class SubscriptionPlan(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "subscription_plans"

    __table_args__ = (
        UniqueConstraint("restaurant_id", "name", name="uq_subscription_plans_restaurant_name"),
    )

    restaurant_id: Mapped[UUID] = mapped_column(
        ForeignKey("restaurants.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    price_minor: Mapped[int] = mapped_column(Integer, nullable=False)
    billing_interval: Mapped[str] = mapped_column(
        String(32), nullable=False
    )  # MONTHLY, QUARTERLY, ANNUAL
    trial_days: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    features: Mapped[str] = mapped_column(
        Text, nullable=False
    )  # JSON string of features
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class Subscription(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "subscriptions"

    __table_args__ = (
        UniqueConstraint("restaurant_id", "membership_id", name="uq_subscriptions_restaurant_membership"),
    )

    restaurant_id: Mapped[UUID] = mapped_column(
        ForeignKey("restaurants.id"), nullable=False
    )
    membership_id: Mapped[UUID] = mapped_column(
        ForeignKey("restaurant_memberships.id"), nullable=False
    )
    plan_id: Mapped[UUID] = mapped_column(
        ForeignKey("subscription_plans.id"), nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(32), nullable=False
    )  # TRIAL, ACTIVE, PAST_DUE, CANCELLED
    started_at: Mapped[datetime] = mapped_column(nullable=False)
    billing_cycle_end: Mapped[datetime] = mapped_column(nullable=False)
    cancel_at_period_end: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    canceled_at: Mapped[datetime | None] = mapped_column(nullable=True)

    restaurant: Mapped["Restaurant"] = relationship(back_populates="subscriptions")
    plan: Mapped["SubscriptionPlan"] = relationship(back_populates="subscriptions")


class SubscriptionBillingInfo(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "subscription_billing_info"

    subscription_id: Mapped[UUID] = mapped_column(
        ForeignKey("subscriptions.id"), nullable=False
    )
    amount_minor: Mapped[int] = mapped_column(Integer, nullable=False)
    currency_code: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")
    billing_date: Mapped[datetime] = mapped_column(nullable=False)
    status: Mapped[str] = mapped_column(
        String(32), nullable=False
    )  # SCHEDULED, PAID, FAILED