from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import Actor, require_permission
from app.db.session import get_db
from app.schemas.common import KitchenTicketOut
from app.schemas.staff import KitchenItemStatusRequest
from app.services import kitchen as kitchen_service

router = APIRouter(tags=["kitchen"])


@router.get("/kitchen/tickets", response_model=list[KitchenTicketOut])
def list_tickets(
    actor: Actor = Depends(require_permission("kitchen.read")),
    db: Session = Depends(get_db),
) -> list[KitchenTicketOut]:
    return kitchen_service.list_tickets(db, actor.restaurant_id)


@router.post("/kitchen/ticket-items/{item_id}/status", response_model=KitchenTicketOut)
def update_item_status(
    item_id: UUID,
    payload: KitchenItemStatusRequest,
    actor: Actor = Depends(require_permission("kitchen.read")),
    db: Session = Depends(get_db),
) -> KitchenTicketOut:
    """Kitchen progress is `kitchen.update`; delivering to the guest (`SERVED`)
    is floor work and requires `orders.serve` — a waiter/manager/owner. A single
    endpoint serves both flows, so the permission is split on the target status."""
    actor.require("orders.serve" if payload.status == "SERVED" else "kitchen.update")
    return kitchen_service.transition_kitchen_item(db, actor.membership, item_id, payload.status)


@router.post("/kitchen/tickets/{ticket_id}/call-waiter", response_model=KitchenTicketOut)
def call_waiter(
    ticket_id: UUID,
    actor: Actor = Depends(require_permission("kitchen.update")),
    db: Session = Depends(get_db),
) -> KitchenTicketOut:
    return kitchen_service.mark_ticket_ready_and_call_waiter(db, actor.membership, ticket_id)
