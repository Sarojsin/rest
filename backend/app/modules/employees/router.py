from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import Actor, require_permission
from app.db.session import get_db
from app.modules.employees.models import Employee, Shift
from app.modules.employees.schemas import (
    EmployeeIn,
    EmployeeOut,
    EmployeeUpdateIn,
    ShiftIn,
    ShiftOut,
)
from app.shared.errors import AppError

router = APIRouter(tags=["employees"])


def _employee(db: Session, actor: Actor, employee_id: UUID) -> Employee:
    employee = db.get(Employee, employee_id)
    if employee is None or employee.restaurant_id != actor.restaurant_id:
        raise AppError(
            404, "EMPLOYEE_NOT_FOUND", "Not found", "Employee was not found."
        )
    return employee


# ── Shifts (declared before /{employee_id} so "shifts" is not captured) ────

@router.get("/shifts", response_model=list[ShiftOut])
def list_shifts(
    branch_id: UUID | None = Query(default=None),
    actor: Actor = Depends(require_permission("shifts.read")),
    db: Session = Depends(get_db),
) -> list[ShiftOut]:
    stmt = select(Shift).where(Shift.restaurant_id == actor.restaurant_id)
    if branch_id:
        stmt = stmt.where(Shift.branch_id == branch_id)
    shifts = db.scalars(stmt.order_by(Shift.date, Shift.start_time)).all()
    return [ShiftOut.model_validate(s) for s in shifts]


@router.post("/shifts", response_model=ShiftOut, status_code=201)
def create_shift(
    payload: ShiftIn,
    actor: Actor = Depends(require_permission("shifts.create")),
    db: Session = Depends(get_db),
) -> ShiftOut:
    employee = _employee(db, actor, payload.employee_id)
    if employee.branch_id is not None and employee.branch_id != payload.branch_id:
        raise AppError(
            422, "BRANCH_MISMATCH", "Branch mismatch",
            "The shift branch does not match the employee's branch.",
        )

    duplicate = db.scalar(
        select(Shift).where(
            Shift.employee_id == payload.employee_id, Shift.date == payload.date
        )
    )
    if duplicate:
        raise AppError(
            409, "SHIFT_EXISTS", "Shift exists",
            "This employee already has a shift on that date.",
        )

    shift = Shift(
        restaurant_id=actor.restaurant_id,
        employee_id=payload.employee_id,
        branch_id=payload.branch_id,
        date=payload.date,
        start_time=payload.start_time,
        end_time=payload.end_time,
        status=payload.status,
        notes=payload.notes,
    )
    db.add(shift)
    db.commit()
    db.refresh(shift)
    return ShiftOut.model_validate(shift)


# ── Employees ───────────────────────────────────────────────────────────────

@router.get("", response_model=list[EmployeeOut])
def list_employees(
    branch_id: UUID | None = Query(default=None),
    active_only: bool = Query(default=False),
    actor: Actor = Depends(require_permission("employees.read")),
    db: Session = Depends(get_db),
) -> list[EmployeeOut]:
    stmt = select(Employee).where(Employee.restaurant_id == actor.restaurant_id)
    if branch_id:
        stmt = stmt.where(Employee.branch_id == branch_id)
    if active_only:
        stmt = stmt.where(Employee.is_active.is_(True))
    employees = db.scalars(stmt.order_by(Employee.name)).all()
    return [EmployeeOut.model_validate(e) for e in employees]


@router.post("", response_model=EmployeeOut, status_code=201)
def create_employee(
    payload: EmployeeIn,
    actor: Actor = Depends(require_permission("employees.create")),
    db: Session = Depends(get_db),
) -> EmployeeOut:
    duplicate = db.scalar(
        select(Employee).where(
            Employee.restaurant_id == actor.restaurant_id,
            Employee.email == payload.email,
        )
    )
    if duplicate:
        raise AppError(
            409, "EMPLOYEE_EMAIL_EXISTS", "Email in use",
            "An employee with this email already exists.",
        )

    employee = Employee(
        restaurant_id=actor.restaurant_id,
        name=payload.name,
        email=payload.email,
        phone=payload.phone,
        role=payload.role,
        hire_date=payload.hire_date,
        is_active=payload.is_active,
        branch_id=payload.branch_id,
    )
    db.add(employee)
    db.commit()
    db.refresh(employee)
    return EmployeeOut.model_validate(employee)


@router.get("/{employee_id}", response_model=EmployeeOut)
def get_employee(
    employee_id: UUID,
    actor: Actor = Depends(require_permission("employees.read")),
    db: Session = Depends(get_db),
) -> EmployeeOut:
    return EmployeeOut.model_validate(_employee(db, actor, employee_id))


@router.patch("/{employee_id}", response_model=EmployeeOut)
def update_employee(
    employee_id: UUID,
    payload: EmployeeUpdateIn,
    actor: Actor = Depends(require_permission("employees.update")),
    db: Session = Depends(get_db),
) -> EmployeeOut:
    employee = _employee(db, actor, employee_id)
    data = payload.model_dump(exclude_unset=True)
    for field, value in data.items():
        setattr(employee, field, value)
    db.commit()
    db.refresh(employee)
    return EmployeeOut.model_validate(employee)
