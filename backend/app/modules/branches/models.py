from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Branch(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "branches"

    __table_args__ = (
        UniqueConstraint("restaurant_id", "name", name="uq_branches_restaurant_name"),
        UniqueConstraint("restaurant_id", "code", name="uq_branches_restaurant_code"),
    )

    restaurant_id: Mapped[UUID] = mapped_column(
        ForeignKey("restaurants.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    code: Mapped[str | None] = mapped_column(String(32), nullable=True)
    address: Mapped[str | None] = mapped_column(String(200), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    timezone: Mapped[str] = mapped_column(String(50), nullable=False, default="UTC")
    currency_code: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    opening_hours: Mapped[str | None] = mapped_column(String(100), nullable=True)
    settings_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    owner_membership_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("restaurant_memberships.id"), nullable=True
    )

    restaurant: Mapped["Restaurant"] = relationship(back_populates="branches")  # noqa: F821
    manager: Mapped["RestaurantMembership | None"] = relationship(  # noqa: F821
        foreign_keys=[owner_membership_id],
    )
    tables: Mapped[list["BranchTable"]] = relationship(
        back_populates="branch", cascade="all, delete-orphan"
    )
    employees: Mapped[list["Employee"]] = relationship(back_populates="branch")  # noqa: F821
    shifts: Mapped[list["Shift"]] = relationship(back_populates="branch")  # noqa: F821
    manager_assignments: Mapped[list["BranchManager"]] = relationship(
        back_populates="branch", cascade="all, delete-orphan"
    )
    sales_reports: Mapped[list["BranchSalesReport"]] = relationship(
        back_populates="branch", cascade="all, delete-orphan"
    )
    dashboard_summaries: Mapped[list["BranchDashboardSummary"]] = relationship(
        back_populates="branch", cascade="all, delete-orphan"
    )


class BranchTable(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "branch_tables"

    __table_args__ = (
        UniqueConstraint("branch_id", "table_code", name="uq_branch_tables_branch_code"),
    )

    branch_id: Mapped[UUID] = mapped_column(
        ForeignKey("branches.id"), nullable=False, index=True
    )
    table_code: Mapped[str] = mapped_column(String(32), nullable=False)
    display_name: Mapped[str] = mapped_column(String(80), nullable=False)
    seating_capacity: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ACTIVE")
    qr_code_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    branch: Mapped["Branch"] = relationship(back_populates="tables")


class BranchManager(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "branch_managers"

    __table_args__ = (
        UniqueConstraint(
            "branch_id", "membership_id", name="uq_branch_managers_branch_membership"
        ),
    )

    branch_id: Mapped[UUID] = mapped_column(
        ForeignKey("branches.id"), nullable=False, index=True
    )
    membership_id: Mapped[UUID] = mapped_column(
        ForeignKey("restaurant_memberships.id"), nullable=False, index=True
    )
    role: Mapped[str] = mapped_column(String(32), nullable=False, default="MANAGER")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    assigned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    branch: Mapped["Branch"] = relationship(back_populates="manager_assignments")
    membership: Mapped["RestaurantMembership"] = relationship(  # noqa: F821
        foreign_keys=[membership_id]
    )


class BranchSalesReport(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "branch_sales_reports"

    branch_id: Mapped[UUID] = mapped_column(
        ForeignKey("branches.id"), nullable=False, index=True
    )
    report_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    total_sales_minor: Mapped[int] = mapped_column(Integer, default=0)
    total_orders: Mapped[int] = mapped_column(Integer, default=0)
    total_orders_completed: Mapped[int] = mapped_column(Integer, default=0)
    total_orders_pending: Mapped[int] = mapped_column(Integer, default=0)
    total_revenue_minor: Mapped[int] = mapped_column(Integer, default=0)
    payment_breakdown: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    average_ticket_minor: Mapped[int] = mapped_column(Integer, default=0)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    branch: Mapped["Branch"] = relationship(back_populates="sales_reports")

    @property
    def total_sales_display(self) -> str:
        return f"{self.total_sales_minor / 100:.2f}"

    @property
    def total_revenue_display(self) -> str:
        return f"{self.total_revenue_minor / 100:.2f}"


class BranchDashboardSummary(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "branch_dashboard_summaries"

    branch_id: Mapped[UUID] = mapped_column(
        ForeignKey("branches.id"), nullable=False, index=True
    )
    summary_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    total_revenue_minor: Mapped[int] = mapped_column(Integer, default=0)
    total_orders: Mapped[int] = mapped_column(Integer, default=0)
    average_rating: Mapped[float | None] = mapped_column(nullable=True)
    low_stock_count: Mapped[int] = mapped_column(Integer, default=0)
    active_tables: Mapped[int] = mapped_column(Integer, default=0)

    branch: Mapped["Branch"] = relationship(back_populates="dashboard_summaries")

    @property
    def total_revenue_display(self) -> str:
        return f"{self.total_revenue_minor / 100:.2f}"
