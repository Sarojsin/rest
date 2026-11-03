from datetime import datetime
from uuid import UUID

from sqlalchemy import ForeignKey, Integer, String, Text, UniqueConstraint, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Branch(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "branches"

    __table_args__ = (
        UniqueConstraint("restaurant_id", "name", name="uq_branches_restaurant_name"),
        UniqueConstraint("restaurant_id", "code", name="uq_branches_restaurant_code"),
    )

    restaurant_id: Mapped[UUID] = mapped_column(
        ForeignKey("restaurants.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    code: Mapped[str | None] = mapped_column(String(32), nullable=True, unique=True)
    address: Mapped[str] = mapped_column(String(200), nullable=True)
    phone: Mapped[str] = mapped_column(String(32), nullable=True)
    timezone: Mapped[str] = mapped_column(String(50), nullable=False, default="UTC")
    currency_code: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    opening_hours: Mapped[str | None] = mapped_column(String(100), nullable=True)
    settings_json: Mapped[str] = mapped_column(String, nullable=True, default="{}")
    owner_membership_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("restaurant_memberships.id"), nullable=True
    )

    restaurant: Mapped["Restaurant"] = relationship(back_populates="branches")
    manager: Mapped["RestaurantMembership"] = relationship(
        back_populates="managed_branch",
        foreign_keys=[owner_membership_id],
    )
    tables: Mapped[list["BranchTable"]] = relationship(back_populates="branch")
    orders: Mapped[list["Order"]] = relationship(back_populates="branch")
    sales_reports: Mapped[list["BranchSalesReport"]] = relationship(back_populates="branch")


class BranchTable(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "branch_tables"

    __table_args__ = (
        UniqueConstraint("branch_id", "table_code", name="uq_branch_tables_branch_code"),
    )

    branch_id: Mapped[UUID] = mapped_column(ForeignKey("branches.id"), nullable=False)
    table_code: Mapped[str] = mapped_column(String(32), nullable=False)
    display_name: Mapped[str] = mapped_column(String(80), nullable=False)
    seating_capacity: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ACTIVE")
    qr_code_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    branch: Mapped["Branch"] = relationship(back_populates="tables")
    orders: Mapped[list["Order"]] = relationship(back_populates="table")


class BranchManager(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "branch_managers"

    __table_args__ = (
        UniqueConstraint("branch_id", "membership_id", name="uq_branch_managers_branch_membership"),
    )

    branch_id: Mapped[UUID] = mapped_column(ForeignKey("branches.id"), nullable=False)
    membership_id: Mapped[UUID] = mapped_column(ForeignKey("restaurant_memberships.id"), nullable=False)
    role: Mapped[str] = mapped_column(String(32), nullable=False, default="MANAGER")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    assigned_at: Mapped[datetime] = mapped_column(nullable=False)

    branch: Mapped["Branch"] = relationship(back_populates="manager_assignments")
    membership: Mapped["RestaurantMembership"] = relationship(
        back_populates="managed_branch",
        foreign_keys=[membership_id],
    )


class BranchSalesReport(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "branch_sales_reports"

    branch_id: Mapped[UUID] = mapped_column(ForeignKey("branches.id"), nullable=False)
    report_date: Mapped[datetime] = mapped_column(nullable=False)
    total_sales_minor: Mapped[int] = mapped_column(Integer, default=0)
    total_orders: Mapped[int] = mapped_column(Integer, default=0)
    total_orders_completed: Mapped[int] = mapped_column(Integer, default=0)
    total_orders_pending: Mapped[int] = mapped_column(Integer, default=0)
    total_revenue_minor: Mapped[int] = mapped_column(Integer, default=0)
    payment_breakdown_json: Mapped[str] = mapped_column(String, nullable=True, default="{}")
    average_ticket_minor: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(nullable=False)

    branch: Mapped["Branch"] = relationship(back_populates="sales_reports")


class BranchDashboardSummary(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "branch_dashboard_summaries"

    branch_id: Mapped[UUID] = mapped_column(ForeignKey("branches.id"), nullable=False)
    summary_date: Mapped[datetime] = mapped_column(nullable=False)
    total_revenue_minor: Mapped[int] = mapped_column(Integer, default=0)
    total_orders: Mapped[int] = mapped_column(Integer, default=0)
    average_rating: Mapped[float] = mapped_column(nullable=True)
    low_stock_count: Mapped[int] = mapped_column(Integer, default=0)
    active_tables: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(nullable=False)

    branch: Mapped["Branch"] = relationship(back_populates="dashboard_summaries")