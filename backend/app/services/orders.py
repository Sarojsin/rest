from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.errors import AppError
from app.core.security import hash_token, new_token
from app.domain.enums import (
    DiningSessionStatus,
    KitchenItemStatus,
    KitchenTicketStatus,
    OrderSource,
    OrderStatus,
)
from app.domain.transitions import assert_order_transition
from app.models.identity import RestaurantMembership, RestaurantSettings
from app.models.kitchen import KitchenTicket, KitchenTicketItem
from app.models.menu import MenuItem
from app.models.orders import Order, OrderItem
from app.models.tables import DiningSession, RestaurantTable, TableQrCode
from app.schemas.common import OrderItemIn, OrderItemOut, OrderOut
from app.services.audit import record_audit, record_outbox
from app.services.money import line_amounts


def _tax_rate(db: Session, restaurant_id: UUID) -> int:
    settings = db.get(RestaurantSettings, restaurant_id)
    return settings.tax_rate_bps if settings else 1000


def order_to_out(order: Order) -> OrderOut:
    items = [
        OrderItemOut.model_validate(item)
        for item in sorted(order.items, key=lambda i: str(i.id))
    ]
    subtotal = sum(i.unit_price_minor * i.quantity for i in order.items)
    tax = sum(i.tax_minor for i in order.items)
    return OrderOut(
        id=order.id,
        table_id=order.table_id,
        dining_session_id=order.dining_session_id,
        source=order.source,
        status=order.status,
        customer_note=order.customer_note,
        submitted_at=order.submitted_at,
        accepted_at=order.accepted_at,
        rejected_at=order.rejected_at,
        rejection_reason_code=order.rejection_reason_code,
        rejection_note=order.rejection_note,
        version=order.version,
        items=items,
        subtotal_minor=subtotal,
        tax_minor=tax,
        total_minor=subtotal + tax,
    )


def _load_order(db: Session, restaurant_id: UUID, order_id: UUID) -> Order:
    order = db.scalar(
        select(Order)
        .options(selectinload(Order.items))
        .where(Order.id == order_id, Order.restaurant_id == restaurant_id)
    )
    if order is None:
        raise AppError(404, "ORDER_NOT_FOUND", "Not found", "Order was not found.")
    return order


def _resolve_items(
    db: Session, restaurant_id: UUID, items: list[OrderItemIn]
) -> list[tuple[MenuItem, OrderItemIn]]:
    ids = [item.menu_item_id for item in items]
    rows = db.scalars(
        select(MenuItem).where(MenuItem.restaurant_id == restaurant_id, MenuItem.id.in_(ids))
    ).all()
    by_id = {row.id: row for row in rows}
    resolved: list[tuple[MenuItem, OrderItemIn]] = []
    for item in items:
        menu_item = by_id.get(item.menu_item_id)
        if menu_item is None or menu_item.status != "PUBLISHED":
            raise AppError(
                422,
                "ITEM_UNAVAILABLE",
                "Item unavailable",
                "One or more items are not currently available.",
            )
        resolved.append((menu_item, item))
    return resolved


def _build_order_items(
    restaurant_id: UUID, order_id: UUID, resolved: list[tuple[MenuItem, OrderItemIn]], tax_rate: int
) -> list[OrderItem]:
    result: list[OrderItem] = []
    for menu_item, incoming in resolved:
        subtotal, tax, total = line_amounts(menu_item.current_price_minor, incoming.quantity, tax_rate)
        result.append(
            OrderItem(
                restaurant_id=restaurant_id,
                order_id=order_id,
                menu_item_id=menu_item.id,
                item_name_snapshot=menu_item.name,
                quantity=incoming.quantity,
                unit_price_minor=menu_item.current_price_minor,
                discount_minor=0,
                tax_minor=tax,
                line_total_minor=total,
                currency_code=menu_item.currency_code,
                special_instructions=incoming.special_instructions.strip(),
            )
        )
    return result


def _active_session(db: Session, restaurant_id: UUID, table_id: UUID) -> DiningSession | None:
    return db.scalar(
        select(DiningSession).where(
            DiningSession.restaurant_id == restaurant_id,
            DiningSession.table_id == table_id,
            DiningSession.status.in_(
                [DiningSessionStatus.OPEN, DiningSessionStatus.CHECKOUT_PENDING]
            ),
        )
    )


def _ensure_session(
    db: Session, restaurant_id: UUID, table_id: UUID, membership_id: UUID | None
) -> DiningSession:
    existing = _active_session(db, restaurant_id, table_id)
    if existing:
        return existing
    session = DiningSession(
        restaurant_id=restaurant_id,
        table_id=table_id,
        status=DiningSessionStatus.OPEN,
        opened_at=datetime.now(UTC),
        opened_by_membership_id=membership_id,
    )
    db.add(session)
    db.flush()
    return session


def resolve_qr(db: Session, qr_token: str) -> tuple[TableQrCode, RestaurantTable]:
    token_hash = hash_token(qr_token)
    qr = db.scalar(
        select(TableQrCode)
        .options(selectinload(TableQrCode.table))
        .where(TableQrCode.token_hash == token_hash, TableQrCode.status == "ACTIVE")
    )
    if qr is None:
        raise AppError(404, "QR_INVALID", "Not found", "This table code is not valid.")
    table = qr.table
    if table.status != "ACTIVE":
        raise AppError(409, "TABLE_UNAVAILABLE", "Table unavailable", "This table is out of service.")
    return qr, table


def submit_qr_order(
    db: Session,
    *,
    qr_token: str,
    items: list[OrderItemIn],
    customer_note: str,
    idempotency_key: str,
) -> tuple[Order, str]:
    qr, table = resolve_qr(db, qr_token)
    restaurant_id = qr.restaurant_id
    existing = db.scalar(
        select(Order)
        .options(selectinload(Order.items))
        .where(Order.restaurant_id == restaurant_id, Order.idempotency_key == idempotency_key)
    )
    if existing is not None:
        return existing, ""

    resolved = _resolve_items(db, restaurant_id, items)
    status_token = new_token()
    now = datetime.now(UTC)
    order = Order(
        restaurant_id=restaurant_id,
        table_id=table.id,
        dining_session_id=None,
        source=OrderSource.CUSTOMER_QR,
        status=OrderStatus.PENDING_CONFIRMATION,
        idempotency_key=idempotency_key,
        customer_status_token_hash=hash_token(status_token),
        customer_note=customer_note.strip(),
        submitted_at=now,
    )
    db.add(order)
    db.flush()
    for item in _build_order_items(restaurant_id, order.id, resolved, _tax_rate(db, restaurant_id)):
        db.add(item)
    record_audit(
        db,
        restaurant_id=restaurant_id,
        action="orders.submit_qr",
        entity_type="order",
        entity_id=order.id,
        detail="Customer QR order submitted",
    )
    record_outbox(
        db,
        restaurant_id=restaurant_id,
        event_type="order.pending_confirmation",
        aggregate_type="order",
        aggregate_id=order.id,
    )
    db.commit()
    db.refresh(order)
    order = _load_order(db, restaurant_id, order.id)
    return order, status_token


def get_public_order_status(db: Session, status_token: str) -> Order:
    order = db.scalar(
        select(Order)
        .options(selectinload(Order.items))
        .where(Order.customer_status_token_hash == hash_token(status_token))
    )
    if order is None:
        raise AppError(404, "ORDER_NOT_FOUND", "Not found", "Order status was not found.")
    return order


def create_waiter_order(
    db: Session,
    *,
    membership: RestaurantMembership,
    table_id: UUID,
    items: list[OrderItemIn],
    customer_note: str,
    idempotency_key: str,
) -> Order:
    restaurant_id = membership.restaurant_id
    existing = db.scalar(
        select(Order)
        .options(selectinload(Order.items))
        .where(Order.restaurant_id == restaurant_id, Order.idempotency_key == idempotency_key)
    )
    if existing is not None:
        return existing

    table = db.scalar(
        select(RestaurantTable).where(
            RestaurantTable.id == table_id, RestaurantTable.restaurant_id == restaurant_id
        )
    )
    if table is None or table.status != "ACTIVE":
        raise AppError(404, "TABLE_NOT_FOUND", "Not found", "Table was not found.")

    resolved = _resolve_items(db, restaurant_id, items)
    session = _ensure_session(db, restaurant_id, table.id, membership.id)
    now = datetime.now(UTC)
    order = Order(
        restaurant_id=restaurant_id,
        table_id=table.id,
        dining_session_id=session.id,
        source=OrderSource.WAITER,
        status=OrderStatus.ACCEPTED,
        created_by_membership_id=membership.id,
        idempotency_key=idempotency_key,
        customer_note=customer_note.strip(),
        submitted_at=now,
        accepted_at=now,
        decision_by_membership_id=membership.id,
    )
    db.add(order)
    db.flush()
    built = _build_order_items(restaurant_id, order.id, resolved, _tax_rate(db, restaurant_id))
    for item in built:
        db.add(item)
    db.flush()
    _create_kitchen_ticket(db, order, built, membership.id)
    record_audit(
        db,
        restaurant_id=restaurant_id,
        action="orders.create_waiter",
        entity_type="order",
        entity_id=order.id,
        actor_user_id=membership.user_id,
        actor_membership_id=membership.id,
        detail="Waiter order sent to kitchen",
    )
    record_outbox(
        db,
        restaurant_id=restaurant_id,
        event_type="order.accepted",
        aggregate_type="order",
        aggregate_id=order.id,
    )
    db.commit()
    return _load_order(db, restaurant_id, order.id)


def _next_ticket_number(db: Session, restaurant_id: UUID) -> int:
    current = db.scalars(
        select(KitchenTicket.ticket_number)
        .where(KitchenTicket.restaurant_id == restaurant_id)
        .order_by(KitchenTicket.ticket_number.desc())
    ).first()
    return (current or 0) + 1


def _create_kitchen_ticket(
    db: Session, order: Order, items: list[OrderItem], membership_id: UUID | None
) -> KitchenTicket:
    ticket = KitchenTicket(
        restaurant_id=order.restaurant_id,
        order_id=order.id,
        ticket_number=_next_ticket_number(db, order.restaurant_id),
        status=KitchenTicketStatus.NEW,
        last_updated_by_membership_id=membership_id,
    )
    db.add(ticket)
    db.flush()
    for item in items:
        db.add(
            KitchenTicketItem(
                restaurant_id=order.restaurant_id,
                ticket_id=ticket.id,
                order_item_id=item.id,
                status=KitchenItemStatus.NEW,
                quantity_snapshot=item.quantity,
                instructions_snapshot=item.special_instructions,
                updated_by_membership_id=membership_id,
            )
        )
    return ticket


def accept_qr_order(db: Session, membership: RestaurantMembership, order_id: UUID) -> Order:
    order = _load_order(db, membership.restaurant_id, order_id)
    assert_order_transition(OrderStatus(order.status), OrderStatus.ACCEPTED)
    now = datetime.now(UTC)
    session = _ensure_session(db, membership.restaurant_id, order.table_id, membership.id)
    order.status = OrderStatus.ACCEPTED
    order.accepted_at = now
    order.dining_session_id = session.id
    order.decision_by_membership_id = membership.id
    order.version += 1
    _create_kitchen_ticket(db, order, list(order.items), membership.id)
    record_audit(
        db,
        restaurant_id=membership.restaurant_id,
        action="orders.accept_qr",
        entity_type="order",
        entity_id=order.id,
        actor_user_id=membership.user_id,
        actor_membership_id=membership.id,
        detail="QR order accepted",
    )
    record_outbox(
        db,
        restaurant_id=membership.restaurant_id,
        event_type="order.accepted",
        aggregate_type="order",
        aggregate_id=order.id,
    )
    db.commit()
    return _load_order(db, membership.restaurant_id, order.id)


def reject_qr_order(
    db: Session, membership: RestaurantMembership, order_id: UUID, reason_code: str, note: str
) -> Order:
    order = _load_order(db, membership.restaurant_id, order_id)
    assert_order_transition(OrderStatus(order.status), OrderStatus.REJECTED)
    order.status = OrderStatus.REJECTED
    order.rejected_at = datetime.now(UTC)
    order.decision_by_membership_id = membership.id
    order.rejection_reason_code = reason_code
    order.rejection_note = note.strip()
    order.version += 1
    record_audit(
        db,
        restaurant_id=membership.restaurant_id,
        action="orders.reject_qr",
        entity_type="order",
        entity_id=order.id,
        actor_user_id=membership.user_id,
        actor_membership_id=membership.id,
        detail=f"Rejected: {reason_code}",
    )
    db.commit()
    return _load_order(db, membership.restaurant_id, order.id)


def list_orders(
    db: Session, restaurant_id: UUID, status: str | None = None, source: str | None = None
) -> list[Order]:
    stmt = (
        select(Order)
        .options(selectinload(Order.items))
        .where(Order.restaurant_id == restaurant_id)
        .order_by(Order.submitted_at.desc())
    )
    if status:
        stmt = stmt.where(Order.status == status)
    if source:
        stmt = stmt.where(Order.source == source)
    return list(db.scalars(stmt).unique().all())
