import json
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.errors import AppError
from app.domain.enums import (
    KitchenItemStatus,
    KitchenTicketStatus,
    OrderStatus,
    ServiceCallKind,
    ServiceCallStatus,
)
from app.domain.transitions import assert_kitchen_item_transition
from app.models.identity import RestaurantMembership
from app.models.kitchen import KitchenTicket, KitchenTicketItem
from app.models.orders import Order, OrderItem
from app.models.service_calls import ServiceCall
from app.models.tables import RestaurantTable
from app.schemas.common import KitchenTicketItemOut, KitchenTicketOut
from app.services.audit import record_audit, record_outbox


def _ticket_status_from_items(items: list[KitchenTicketItem]) -> str:
    statuses = {KitchenItemStatus(item.status) for item in items}
    if statuses == {KitchenItemStatus.CANCELLED}:
        return KitchenTicketStatus.CANCELLED
    if statuses.issubset({KitchenItemStatus.READY, KitchenItemStatus.SERVED, KitchenItemStatus.CANCELLED}) and (
        KitchenItemStatus.READY in statuses or KitchenItemStatus.SERVED in statuses
    ):
        return KitchenTicketStatus.READY
    if KitchenItemStatus.PREPARING in statuses or KitchenItemStatus.READY in statuses:
        return KitchenTicketStatus.IN_PROGRESS
    return KitchenTicketStatus.NEW


def _name_and_table_maps(
    db: Session, tickets: list[KitchenTicket]
) -> tuple[dict[UUID, OrderItem], dict[UUID, RestaurantTable]]:
    order_item_ids = [item.order_item_id for ticket in tickets for item in ticket.items]
    order_items = {
        item.id: item
        for item in db.scalars(select(OrderItem).where(OrderItem.id.in_(order_item_ids))).all()
    } if order_item_ids else {}
    table_ids = {ticket.order.table_id for ticket in tickets if ticket.order}
    tables = {
        table.id: table
        for table in db.scalars(select(RestaurantTable).where(RestaurantTable.id.in_(table_ids))).all()
    } if table_ids else {}
    return order_items, tables


def _ticket_out(
    ticket: KitchenTicket,
    order_items: dict[UUID, OrderItem],
    tables: dict[UUID, RestaurantTable],
) -> KitchenTicketOut:
    """Single serializer shared by the queue listing and direct transitions."""
    table = tables.get(ticket.order.table_id) if ticket.order else None
    items_out = []
    for item in ticket.items:
        order_item = order_items.get(item.order_item_id)
        items_out.append(
            KitchenTicketItemOut(
                id=item.id,
                order_item_id=item.order_item_id,
                status=item.status,
                quantity_snapshot=item.quantity_snapshot,
                instructions_snapshot=item.instructions_snapshot,
                item_name=order_item.item_name_snapshot if order_item else None,
                table_display_name=table.display_name if table else None,
            )
        )
    return KitchenTicketOut(
        id=ticket.id,
        order_id=ticket.order_id,
        ticket_number=ticket.ticket_number,
        status=ticket.status,
        created_at=ticket.created_at,
        started_at=ticket.started_at,
        ready_at=ticket.ready_at,
        table_display_name=table.display_name if table else None,
        items=items_out,
    )


def list_tickets(db: Session, restaurant_id: UUID) -> list[KitchenTicketOut]:
    tickets = db.scalars(
        select(KitchenTicket)
        .options(selectinload(KitchenTicket.items), selectinload(KitchenTicket.order))
        .where(
            KitchenTicket.restaurant_id == restaurant_id,
            KitchenTicket.status != KitchenTicketStatus.CANCELLED,
        )
        .order_by(KitchenTicket.created_at.asc())
    ).unique().all()
    order_items, tables = _name_and_table_maps(db, list(tickets))
    return [_ticket_out(ticket, order_items, tables) for ticket in tickets]


def transition_kitchen_item(
    db: Session, membership: RestaurantMembership, item_id: UUID, next_status: str
) -> KitchenTicketOut:
    item = db.scalar(
        select(KitchenTicketItem)
        .options(selectinload(KitchenTicketItem.ticket).selectinload(KitchenTicket.order))
        .where(
            KitchenTicketItem.id == item_id,
            KitchenTicketItem.restaurant_id == membership.restaurant_id,
        )
    )
    if item is None:
        raise AppError(404, "TICKET_ITEM_NOT_FOUND", "Not found", "Kitchen item was not found.")
    try:
        target = KitchenItemStatus(next_status)
    except ValueError as exc:
        raise AppError(422, "INVALID_STATUS", "Validation error", "Unknown kitchen status.") from exc

    assert_kitchen_item_transition(KitchenItemStatus(item.status), target)
    now = datetime.now(UTC)
    item.status = target
    item.updated_by_membership_id = membership.id
    if target == KitchenItemStatus.PREPARING:
        item.started_at = now
    elif target == KitchenItemStatus.READY:
        item.ready_at = now
    elif target == KitchenItemStatus.SERVED:
        item.served_at = now
        if item.ticket.order:
            remaining = db.scalars(
                select(KitchenTicketItem).where(KitchenTicketItem.ticket_id == item.ticket_id)
            ).all()
            if all(KitchenItemStatus(i.status) in {KitchenItemStatus.SERVED, KitchenItemStatus.CANCELLED} for i in remaining):
                order = db.get(Order, item.ticket.order_id)
                if order and order.status == "ACCEPTED":
                    order.status = "COMPLETED"
                    order.completed_at = now
    elif target == KitchenItemStatus.CANCELLED:
        item.cancelled_at = now

    ticket = item.ticket
    ticket.status = _ticket_status_from_items(list(ticket.items))
    ticket.last_updated_by_membership_id = membership.id
    if ticket.status == KitchenTicketStatus.IN_PROGRESS and ticket.started_at is None:
        ticket.started_at = now
    if ticket.status == KitchenTicketStatus.READY and ticket.ready_at is None:
        ticket.ready_at = now

    record_audit(
        db,
        restaurant_id=membership.restaurant_id,
        action="kitchen.item_status",
        entity_type="kitchen_ticket_item",
        entity_id=item.id,
        actor_user_id=membership.user_id,
        actor_membership_id=membership.id,
        detail=f"{item.status}",
    )
    db.commit()
    return _single_ticket_out(db, membership.restaurant_id, item.ticket_id)


def _pickup_summary(db: Session, ticket: KitchenTicket) -> str:
    """Human-readable snapshot of the food waiting to be served, for service calls."""
    serving_items = [
        item
        for item in ticket.items
        if KitchenItemStatus(item.status)
        not in {KitchenItemStatus.CANCELLED, KitchenItemStatus.SERVED}
    ]
    order_item_ids = [item.order_item_id for item in serving_items]
    names: dict[UUID, str] = {}
    if order_item_ids:
        rows = db.scalars(select(OrderItem).where(OrderItem.id.in_(order_item_ids))).all()
        names = {row.id: row.item_name_snapshot for row in rows}
    return ", ".join(
        f"{item.quantity_snapshot}x {names.get(item.order_item_id, 'item')}"
        for item in serving_items
    )


def _single_ticket_out(db: Session, restaurant_id: UUID, ticket_id: UUID) -> KitchenTicketOut:
    """Serialize one ticket directly, so responses exist even for CANCELLED tickets."""
    ticket = db.scalar(
        select(KitchenTicket)
        .options(selectinload(KitchenTicket.items), selectinload(KitchenTicket.order))
        .where(
            KitchenTicket.id == ticket_id,
            KitchenTicket.restaurant_id == restaurant_id,
        )
    )
    if ticket is None:
        raise AppError(404, "TICKET_NOT_FOUND", "Not found", "Kitchen ticket was not found.")
    order_items, tables = _name_and_table_maps(db, [ticket])
    return _ticket_out(ticket, order_items, tables)


def mark_ticket_ready_and_call_waiter(
    db: Session, membership: RestaurantMembership, ticket_id: UUID
) -> KitchenTicketOut:
    """Kitchen signals that a ticket is done: force its open items to READY and
    raise a kitchen service call so service staff come to pick the food up.

    Repeat taps while a REQUESTED call is open for the ticket are no-ops
    (idempotent), so double presses never spam the service queue.
    """
    ticket = db.scalar(
        select(KitchenTicket)
        .options(selectinload(KitchenTicket.items), selectinload(KitchenTicket.order))
        .where(
            KitchenTicket.id == ticket_id,
            KitchenTicket.restaurant_id == membership.restaurant_id,
        )
    )
    if ticket is None:
        raise AppError(404, "TICKET_NOT_FOUND", "Not found", "Kitchen ticket was not found.")
    order = ticket.order
    if (
        ticket.status == KitchenTicketStatus.CANCELLED
        or order is None
        or OrderStatus(order.status) != OrderStatus.ACCEPTED
    ):
        raise AppError(
            409,
            "KITCHEN_STATE_CONFLICT",
            "State conflict",
            "This ticket is closed and cannot be signalled to service.",
        )

    open_call = db.scalar(
        select(ServiceCall)
        .where(
            ServiceCall.restaurant_id == membership.restaurant_id,
            ServiceCall.kind == ServiceCallKind.KITCHEN,
            ServiceCall.kitchen_ticket_id == ticket.id,
            ServiceCall.status == ServiceCallStatus.REQUESTED,
        )
        .order_by(ServiceCall.created_at.desc())
    )
    if open_call is not None:
        return _single_ticket_out(db, membership.restaurant_id, ticket_id)

    now = datetime.now(UTC)
    for item in ticket.items:
        status = KitchenItemStatus(item.status)
        if status in {KitchenItemStatus.NEW, KitchenItemStatus.PREPARING}:
            # Bulk "everything is done" action; per-item transitions keep the
            # fine-grained workflow for the dedicated item endpoint.
            item.status = KitchenItemStatus.READY
            if item.started_at is None:
                item.started_at = now
            item.ready_at = now
            item.updated_by_membership_id = membership.id

    ticket.status = _ticket_status_from_items(list(ticket.items))
    ticket.last_updated_by_membership_id = membership.id
    if ticket.status == KitchenTicketStatus.READY and ticket.ready_at is None:
        ticket.ready_at = now

    call = ServiceCall(
        restaurant_id=membership.restaurant_id,
        kind=ServiceCallKind.KITCHEN,
        table_id=order.table_id,
        kitchen_ticket_id=ticket.id,
        detail=_pickup_summary(db, ticket),
        status=ServiceCallStatus.REQUESTED,
        created_by_membership_id=membership.id,
    )
    db.add(call)
    db.flush()
    record_audit(
        db,
        restaurant_id=membership.restaurant_id,
        action="kitchen.call_waiter",
        entity_type="kitchen_ticket",
        entity_id=ticket.id,
        actor_user_id=membership.user_id,
        actor_membership_id=membership.id,
        detail=f"Ticket {ticket.ticket_number} marked ready for pickup: {call.detail}",
    )
    record_outbox(
        db,
        restaurant_id=membership.restaurant_id,
        event_type="service_call.requested",
        aggregate_type="service_call",
        aggregate_id=call.id,
        payload=json.dumps(
            {
                "kind": ServiceCallKind.KITCHEN,
                "kitchen_ticket_id": str(ticket.id),
                "ticket_number": ticket.ticket_number,
                "table_id": str(order.table_id),
            }
        ),
    )
    db.commit()
    return _single_ticket_out(db, membership.restaurant_id, ticket_id)
