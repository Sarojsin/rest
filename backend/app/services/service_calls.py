from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.core.errors import AppError
from app.domain.enums import ServiceCallKind, ServiceCallStatus
from app.models.identity import RestaurantMembership
from app.models.kitchen import KitchenTicket
from app.models.service_calls import ServiceCall
from app.models.tables import RestaurantTable
from app.services.audit import record_audit, record_outbox
from app.services.orders import resolve_qr


def create_service_call(db: Session, qr_token: str) -> tuple[ServiceCall, bool]:
    """Create a waiter call for the table behind a QR token.

    Idempotent in practice: while a REQUESTED call is open for the table,
    repeated taps return the existing call instead of spamming new rows.
    Returns (call, created) where created is False for a duplicate tap.
    """
    qr, table = resolve_qr(db, qr_token)
    open_call = db.scalar(
        select(ServiceCall)
        .where(
            ServiceCall.table_id == table.id,
            ServiceCall.kind == ServiceCallKind.GUEST,
            ServiceCall.status == ServiceCallStatus.REQUESTED,
        )
        .order_by(ServiceCall.created_at.desc())
    )
    if open_call is not None:
        return open_call, False
    call = ServiceCall(
        restaurant_id=qr.restaurant_id,
        kind=ServiceCallKind.GUEST,
        table_id=table.id,
        status=ServiceCallStatus.REQUESTED,
    )
    db.add(call)
    db.flush()
    record_audit(
        db,
        restaurant_id=qr.restaurant_id,
        action="service_calls.create",
        entity_type="service_call",
        entity_id=call.id,
        detail=f"Guest requested service at {table.display_name}",
    )
    record_outbox(
        db,
        restaurant_id=qr.restaurant_id,
        event_type="service_call.requested",
        aggregate_type="service_call",
        aggregate_id=call.id,
    )
    db.commit()
    db.refresh(call)
    return call, True


def latest_service_call_for_qr(db: Session, qr_token: str) -> ServiceCall | None:
    """Read-only status for the guest, scoped to one table via the QR token."""
    _, table = resolve_qr(db, qr_token)
    return db.scalar(
        select(ServiceCall)
        .where(ServiceCall.table_id == table.id)
        .order_by(ServiceCall.created_at.desc())
    )


def list_service_calls(
    db: Session, restaurant_id: UUID, status: str | None = None
) -> list[tuple[ServiceCall, RestaurantTable]]:
    stmt = (
        select(ServiceCall)
        .options(joinedload(ServiceCall.table))
        .where(ServiceCall.restaurant_id == restaurant_id)
        .order_by(ServiceCall.created_at.desc())
    )
    if status:
        stmt = stmt.where(ServiceCall.status == status)
    rows = db.execute(stmt).unique().all()
    return [(row[0], row[0].table) for row in rows]


def acknowledge_service_call(
    db: Session, membership: RestaurantMembership, call_id: UUID
) -> tuple[ServiceCall, bool]:
    """Waiter confirms they are attending; deduplicates concurrent taps."""
    call = db.scalar(
        select(ServiceCall).where(
            ServiceCall.id == call_id,
            ServiceCall.restaurant_id == membership.restaurant_id,
        )
    )
    if call is None:
        raise AppError(404, "CALL_NOT_FOUND", "Not found", "Service call was not found.")
    if call.status == ServiceCallStatus.ACKNOWLEDGED:
        return call, False
    if call.status != ServiceCallStatus.REQUESTED:
        raise AppError(
            409,
            "CALL_NOT_CANCELLABLE",
            "State conflict",
            "This service call cannot be acknowledged right now.",
        )
    call.status = ServiceCallStatus.ACKNOWLEDGED
    call.acknowledged_at = datetime.now(UTC)
    call.acknowledged_by_membership_id = membership.id
    table = db.get(RestaurantTable, call.table_id)
    record_audit(
        db,
        restaurant_id=membership.restaurant_id,
        action="service_calls.acknowledge",
        entity_type="service_call",
        entity_id=call.id,
        actor_user_id=membership.user_id,
        actor_membership_id=membership.id,
        detail=f"Service call acknowledged at {table.display_name if table else 'table'}",
    )
    db.commit()
    db.refresh(call)
    return call, True


def ticket_numbers_for_calls(db: Session, calls: list[ServiceCall]) -> dict[UUID, int]:
    """Ticket numbers for kitchen-initiated calls, resolved in a single query."""
    ticket_ids = {call.kitchen_ticket_id for call in calls if call.kitchen_ticket_id}
    if not ticket_ids:
        return {}
    rows = db.execute(
        select(KitchenTicket.id, KitchenTicket.ticket_number).where(
            KitchenTicket.id.in_(ticket_ids)
        )
    ).all()
    return {ticket_id: ticket_number for ticket_id, ticket_number in rows}
