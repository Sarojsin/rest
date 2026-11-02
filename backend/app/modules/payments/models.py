from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class PaymentMethodConfig(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Owner-configured tender option for checkout (cash or static QR)."""

    __tablename__ = "payment_methods"
    __table_args__ = (
        UniqueConstraint("restaurant_id", "label", name="uq_payment_methods_restaurant_label"),
    )

    restaurant_id: Mapped[UUID] = mapped_column(ForeignKey("restaurants.id"), nullable=False)
    label: Mapped[str] = mapped_column(String(80), nullable=False)
    kind: Mapped[str] = mapped_column(String(16), nullable=False)  # CASH | QR
    qr_image_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    qr_image_ext: Mapped[str | None] = mapped_column(String(8), nullable=True)
    account_hint: Mapped[str] = mapped_column(String(160), default="", nullable=False)
    instructions: Mapped[str] = mapped_column(String(500), default="", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    display_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class Payment(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "payments"
    __table_args__ = (
        UniqueConstraint(
            "restaurant_id", "idempotency_key", name="uq_payments_restaurant_idempotency_key"
        ),
    )

    restaurant_id: Mapped[UUID] = mapped_column(ForeignKey("restaurants.id"), nullable=False)
    bill_id: Mapped[UUID] = mapped_column(ForeignKey("bills.id"), nullable=False)
    method: Mapped[str] = mapped_column(String(80), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    amount_minor: Mapped[int] = mapped_column(Integer, nullable=False)
    currency_code: Mapped[str] = mapped_column(String(3), nullable=False)
    provider: Mapped[str | None] = mapped_column(String(64), nullable=True)
    note: Mapped[str] = mapped_column(String(120), default="", nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(80), nullable=False)
    initiated_by_membership_id: Mapped[UUID | None] = mapped_column(nullable=True)
    succeeded_at: Mapped[datetime | None] = mapped_column(nullable=True)
    failure_code: Mapped[str | None] = mapped_column(String(64), nullable=True)

    bill: Mapped["Bill"] = relationship(back_populates="payments")  # noqa: F821
