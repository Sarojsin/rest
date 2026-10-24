from datetime import datetime
from uuid import UUID

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class KitchenTicket(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "kitchen_tickets"

    restaurant_id: Mapped[UUID] = mapped_column(ForeignKey("restaurants.id"), nullable=False)
    order_id: Mapped[UUID] = mapped_column(ForeignKey("orders.id"), nullable=False)
    ticket_number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="NEW")
    started_at: Mapped[datetime | None] = mapped_column(nullable=True)
    ready_at: Mapped[datetime | None] = mapped_column(nullable=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(nullable=True)
    last_updated_by_membership_id: Mapped[UUID | None] = mapped_column(nullable=True)

    order: Mapped["Order"] = relationship(back_populates="kitchen_tickets")  # noqa: F821
    items: Mapped[list["KitchenTicketItem"]] = relationship(back_populates="ticket")


class KitchenTicketItem(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "kitchen_ticket_items"

    restaurant_id: Mapped[UUID] = mapped_column(ForeignKey("restaurants.id"), nullable=False)
    ticket_id: Mapped[UUID] = mapped_column(ForeignKey("kitchen_tickets.id"), nullable=False)
    order_item_id: Mapped[UUID] = mapped_column(ForeignKey("order_items.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="NEW")
    quantity_snapshot: Mapped[int] = mapped_column(Integer, nullable=False)
    instructions_snapshot: Mapped[str] = mapped_column(Text, default="")
    started_at: Mapped[datetime | None] = mapped_column(nullable=True)
    ready_at: Mapped[datetime | None] = mapped_column(nullable=True)
    served_at: Mapped[datetime | None] = mapped_column(nullable=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(nullable=True)
    updated_by_membership_id: Mapped[UUID | None] = mapped_column(nullable=True)

    ticket: Mapped[KitchenTicket] = relationship(back_populates="items")
