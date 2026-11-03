from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import Actor, require_permission
from app.db.session import get_db
from app.modules.employees.models import Employee, Shift
from app.modules.employees.schemas import EmployeeOut, EmployeeIn, ShiftOut, ShiftIn
from app.shared.errors import AppError
from app.shared.idempotency import idempotency_key

router = APIRouter(tags=["employees"])


@router.get("/", response_model=list[EmployeeOut])
def list_employees(
    actor: Actor = Depends(require_permission("employees.read")),
    db: Session = Depends(get_db),
) -> list[EmployeeOut]:
    employees = db.scalars(
        select(Employee).where(Employee.restaurant_id == actor.restaurant_id)
    ).all()
    return [EmployeeOut.model_validate(e) for e in employees]


@router.post("/", response_model=EmployeeOut)
def create_employee(
    payload: EmployeeIn,
    actor: Actor = Depends(require_permission("employees.create")),
    db: Session = Depends(get_db),
) -> EmployeeOut:
    # Verify branch exists if provided
    if payload.branch_id:
        branch = db.get(Employee.__table__.foreign_keys[0].target_reference, payload.branch_id)
        # Actually let me just check branches table
        from app.modules.branches.models import Branch
        branch = db.get(Branch, payload.branch_id)
        if not branch:
            raise AppError(404, "BRANCH_NOT_FOUND", "Not found", "Branch was not found.")

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
    db.flush()
    db.commit()
    return EmployeeOut.model_validate(employee)


@router.get("/{employee_id}", response_model=EmployeeOut)
def get_employee(
    employee_id: UUID,
    actor: Actor = Depends(require_permission("employees.read")),
    db: Session = Depends(get_db),
) -> EmployeeOut | None:
    employee = db.get(Employee, employee_id)
    if employee is None or employee.restaurant_id != actor.restaurant_id:
        return None
    return EmployeeOut.model_validate(employee)


# ── Shifts ──────────────────────────────────────────────────────────────────

@router.get("/shifts", response_model=list[ShiftOut])
def list_shifts(
    actor: Actor = Depends(require_permission("shifts.read")),
    db: Session = Depends(get_db),
) -> list[ShiftOut]:
    shifts = db.scalars(
        select(Shift).where(Shift.branch_id == actor.restaurant_id)
    ).all()
    return [ShiftOut.model_validate(s) for s in shifts]


@router.post("/shifts", response_model=ShiftOut)
def create_shift(
    payload: ShiftIn,
    actor: Actor = Depends(require_permission("shifts.create")),
    db: Session = Depends(get_db),
) -> ShiftOut:
    # Verify employee exists
    employee = db.get(Employee, payload.employee_id)
    if not employee or employee.restaurant_id != actor.restaurant_id:
        raise AppError(404, "EMPLOYEE_NOT_FOUND", "Not found", "Employee was not found.")

    shift = Shift(
        employee_id=payload.employee_id,
        branch_id=payload.branch_id,
        date=payload.date,
        start_time=payload.start_time,
        end_time=payload.end_time,
        status=payload.status,
        notes=payload.notes,
    )
    db.add(shift)
    db.flush()
    db.commit()
    return ShiftOut.model_validate(shift)