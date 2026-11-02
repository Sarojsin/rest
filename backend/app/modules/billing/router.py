from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import Actor, require_permission
from app.api.idempotency import idempotency_key
from app.db.session import get_db
from app.modules.billing.schemas import BillOut
from app.modules.billing.services import billing as billing_service
from app.modules.payments.schemas import RecordPaymentRequest
from app.shared.errors import AppError

router = APIRouter(tags=["bills"])


@router.get("/sessions/{session_id}/bill", response_model=BillOut)
def get_bill(
    session_id: UUID,
    actor: Actor = Depends(require_permission("bills.issue")),
    db: Session = Depends(get_db),
) -> BillOut:
    bill = billing_service.get_session_bill(db, actor.restaurant_id, session_id)
    if bill is None:
        raise AppError(
            404, "BILL_NOT_FOUND", "Not found", "No bill has been issued for this session."
        )
    return billing_service.bill_to_out(bill)


@router.post("/sessions/{session_id}/bill/issue", response_model=BillOut)
def issue_bill(
    session_id: UUID,
    actor: Actor = Depends(require_permission("bills.issue")),
    db: Session = Depends(get_db),
) -> BillOut:
    bill = billing_service.issue_bill(db, actor.membership, session_id)
    return billing_service.bill_to_out(bill)


@router.post("/bills/{bill_id}/payments", response_model=BillOut)
def record_payment(
    bill_id: UUID,
    payload: RecordPaymentRequest,
    actor: Actor = Depends(require_permission("payments.record")),
    db: Session = Depends(get_db),
    idempotency_key: str = Depends(idempotency_key),
) -> BillOut:
    bill = billing_service.record_payment(
        db,
        actor.membership,
        bill_id,
        method_id=payload.method_id,
        amount_minor=payload.amount_minor,
        note=payload.note,
        idempotency_key=idempotency_key,
    )
    return billing_service.bill_to_out(bill)
