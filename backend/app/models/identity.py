from datetime import datetime
from uuid import UUID

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Restaurant(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "restaurants"

    name: Mapped[str] = mapped_column(String(160), nullable=False)
    slug: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ACTIVE")
    timezone: Mapped[str] = mapped_column(String(64), nullable=False, default="UTC")
    currency_code: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")

    settings: Mapped["RestaurantSettings"] = relationship(back_populates="restaurant")
    memberships: Mapped[list["RestaurantMembership"]] = relationship(back_populates="restaurant")


class RestaurantSettings(TimestampMixin, Base):
    __tablename__ = "restaurant_settings"

    restaurant_id: Mapped[UUID] = mapped_column(
        ForeignKey("restaurants.id"), primary_key=True
    )
    locale: Mapped[str] = mapped_column(String(16), default="en-US")
    business_day_start_local: Mapped[str] = mapped_column(String(8), default="05:00")
    tax_rate_bps: Mapped[int] = mapped_column(default=1000)
    receipt_header: Mapped[str] = mapped_column(String(160), default="")
    receipt_footer: Mapped[str] = mapped_column(String(160), default="Thank you")
    qr_ordering_enabled: Mapped[bool] = mapped_column(default=True)
    online_payments_enabled: Mapped[bool] = mapped_column(default=False)
    settings_version: Mapped[int] = mapped_column(default=1)

    restaurant: Mapped[Restaurant] = relationship(back_populates="settings")


class User(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str] = mapped_column(String(120), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ACTIVE")
    last_login_at: Mapped[datetime | None] = mapped_column(nullable=True)

    memberships: Mapped[list["RestaurantMembership"]] = relationship(back_populates="user")


class RestaurantMembership(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "restaurant_memberships"
    __table_args__ = (UniqueConstraint("restaurant_id", "user_id", name="uq_membership_restaurant_user"),)

    restaurant_id: Mapped[UUID] = mapped_column(ForeignKey("restaurants.id"), nullable=False)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    role: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ACTIVE")

    restaurant: Mapped[Restaurant] = relationship(back_populates="memberships")
    user: Mapped[User] = relationship(back_populates="memberships")
