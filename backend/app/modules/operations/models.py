from datetime import datetime
from uuid import UUID

from sqlalchemy import ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class RestaurantTable(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "restaurant_tables"
    __table_args__ = (
        UniqueConstraint("restaurant_id", "table_code", name="uq_tables_restaurant_code"),
    )

    restaurant_id: Mapped[UUID] = mapped_column(ForeignKey("restaurants.id"), nullable=False)
    table_code: Mapped[str] = mapped_column(String(32), nullable=False)
    display_name: Mapped[str] = mapped_column(String(80), nullable=False)
    seating_capacity: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ACTIVE")
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    qr_codes: Mapped[list["TableQrCode"]] = relationship(back_populates="table")
    sessions: Mapped[list["DiningSession"]] = relationship(back_populates="table")


class TableQrCode(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "table_qr_codes"

    restaurant_id: Mapped[UUID] = mapped_column(ForeignKey("restaurants.id"), nullable=False)
    table_id: Mapped[UUID] = mapped_column(ForeignKey("restaurant_tables.id"), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    token_preview: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ACTIVE")
    revoked_at: Mapped[datetime | None] = mapped_column(nullable=True)

    table: Mapped[RestaurantTable] = relationship(back_populates="qr_codes")


class DiningSession(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "dining_sessions"

    restaurant_id: Mapped[UUID] = mapped_column(ForeignKey("restaurants.id"), nullable=False)
    table_id: Mapped[UUID] = mapped_column(ForeignKey("restaurant_tables.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="OPEN")
    opened_at: Mapped[datetime] = mapped_column(nullable=False)
    opened_by_membership_id: Mapped[UUID | None] = mapped_column(nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(nullable=True)
    closed_by_membership_id: Mapped[UUID | None] = mapped_column(nullable=True)
    version: Mapped[int] = mapped_column(Integer, default=1)

    table: Mapped[RestaurantTable] = relationship(back_populates="sessions")
    orders: Mapped[list["Order"]] = relationship(back_populates="dining_session")  # noqa: F821
    bills: Mapped[list["Bill"]] = relationship(back_populates="dining_session")  # noqa: F821


class Order(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "orders"
    __table_args__ = (
        UniqueConstraint(
            "restaurant_id", "idempotency_key", name="uq_orders_restaurant_idempotency_key"
        ),
    )

    restaurant_id: Mapped[UUID] = mapped_column(ForeignKey("restaurants.id"), nullable=False)
    table_id: Mapped[UUID] = mapped_column(ForeignKey("restaurant_tables.id"), nullable=False)
    dining_session_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("dining_sessions.id"), nullable=True
    )
    source: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    created_by_membership_id: Mapped[UUID | None] = mapped_column(nullable=True)
    idempotency_key: Mapped[str] = mapped_column(String(80), nullable=False)
    customer_status_token_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    customer_note: Mapped[str] = mapped_column(String(280), default="")
    submitted_at: Mapped[datetime] = mapped_column(nullable=False)
    accepted_at: Mapped[datetime | None] = mapped_column(nullable=True)
    rejected_at: Mapped[datetime | None] = mapped_column(nullable=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(nullable=True)
    decision_by_membership_id: Mapped[UUID | None] = mapped_column(nullable=True)
    rejection_reason_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    rejection_note: Mapped[str] = mapped_column(String(280), default="")
    version: Mapped[int] = mapped_column(Integer, default=1)

    dining_session: Mapped["DiningSession"] = relationship(back_populates="orders")
    items: Mapped[list["OrderItem"]] = relationship(back_populates="order")
    kitchen_tickets: Mapped[list["KitchenTicket"]] = relationship(  # noqa: F821
        back_populates="order"
    )


class OrderItem(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "order_items"

    restaurant_id: Mapped[UUID] = mapped_column(ForeignKey("restaurants.id"), nullable=False)
    order_id: Mapped[UUID] = mapped_column(ForeignKey("orders.id"), nullable=False)
    menu_item_id: Mapped[UUID | None] = mapped_column(ForeignKey("menu_items.id"), nullable=True)
    item_name_snapshot: Mapped[str] = mapped_column(String(120), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price_minor: Mapped[int] = mapped_column(Integer, nullable=False)
    discount_minor: Mapped[int] = mapped_column(Integer, default=0)
    tax_minor: Mapped[int] = mapped_column(Integer, default=0)
    line_total_minor: Mapped[int] = mapped_column(Integer, nullable=False)
    currency_code: Mapped[str] = mapped_column(String(3), nullable=False)
    special_instructions: Mapped[str] = mapped_column(Text, default="")

    order: Mapped[Order] = relationship(back_populates="items")


class OrderRating(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "order_ratings"
    __table_args__ = (UniqueConstraint("order_id", name="uq_order_rating_order_id"),)

    restaurant_id: Mapped[UUID] = mapped_column(ForeignKey("restaurants.id"), nullable=False)
    order_id: Mapped[UUID] = mapped_column(ForeignKey("orders.id"), nullable=False)
    rating: Mapped[int] = mapped_column(Integer, nullable=False)
    comment: Mapped[str] = mapped_column(String(280), default="")
    rated_by_token_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)

    order: Mapped[Order] = relationship()
