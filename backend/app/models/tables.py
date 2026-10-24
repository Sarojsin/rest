from datetime import datetime
from uuid import UUID

from sqlalchemy import ForeignKey, Integer, String, UniqueConstraint
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
