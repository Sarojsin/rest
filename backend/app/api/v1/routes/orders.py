from uuid import UUID

from fastapi import APIRouter, Depends, Header
from sqlalchemy.orm import Session

from app.api.deps import Actor, require_permission
from app.core.errors import AppError
from app.db.session import get_db
from app.schemas.common import BillOut, OrderOut
from app.schemas.staff import CashPaymentRequest, CreateWaiterOrderRequest, RejectOrderRequest
from app.services import billing as billing_service
from app.services import orders as order_service

router = APIRouter(tags=["orders"])


def _idempotency_key(idempotency_key: str | None = Header(default=None, alias="Idempotency-Key")) -> str:
    if not idempotency_key or len(idempotency_key) < 8:
        raise AppError(
            400,
            "IDEMPOTENCY_KEY_REQUIRED",
            "Idempotency key required",
            "Provide an Idempotency-Key header of at least 8 characters.",
        )
    return idempotency_key


@router.get("/orders", response_model=list[OrderOut])
def list_orders(
    status: str | None = None,
    source: str | None = None,
    actor: Actor = Depends(require_permission("orders.read")),
    db: Session = Depends(get_db),
) -> list[OrderOut]:
    return [order_service.order_to_out(order) for order in order_service.list_orders(db, actor.restaurant_id, status, source)]


@router.get("/orders/{order_id}", response_model=OrderOut)
def get_order(
    order_id: UUID,
    actor: Actor = Depends(require_permission("orders.read")),
    db: Session = Depends(get_db),
) -> OrderOut:
    order = order_service._load_order(db, actor.restaurant_id, order_id)
    return order_service.order_to_out(order)


@router.post("/orders", response_model=OrderOut)
def create_waiter_order(
    payload: CreateWaiterOrderRequest,
    actor: Actor = Depends(require_permission("orders.create")),
    db: Session = Depends(get_db),
    idempotency_key: str = Depends(_idempotency_key),
) -> OrderOut:
    order = order_service.create_waiter_order(
        db,
        membership=actor.membership,
        table_id=payload.table_id,
        items=payload.items,
        customer_note=payload.customer_note,
        idempotency_key=idempotency_key,
    )
    return order_service.order_to_out(order)


@router.post("/orders/{order_id}/accept", response_model=OrderOut)
def accept_order(
    order_id: UUID,
    actor: Actor = Depends(require_permission("orders.confirm_qr")),
    db: Session = Depends(get_db),
) -> OrderOut:
    order = order_service.accept_qr_order(db, actor.membership, order_id)
    return order_service.order_to_out(order)


@router.post("/orders/{order_id}/reject", response_model=OrderOut)
def reject_order(
    order_id: UUID,
    payload: RejectOrderRequest,
    actor: Actor = Depends(require_permission("orders.confirm_qr")),
    db: Session = Depends(get_db),
) -> OrderOut:
    order = order_service.reject_qr_order(
        db, actor.membership, order_id, payload.reason_code, payload.note
    )
    return order_service.order_to_out(order)


@router.get("/sessions/{session_id}/bill", response_model=BillOut)
def get_bill(
    session_id: UUID,
    actor: Actor = Depends(require_permission("bills.issue")),
    db: Session = Depends(get_db),
) -> BillOut:
    bill = billing_service.get_session_bill(db, actor.restaurant_id, session_id)
    if bill is None:
        raise AppError(404, "BILL_NOT_FOUND", "Not found", "No bill has been issued for this session.")
    return billing_service.bill_to_out(bill)


@router.post("/sessions/{session_id}/bill/issue", response_model=BillOut)
def issue_bill(
    session_id: UUID,
    actor: Actor = Depends(require_permission("bills.issue")),
    db: Session = Depends(get_db),
) -> BillOut:
    bill = billing_service.issue_bill(db, actor.membership, session_id)
    return billing_service.bill_to_out(bill)


@router.post("/bills/{bill_id}/cash-payments", response_model=BillOut)
def record_cash(
    bill_id: UUID,
    payload: CashPaymentRequest,
    actor: Actor = Depends(require_permission("payments.record_cash")),
    db: Session = Depends(get_db),
    idempotency_key: str = Depends(_idempotency_key),
) -> BillOut:
    bill = billing_service.record_cash_payment(
        db, actor.membership, bill_id, payload.amount_minor, idempotency_key
    )
    return billing_service.bill_to_out(bill)
