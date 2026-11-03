from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import Actor, require_permission
from app.db.session import get_db
from app.modules.operations.schemas import (
    CreateWaiterOrderRequest,
    EscalateOrderRequest,
    OrderOut,
    RejectOrderRequest,
)
from app.modules.operations.services import claims as claim_service
from app.modules.operations.services import orders as order_service
from app.shared.idempotency import idempotency_key

router = APIRouter(tags=["orders"])


@router.get("/orders", response_model=list[OrderOut])
def list_orders(
    status: str | None = None,
    source: str | None = None,
    actor: Actor = Depends(require_permission("orders.read")),
    db: Session = Depends(get_db),
) -> list[OrderOut]:
    # Plan 08: expired claims must never linger silently in the shared view.
    claim_service.sweep_expired_claims(db, actor.restaurant_id)
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


# --- Waiter claims (plan 08) ---------------------------------------------------


@router.post("/orders/{order_id}/claim", response_model=OrderOut)
def claim_order(
    order_id: UUID,
    actor: Actor = Depends(require_permission("orders.confirm_qr")),
    db: Session = Depends(get_db),
) -> OrderOut:
    order = claim_service.claim_order(db, actor.membership, order_id)
    return order_service.order_to_out(order)


@router.post("/orders/{order_id}/escalate", response_model=OrderOut)
def escalate_order(
    order_id: UUID,
    payload: EscalateOrderRequest,
    actor: Actor = Depends(require_permission("orders.confirm_qr")),
    db: Session = Depends(get_db),
) -> OrderOut:
    is_supervisor = actor.membership.role == "manager"
    order = claim_service.escalate_order(
        db, actor.membership, order_id, payload.note, is_supervisor=is_supervisor
    )
    return order_service.order_to_out(order)


@router.post("/orders/{order_id}/release", response_model=OrderOut)
def release_claim(
    order_id: UUID,
    actor: Actor = Depends(require_permission("orders.serve")),
    db: Session = Depends(get_db),
) -> OrderOut:
    order = claim_service.release_claim(
        db, actor.membership, order_id, is_supervisor=bool(actor.membership.role == "manager")
    )
    return order_service.order_to_out(order)
