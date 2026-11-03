from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.shared.schemas import ORMModel

# ── Branch ──────────────────────────────────────────────────────────────────

class BranchOut(ORMModel):
    name: str
    code: str | None
    address: str | None
    phone: str | None
    timezone: str
    currency_code: str
    is_active: bool
    opening_hours: str | None
    settings_json: dict
    owner_membership_id: UUID | None
    restaurant_name: str | None = None
    manager_name: str | None = None


class BranchIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=120)
    code: str | None = Field(default=None, max_length=32)
    address: str | None = None
    phone: str | None = None
    timezone: str = "UTC"
    currency_code: str = "USD"
    is_active: bool = True
    opening_hours: str | None = None


# ── Branch Table ────────────────────────────────────────────────────────────

class BranchTableOut(ORMModel):
    table_code: str
    display_name: str
    seating_capacity: int | None
    status: str
    qr_code_active: bool


class BranchTableIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    table_code: str = Field(min_length=1, max_length=32)
    display_name: str = Field(min_length=1, max_length=80)
    seating_capacity: int | None = None
    status: str | None = "ACTIVE"
    qr_code_active: bool = True


# ── Branch Manager ────────────────────────────────────────────────────────

class BranchManagerOut(ORMModel):
    role: str
    is_active: bool
    assigned_at: datetime


class BranchManagerIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    membership_id: UUID
    role: str = "MANAGER"


# ── Branch Sales Report ───────────────────────────────────────────────────

class BranchSalesReportOut(ORMModel):
    id: UUID
    report_date: datetime
    total_sales_minor: int
    total_sales_display: str
    total_orders: int
    total_orders_completed: int
    total_orders_pending: int
    total_revenue_minor: int
    total_revenue_display: str
    average_ticket_minor: int
    payment_breakdown: dict
    created_at: datetime


class BranchSalesReportIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    branch_id: UUID
    report_date: datetime
    total_sales_minor: int = 0
    total_orders: int = 0
    total_orders_completed: int = 0
    total_orders_pending: int = 0
    total_revenue_minor: int = 0
    payment_breakdown: dict | None = None


# ── Branch Dashboard Summary ──────────────────────────────────────────────

class BranchDashboardSummaryOut(ORMModel):
    id: UUID
    summary_date: datetime
    total_revenue_minor: int
    total_revenue_display: str
    total_orders: int
    average_rating: float | None
    low_stock_count: int
    active_tables: int


class BranchDashboardSummaryIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    branch_id: UUID
    summary_date: datetime
    total_revenue_minor: int = 0
    total_orders: int = 0
    average_rating: float | None = None
    low_stock_count: int = 0
    active_tables: int = 0


# ── Owner Dashboard ───────────────────────────────────────────────────────

class OwnerDashboardSummaryOut(BaseModel):
    restaurant_name: str
    total_revenue_minor: int
    total_revenue_display: str
    total_orders: int
    branch_count: int
    active_branch_count: int
    branches: list[BranchDashboardSummaryOut]


class OwnerDashboardSummaryIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    restaurant_id: UUID