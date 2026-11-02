from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import Actor, require_permission
from app.api.idempotency import idempotency_key
from app.db.session import get_db
from app.modules.operations.schemas import CreateWaiterOrderRequest, OrderOut, RejectOrderRequest
from app.modules.operations.services import orders as order_service

router = APIRouter(tags=["orders"])


@router.get("/orders", response_model=list[OrderOut])
def list_orders(
    status: str | None = None,
    source: str | None = None,
    actor: Actor = Depends(require_permission("orders.read")),
    db: Session = Depends(get_db),
) -> list[OrderOut]:
    return [
        order_service.order_to_out(order)
        for order in order_service.list_orders(db, actor.restaurant_id, status, source)
    ]


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
    idempotency_key: str = Depends(idempotency_key),
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
