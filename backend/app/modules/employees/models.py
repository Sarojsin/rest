from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Employee(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "employees"

    __table_args__ = (
        UniqueConstraint("restaurant_id", "email", name="uq_employees_restaurant_email"),
        UniqueConstraint("restaurant_id", "phone", name="uq_employees_restaurant_phone"),
    )

    restaurant_id: Mapped[UUID] = mapped_column(
        ForeignKey("restaurants.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(120), nullable=False, unique=True)
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    role: Mapped[str] = mapped_column(String(32), nullable=False, default="EMPLOYEE")
    hire_date: Mapped[datetime] = mapped_column(nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    branch_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("branches.id"), nullable=True
    )
    user_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("restaurant_memberships.id"), nullable=True
    )

    restaurant: Mapped["Restaurant"] = relationship(back_populates="employees")
    branch: Mapped["Branch"] = relationship(back_populates="employees")
    shifts: Mapped[list["Shift"]] = relationship(back_populates="employee")


class Shift(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "shifts"

    __table_args__ = (
        UniqueConstraint("employee_id", "date", name="uq_shifts_employee_date"),
    )

    employee_id: Mapped[UUID] = mapped_column(ForeignKey("employees.id"), nullable=False)
    branch_id: Mapped[UUID] = mapped_column(ForeignKey("branches.id"), nullable=False)
    date: Mapped[str] = mapped_column(nullable=False)  # YYYY-MM-DD format
    start_time: Mapped[str] = mapped_column(nullable=False)  # HH:MM format
    end_time: Mapped[str] = mapped_column(nullable=False)  # HH:MM format
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="SCHEDULED"
    )  # SCHEDULED, IN_PROGRESS, COMPLETED, NO_SHOW
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    employee: Mapped["Employee"] = relationship(back_populates="shifts")
    branch: Mapped["Branch"] = relationship(back_populates="shifts")