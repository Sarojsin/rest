from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.domain.enums import ServiceCallKind


class ServiceCall(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "service_calls"

    restaurant_id: Mapped[UUID] = mapped_column(ForeignKey("restaurants.id"), nullable=False)
    kind: Mapped[str] = mapped_column(
        String(16), nullable=False, default=ServiceCallKind.GUEST.value
    )
    table_id: Mapped[UUID] = mapped_column(ForeignKey("restaurant_tables.id"), nullable=False)
    kitchen_ticket_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("kitchen_tickets.id"), nullable=True
    )
    detail: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="REQUESTED")
    created_by_membership_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("restaurant_memberships.id"), nullable=True
    )
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    acknowledged_by_membership_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("restaurant_memberships.id"), nullable=True
    )

    table: Mapped["RestaurantTable"] = relationship()  # noqa: F821
    kitchen_ticket: Mapped["KitchenTicket | None"] = relationship()  # noqa: F821
