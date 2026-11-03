from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


# ── Employee ──────────────────────────────────────────────────────────────────

class EmployeeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    email: str
    phone: str | None
    role: str
    hire_date: datetime
    is_active: bool
    branch_id: UUID | None
    user_id: UUID | None
    created_at: datetime
    updated_at: datetime


class EmployeeIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=120)
    email: str = Field(min_length=1, max_length=120)
    phone: str | None = None
    role: str = "EMPLOYEE"
    hire_date: datetime
    is_active: bool = True
    branch_id: UUID | None = None


# ── Shift ───────────────────────────────────────────────────────────────────

class ShiftOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    employee_id: UUID
    branch_id: UUID
    date: str
    start_time: str
    end_time: str
    status: str
    notes: str | None
    created_at: datetime


class ShiftIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    employee_id: UUID
    branch_id: UUID
    date: str
    start_time: str
    end_time: str
    status: str = "SCHEDULED"
    notes: str | None = None