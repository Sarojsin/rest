from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Employee(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "employees"

    __table_args__ = (
        UniqueConstraint("restaurant_id", "email", name="uq_employees_restaurant_email"),
    )

    restaurant_id: Mapped[UUID] = mapped_column(
        ForeignKey("restaurants.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(120), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    role: Mapped[str] = mapped_column(String(32), nullable=False, default="EMPLOYEE")
    hire_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    branch_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("branches.id"), nullable=True, index=True
    )
    user_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("restaurant_memberships.id"), nullable=True
    )

    restaurant: Mapped["Restaurant"] = relationship(back_populates="employees")  # noqa: F821
    branch: Mapped["Branch | None"] = relationship(back_populates="employees")  # noqa: F821
    shifts: Mapped[list["Shift"]] = relationship(
        back_populates="employee", cascade="all, delete-orphan"
    )


class Shift(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "shifts"

    __table_args__ = (
        UniqueConstraint("employee_id", "date", name="uq_shifts_employee_date"),
    )

    restaurant_id: Mapped[UUID] = mapped_column(
        ForeignKey("restaurants.id"), nullable=False, index=True
    )
    employee_id: Mapped[UUID] = mapped_column(
        ForeignKey("employees.id"), nullable=False, index=True
    )
    branch_id: Mapped[UUID] = mapped_column(
        ForeignKey("branches.id"), nullable=False, index=True
    )
    date: Mapped[str] = mapped_column(String(10), nullable=False)  # YYYY-MM-DD
    start_time: Mapped[str] = mapped_column(String(5), nullable=False)  # HH:MM
    end_time: Mapped[str] = mapped_column(String(5), nullable=False)  # HH:MM
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="SCHEDULED"
    )  # SCHEDULED, IN_PROGRESS, COMPLETED, NO_SHOW
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    employee: Mapped["Employee"] = relationship(back_populates="shifts")
    branch: Mapped["Branch"] = relationship(back_populates="shifts")  # noqa: F821
