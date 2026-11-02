from datetime import datetime
from uuid import UUID

from sqlalchemy import ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Bill(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "bills"
    __table_args__ = (UniqueConstraint("dining_session_id", name="uq_bills_dining_session_id"),)

    restaurant_id: Mapped[UUID] = mapped_column(ForeignKey("restaurants.id"), nullable=False)
    dining_session_id: Mapped[UUID] = mapped_column(
        ForeignKey("dining_sessions.id"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="OPEN")
    currency_code: Mapped[str] = mapped_column(String(3), nullable=False)
    subtotal_minor: Mapped[int] = mapped_column(Integer, default=0)
    discount_minor: Mapped[int] = mapped_column(Integer, default=0)
    tax_minor: Mapped[int] = mapped_column(Integer, default=0)
    service_charge_minor: Mapped[int] = mapped_column(Integer, default=0)
    total_minor: Mapped[int] = mapped_column(Integer, default=0)
    paid_minor: Mapped[int] = mapped_column(Integer, default=0)
    balance_due_minor: Mapped[int] = mapped_column(Integer, default=0)
    issued_at: Mapped[datetime | None] = mapped_column(nullable=True)
    paid_at: Mapped[datetime | None] = mapped_column(nullable=True)
    voided_at: Mapped[datetime | None] = mapped_column(nullable=True)
    version: Mapped[int] = mapped_column(Integer, default=1)

    dining_session: Mapped["DiningSession"] = relationship(  # noqa: F821
        back_populates="bills"
    )
    items: Mapped[list["BillItem"]] = relationship(back_populates="bill")
    payments: Mapped[list["Payment"]] = relationship(  # noqa: F821
        back_populates="bill"
    )


class BillItem(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "bill_items"

    restaurant_id: Mapped[UUID] = mapped_column(ForeignKey("restaurants.id"), nullable=False)
    bill_id: Mapped[UUID] = mapped_column(ForeignKey("bills.id"), nullable=False)
    order_item_id: Mapped[UUID | None] = mapped_column(ForeignKey("order_items.id"), nullable=True)
    description_snapshot: Mapped[str] = mapped_column(String(160), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price_minor: Mapped[int] = mapped_column(Integer, nullable=False)
    discount_minor: Mapped[int] = mapped_column(Integer, default=0)
    tax_minor: Mapped[int] = mapped_column(Integer, default=0)
    line_total_minor: Mapped[int] = mapped_column(Integer, nullable=False)

    bill: Mapped[Bill] = relationship(back_populates="items")
