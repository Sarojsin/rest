from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.modules.audit.services import record_audit
from app.modules.billing.models import Bill, BillItem
from app.modules.billing.schemas import BillItemOut, BillOut
from app.modules.notifications.services import record_outbox
from app.modules.operations.models import DiningSession, Order
from app.modules.payments.models import Payment, PaymentMethodConfig
from app.modules.payments.schemas import PaymentOut
from app.modules.tenancy.models import Restaurant, RestaurantMembership
from app.shared import tenant_access
from app.shared.enums import (
    BillStatus,
    DiningSessionStatus,
    OrderStatus,
    PaymentMethodKind,
    PaymentStatus,
)
from app.shared.errors import AppError


def bill_to_out(bill: Bill) -> BillOut:
    return BillOut(
        id=bill.id,
        dining_session_id=bill.dining_session_id,
        status=bill.status,
        currency_code=bill.currency_code,
        subtotal_minor=bill.subtotal_minor,
        tax_minor=bill.tax_minor,
        total_minor=bill.total_minor,
        paid_minor=bill.paid_minor,
        balance_due_minor=bill.balance_due_minor,
        version=bill.version,
        issued_at=bill.issued_at,
        items=[BillItemOut.model_validate(item) for item in bill.items],
        payments=[PaymentOut.model_validate(p) for p in bill.payments],
    )


def _load_bill(db: Session, restaurant_id: UUID, bill_id: UUID) -> Bill:
    bill = db.scalar(
        select(Bill)
        .options(selectinload(Bill.items), selectinload(Bill.payments))
        .where(Bill.id == bill_id, Bill.restaurant_id == restaurant_id)
    )
    if bill is None:
        raise AppError(404, "BILL_NOT_FOUND", "Not found", "Bill was not found.")
    return bill


def get_session_bill(db: Session, restaurant_id: UUID, session_id: UUID) -> Bill | None:
    return db.scalar(
        select(Bill)
        .options(selectinload(Bill.items), selectinload(Bill.payments))
        .where(Bill.restaurant_id == restaurant_id, Bill.dining_session_id == session_id)
    )


def _ensure_inflight(
    db: Session, restaurant_id: UUID, started_at: datetime | None
) -> None:
    """Billing/payment is allowed only for a visit that predates suspension."""
    restaurant = db.get(Restaurant, restaurant_id)
    if restaurant is None:
        raise AppError(404, "TENANT_NOT_FOUND", "Not found", "Restaurant was not found.")
    tenant_access.ensure_inflight_allowed(
        status=restaurant.status,
        archived_at=restaurant.archived_at,
        suspended_at=restaurant.suspended_at,
        started_at=started_at,
    )


def issue_bill(db: Session, membership: RestaurantMembership, session_id: UUID) -> Bill:
    session = db.scalar(
        select(DiningSession).where(
            DiningSession.id == session_id,
            DiningSession.restaurant_id == membership.restaurant_id,
        )
    )
    if session is None:
        raise AppError(404, "SESSION_NOT_FOUND", "Not found", "Dining session was not found.")
    if session.status not in {DiningSessionStatus.OPEN, DiningSessionStatus.CHECKOUT_PENDING}:
        raise AppError(409, "SESSION_CLOSED", "Session closed", "This session cannot be billed.")

    _ensure_inflight(db, membership.restaurant_id, session.opened_at)

    existing = get_session_bill(db, membership.restaurant_id, session_id)
    if existing and existing.status in {BillStatus.PAID, BillStatus.VOID}:
        raise AppError(409, "BILL_LOCKED", "Bill locked", "This bill can no longer be issued.")

    orders = (
        db.scalars(
            select(Order)
            .options(selectinload(Order.items))
            .where(
                Order.restaurant_id == membership.restaurant_id,
                Order.dining_session_id == session_id,
                Order.status.in_([OrderStatus.ACCEPTED, OrderStatus.COMPLETED]),
            )
        )
        .unique()
        .all()
    )
    if not orders:
        raise AppError(
            422, "NO_BILLABLE_ITEMS", "No billable items", "Accept an order before issuing a bill."
        )

    bill = existing or Bill(
        restaurant_id=membership.restaurant_id,
        dining_session_id=session_id,
        status=BillStatus.OPEN,
        currency_code="USD",
    )
    if existing is None:
        db.add(bill)
        db.flush()
    else:
        for item in list(bill.items):
            db.delete(item)
        db.flush()

    subtotal = 0
    tax = 0
    for order in orders:
        for item in order.items:
            db.add(
                BillItem(
                    restaurant_id=membership.restaurant_id,
                    bill_id=bill.id,
                    order_item_id=item.id,
                    description_snapshot=item.item_name_snapshot,
                    quantity=item.quantity,
                    unit_price_minor=item.unit_price_minor,
                    discount_minor=item.discount_minor,
                    tax_minor=item.tax_minor,
                    line_total_minor=item.line_total_minor,
                )
            )
            subtotal += item.unit_price_minor * item.quantity
            tax += item.tax_minor

    now = datetime.now(UTC)
    total = subtotal + tax
    paid = sum(p.amount_minor for p in bill.payments if p.status == PaymentStatus.SUCCEEDED)
    bill.subtotal_minor = subtotal
    bill.tax_minor = tax
    bill.total_minor = total
    bill.paid_minor = paid
    bill.balance_due_minor = max(total - paid, 0)
    bill.status = (
        BillStatus.ISSUED
        if paid == 0
        else (BillStatus.PAID if paid >= total else BillStatus.PARTIALLY_PAID)
    )
    bill.issued_at = now
    bill.version += 1
    bill.currency_code = orders[0].items[0].currency_code if orders and orders[0].items else "USD"
    session.status = DiningSessionStatus.CHECKOUT_PENDING
    session.version += 1

    record_audit(
        db,
        restaurant_id=membership.restaurant_id,
        action="bills.issue",
        entity_type="bill",
        entity_id=bill.id,
        actor_user_id=membership.user_id,
        actor_membership_id=membership.id,
        detail=f"total={total}",
    )
    record_outbox(
        db,
        restaurant_id=membership.restaurant_id,
        event_type="bill.issued",
        aggregate_type="bill",
        aggregate_id=bill.id,
    )
    db.commit()
    return _load_bill(db, membership.restaurant_id, bill.id)


def record_payment(
    db: Session,
    membership: RestaurantMembership,
    bill_id: UUID,
    method_id: UUID,
    amount_minor: int,
    note: str,
    idempotency_key: str,
) -> Bill:
    existing_payment = db.scalar(
        select(Payment).where(
            Payment.restaurant_id == membership.restaurant_id,
            Payment.idempotency_key == idempotency_key,
        )
    )
    if existing_payment is not None:
        return _load_bill(db, membership.restaurant_id, existing_payment.bill_id)

    method = db.scalar(
        select(PaymentMethodConfig).where(
            PaymentMethodConfig.id == method_id,
            PaymentMethodConfig.restaurant_id == membership.restaurant_id,
        )
    )
    if method is None:
        raise AppError(
            404, "PAYMENT_METHOD_NOT_FOUND", "Not found", "Payment method was not found."
        )
    if not method.is_active:
        raise AppError(
            409, "METHOD_UNAVAILABLE", "Method unavailable", "This payment method is not active."
        )
    if method.kind == PaymentMethodKind.QR and not (method.qr_image_name and method.qr_image_ext):
        raise AppError(
            422,
            "METHOD_QR_IMAGE_MISSING",
            "QR image missing",
            "Ask the owner to upload a QR image before using this method.",
        )

    bill = _load_bill(db, membership.restaurant_id, bill_id)
    session = db.get(DiningSession, bill.dining_session_id)
    _ensure_inflight(
        db,
        membership.restaurant_id,
        session.opened_at if session is not None else None,
    )
    if bill.status not in {BillStatus.ISSUED, BillStatus.PARTIALLY_PAID}:
        raise AppError(
            409, "BILL_NOT_PAYABLE", "Bill not payable", "Issue the bill before recording payment."
        )
    if amount_minor > bill.balance_due_minor:
        raise AppError(
            422,
            "AMOUNT_EXCEEDS_BALANCE",
            "Amount exceeds balance",
            "Payment cannot exceed the outstanding balance.",
        )

    now = datetime.now(UTC)
    payment = Payment(
        restaurant_id=membership.restaurant_id,
        bill_id=bill.id,
        method=method.label,
        status=PaymentStatus.SUCCEEDED,
        amount_minor=amount_minor,
        currency_code=bill.currency_code,
        note=note,
        idempotency_key=idempotency_key,
        initiated_by_membership_id=membership.id,
        succeeded_at=now,
    )
    db.add(payment)
    db.flush()
    bill.paid_minor += amount_minor
    bill.balance_due_minor = max(bill.total_minor - bill.paid_minor, 0)
    if bill.balance_due_minor == 0:
        bill.status = BillStatus.PAID
        bill.paid_at = now
        session = db.get(DiningSession, bill.dining_session_id)
        if session:
            session.status = DiningSessionStatus.CLOSED
            session.closed_at = now
            session.closed_by_membership_id = membership.id
    else:
        bill.status = BillStatus.PARTIALLY_PAID
    bill.version += 1
    record_audit(
        db,
        restaurant_id=membership.restaurant_id,
        action="payments.record",
        entity_type="payment",
        entity_id=payment.id,
        actor_user_id=membership.user_id,
        actor_membership_id=membership.id,
        detail=f"method={method.label};amount={amount_minor};bill={bill.id}",
    )
    record_outbox(
        db,
        restaurant_id=membership.restaurant_id,
        event_type="payment.recorded",
        aggregate_type="payment",
        aggregate_id=payment.id,
        payload=(
            f'{{"bill_id": "{bill.id}", "method": "{method.label}", '
            f'"amount_minor": {amount_minor}}}'
        ),
    )
    db.commit()
    return _load_bill(db, membership.restaurant_id, bill.id)
