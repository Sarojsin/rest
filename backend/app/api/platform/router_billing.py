"""Platform invoices, payments, and refunds (plan 05 §7)."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, Request, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.modules.platform.deps import (
    PlatformActor,
    require_platform_permission,
    require_platform_step_up,
)
from app.modules.platform.models import (
    PlatformInvoice,
    PlatformPayment,
    PlatformPaymentEvent,
    PlatformSubscription,
)
from app.modules.platform.schemas_admin import (
    InvoiceCreateRequest,
    PaymentRequest,
    PaymentVoidRequest,
    ReasonConfirmRequest,
    ReasonRequest,
    RefundCompleteRequest,
    RefundRequest,
)
from app.modules.tenancy.services import platform_directory
from app.modules.platform.services.audit import write_platform_audit
from app.modules.platform.services.billing import (
    REFUND_RESERVING_STATUSES,
    add_payment_event,
    add_subscription_event,
    create_invoice,
    find_payment_by_reference,
    invoice_paid_total,
    normalize_reference,
    refresh_invoice_refunded,
    serialize_invoice,
    serialize_payment,
)
from app.modules.platform.services.common import (
    page_params,
    paginated,
    require_confirm,
    require_reason,
    now_utc,
)
from app.modules.platform.services.settings import get_setting
from app.shared.errors import AppError

router = APIRouter(tags=["platform-billing"])

PAYMENT_METHODS = {
    "CASH",
    "BANK_TRANSFER",
    "CARD_TERMINAL",
    "ESEWA",
    "KHALTI",
    "OTHER",
}
LINE_KINDS = {"PLAN", "OVERAGE", "DISCOUNT", "ADJUSTMENT"}
REFUND_REASON_CODES = {
    "DUPLICATE",
    "SERVICE_FAILURE",
    "GOODWILL",
    "BILLING_ERROR",
    "OTHER",
}


def _invoice(db: Session, invoice_id: UUID) -> PlatformInvoice:
    row = db.get(PlatformInvoice, invoice_id)
    if row is None:
        raise AppError(404, "INVOICE_NOT_FOUND", "Not found", "Invoice not found.")
    return row


def _payment(db: Session, payment_id: UUID) -> PlatformPayment:
    row = db.get(PlatformPayment, payment_id)
    if row is None:
        raise AppError(404, "PAYMENT_NOT_FOUND", "Not found", "Payment not found.")
    return row


def _idempotency_key(value: str | None) -> str:
    key = (value or "").strip()
    if not 8 <= len(key) <= 120:
        raise AppError(
            422,
            "IDEMPOTENCY_KEY_REQUIRED",
            "Invalid input",
            "Idempotency-Key header is required (8-120 characters).",
        )
    return key


def _require_idempotent(
    db: Session, key: str, kind: str
) -> PlatformPayment | None:
    return db.scalar(
        select(PlatformPayment).where(
            PlatformPayment.idempotency_key == key,
            PlatformPayment.kind == kind,
        )
    )


# ---------------------------------------------------------------------------
# Invoices
# ---------------------------------------------------------------------------


@router.get("/invoices")
def list_invoices(
    tenant_id: UUID | None = None,
    status_filter: str | None = Query(default=None, alias="status"),
    from_: datetime | None = Query(default=None, alias="from"),
    to: datetime | None = None,
    page: int = 1,
    page_size: int = 25,
    actor: PlatformActor = Depends(require_platform_permission("invoice.view")),
    db: Session = Depends(get_db),
) -> dict:
    page, page_size = page_params(page, page_size)
    query = select(PlatformInvoice)
    if tenant_id:
        query = query.where(PlatformInvoice.restaurant_id == tenant_id)
    if status_filter:
        query = query.where(PlatformInvoice.status == status_filter)
    if from_:
        query = query.where(PlatformInvoice.issued_at >= from_)
    if to:
        query = query.where(PlatformInvoice.issued_at <= to)
    total = int(db.scalar(select(func.count()).select_from(query.subquery())) or 0)
    rows = db.scalars(
        query.order_by(PlatformInvoice.created_at.desc())
        .limit(page_size)
        .offset((page - 1) * page_size)
    ).all()
    items = []
    for row in rows:
        data = serialize_invoice(db, row, include_lines=False)
        tenant = platform_directory.get_tenant(db, row.restaurant_id)
        data["tenant_name"] = tenant["name"] if tenant else None
        data["tenant_slug"] = tenant["slug"] if tenant else None
        items.append(data)
    return paginated(items, total, page, page_size)


@router.post("/invoices", status_code=status.HTTP_201_CREATED)
def issue_invoice(
    payload: InvoiceCreateRequest,
    request: Request,
    actor: PlatformActor = Depends(require_platform_permission("invoice.manage")),
    _: PlatformActor = Depends(require_platform_step_up),
    db: Session = Depends(get_db),
) -> dict:
    reason = require_reason(payload.reason)
    try:
        tenant_id = UUID(payload.restaurant_id)
    except ValueError as exc:
        raise AppError(422, "INVALID_TENANT", "Invalid input", "Invalid tenant id.") from exc
    tenant = platform_directory.require_tenant(db, tenant_id)

    subscription = None
    if payload.subscription_id:
        try:
            subscription_id = UUID(payload.subscription_id)
        except ValueError as exc:
            raise AppError(422, "INVALID_SUBSCRIPTION", "Invalid input", "Invalid subscription id.") from exc
        subscription = db.get(PlatformSubscription, subscription_id)
        if subscription is None or subscription.restaurant_id != tenant_id:
            raise AppError(404, "SUBSCRIPTION_NOT_FOUND", "Not found", "Subscription not found.")

    lines = []
    for line in payload.lines:
        kind = line.kind.upper()
        if kind not in LINE_KINDS:
            raise AppError(422, "INVALID_LINE_KIND", "Invalid input", f"Unknown line kind {kind}.")
        if kind == "DISCOUNT":
            raise AppError(
                422,
                "INVALID_LINE_KIND",
                "Invalid input",
                "Use the invoice discount field for discounts.",
            )
        lines.append(
            {
                "kind": kind,
                "description": line.description,
                "quantity": line.quantity,
                "unit_amount_minor": line.unit_amount_minor,
            }
        )

    invoice = create_invoice(
        db,
        tenant=tenant,
        subscription=subscription,
        lines=lines,
        due_at=payload.due_at,
        currency_code=payload.currency_code.upper(),
        notes=payload.notes,
        discount_minor=payload.discount_minor,
        admin_id=actor.admin_id,
    )
    write_platform_audit(
        db,
        action="INVOICE_CREATED",
        entity_type="platform_invoice",
        entity_id=str(invoice.id),
        actor_admin_id=actor.admin_id,
        actor_email=actor.email,
        restaurant_id=tenant_id,
        reason=reason,
        request=request,
        after={
            "invoice_number": invoice.invoice_number,
            "total_minor": invoice.total_minor,
            "currency_code": invoice.currency_code,
        },
    )
    db.commit()
    return serialize_invoice(db, invoice)


@router.get("/invoices/{invoice_id}")
def get_invoice(
    invoice_id: UUID,
    actor: PlatformActor = Depends(require_platform_permission("invoice.view")),
    db: Session = Depends(get_db),
) -> dict:
    invoice = _invoice(db, invoice_id)
    data = serialize_invoice(db, invoice)
    data["tenant"] = platform_directory.get_tenant(db, invoice.restaurant_id)
    payments = db.scalars(
        select(PlatformPayment)
        .where(PlatformPayment.invoice_id == invoice.id)
        .order_by(PlatformPayment.created_at.desc())
    ).all()
    data["payments"] = [serialize_payment(row) for row in payments]
    events = db.scalars(
        select(PlatformPaymentEvent)
        .where(PlatformPaymentEvent.invoice_id == invoice.id)
        .order_by(PlatformPaymentEvent.created_at.desc())
    ).all()
    data["payment_events"] = [
        {
            "id": event.id,
            "payment_id": event.payment_id,
            "event_type": event.event_type,
            "amount_minor": event.amount_minor,
            "currency_code": event.currency_code,
            "actor_admin_id": event.actor_admin_id,
            "reason": event.reason,
            "metadata": event.metadata_json,
            "created_at": event.created_at,
        }
        for event in events
    ]
    data["second_approval_policy"] = "DEFERRED"
    return data


@router.get("/invoices/{invoice_id}/payment-instructions")
def payment_instructions(
    invoice_id: UUID,
    actor: PlatformActor = Depends(require_platform_permission("invoice.view")),
    db: Session = Depends(get_db),
) -> dict:
    invoice = _invoice(db, invoice_id)
    return {
        "invoice_number": invoice.invoice_number,
        "amount_minor": max(0, invoice.total_minor - invoice.refunded_amount_minor),
        "currency_code": invoice.currency_code,
        "due_at": invoice.due_at,
        "instructions_text": get_setting(db, "platform.payment.instructions_text", "") or "",
        "qr_image_ref": get_setting(db, "platform.payment.qr_image_ref", "") or "",
        "reference_to_quote": invoice.invoice_number,
    }


@router.post("/invoices/{invoice_id}/void")
def void_invoice(
    invoice_id: UUID,
    payload: ReasonConfirmRequest,
    request: Request,
    actor: PlatformActor = Depends(require_platform_permission("invoice.manage")),
    _: PlatformActor = Depends(require_platform_step_up),
    db: Session = Depends(get_db),
) -> dict:
    reason = require_reason(payload.reason)
    invoice = _invoice(db, invoice_id)
    require_confirm(payload.confirm, invoice.invoice_number)
    if invoice.status == "VOID":
        raise AppError(409, "INVOICE_ALREADY_VOID", "Conflict", "Invoice is already void.")
    if invoice.status == "PAID":
        raise AppError(
            409, "INVOICE_ALREADY_PAID", "Conflict", "Paid invoices must be refunded, not voided."
        )
    if invoice.status not in ("DRAFT", "OPEN", "OVERDUE"):
        raise AppError(
            409, "INVALID_STATUS_TRANSITION", "Conflict", "This invoice cannot be voided."
        )
    before = invoice.status
    invoice.status = "VOID"
    invoice.voided_at = now_utc()
    invoice.void_reason = reason
    invoice.updated_at = now_utc()
    write_platform_audit(
        db,
        action="INVOICE_VOIDED",
        entity_type="platform_invoice",
        entity_id=str(invoice.id),
        actor_admin_id=actor.admin_id,
        actor_email=actor.email,
        restaurant_id=invoice.restaurant_id,
        reason=reason,
        request=request,
        before={"status": before},
        after={"status": "VOID"},
    )
    db.commit()
    return serialize_invoice(db, invoice)


@router.post("/invoices/{invoice_id}/pay")
def pay_invoice(
    invoice_id: UUID,
    payload: PaymentRequest,
    request: Request,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    actor: PlatformActor = Depends(require_platform_permission("payment.confirm")),
    _: PlatformActor = Depends(require_platform_step_up),
    db: Session = Depends(get_db),
) -> dict:
    reason = require_reason(payload.reason)
    key = _idempotency_key(idempotency_key)
    existing = _require_idempotent(db, key, "PAYMENT")
    if existing is not None:
        invoice = _invoice(db, existing.invoice_id)
        return {
            "payment": serialize_payment(existing),
            "invoice": serialize_invoice(db, invoice),
            "subscription": None,
            "payment_event_id": None,
            "audit_id": None,
        }

    invoice = _invoice(db, invoice_id)
    if invoice.status == "PAID" or invoice.status == "REFUNDED":
        raise AppError(409, "INVOICE_ALREADY_PAID", "Conflict", "Invoice is already paid.")
    if invoice.status == "VOID":
        raise AppError(409, "INVOICE_VOID", "Conflict", "Invoice is void.")
    if invoice.status not in ("OPEN", "OVERDUE", "DRAFT"):
        raise AppError(
            409, "INVALID_STATUS_TRANSITION", "Conflict", "Invoice cannot be paid in this state."
        )

    method = payload.method.upper()
    if method not in PAYMENT_METHODS:
        raise AppError(422, "INVALID_PAYMENT_METHOD", "Invalid input", "Unknown payment method.")
    if not payload.provider_reference and method != "CASH":
        raise AppError(
            422,
            "PAYMENT_REFERENCE_REQUIRED",
            "Invalid input",
            "A verifiable transaction reference is required.",
        )
    if method == "CASH" and not payload.provider_reference and not (payload.exception_reason or "").strip():
        raise AppError(
            422,
            "PAYMENT_REFERENCE_REQUIRED",
            "Invalid input",
            "Cash without a reference needs an audited exception reason.",
        )
    if payload.evidence_ref and payload.evidence_ref.lower().startswith(("http://", "https://")):
        raise AppError(
            422,
            "EVIDENCE_TYPE_INVALID",
            "Invalid input",
            "Evidence must be a private object key, never a public URL.",
        )

    normalized = normalize_reference(payload.reference)
    if find_payment_by_reference(db, normalized) is not None:
        raise AppError(
            409, "PAYMENT_REFERENCE_EXISTS", "Conflict", "That payment reference is already recorded."
        )

    now = now_utc()
    payment = PlatformPayment(
        invoice_id=invoice.id,
        restaurant_id=invoice.restaurant_id,
        kind="PAYMENT",
        amount_minor=invoice.total_minor,
        currency_code=invoice.currency_code,
        method=method,
        reference=payload.reference.strip(),
        normalized_reference=normalized,
        provider="MANUAL",
        provider_reference=payload.provider_reference,
        evidence_type=payload.evidence_type,
        evidence_ref=payload.evidence_ref,
        exception_reason=payload.exception_reason,
        status="CONFIRMED",
        paid_at=payload.paid_at or now,
        recorded_by_admin_id=actor.admin_id,
        confirmed_by_admin_id=actor.admin_id,
        confirmed_at=now,
        idempotency_key=key,
    )
    db.add(payment)
    db.flush()
    add_payment_event(
        db,
        payment=payment,
        event_type="payment_created",
        reason=reason,
        admin_id=actor.admin_id,
    )
    event = add_payment_event(
        db,
        payment=payment,
        event_type="payment_confirmed",
        reason=reason,
        admin_id=actor.admin_id,
        metadata={"method": method, "reference": normalized},
    )

    paid_total = invoice_paid_total(db, invoice.id)
    if paid_total >= invoice.total_minor:
        invoice.status = "PAID"
        invoice.paid_at = payment.paid_at
    invoice.updated_at = now

    subscription = db.scalar(
        select(PlatformSubscription).where(
            PlatformSubscription.restaurant_id == invoice.restaurant_id,
            PlatformSubscription.status.in_(("TRIALING", "ACTIVE", "PAST_DUE", "GRACE")),
        )
    )
    if subscription is not None and subscription.status == "TRIALING":
        previous = subscription.status
        subscription.status = "ACTIVE"
        subscription.updated_at = now
        add_subscription_event(
            db,
            subscription,
            event_type="PAYMENT_RECORDED",
            admin_id=actor.admin_id,
            reason=reason,
            from_status=previous,
            to_status="ACTIVE",
            metadata={"invoice_number": invoice.invoice_number},
        )
    elif subscription is not None:
        add_subscription_event(
            db,
            subscription,
            event_type="PAYMENT_RECORDED",
            admin_id=actor.admin_id,
            reason=reason,
            to_status=subscription.status,
            metadata={"invoice_number": invoice.invoice_number},
        )

    audit = write_platform_audit(
        db,
        action="PAYMENT_RECORDED",
        entity_type="platform_payment",
        entity_id=str(payment.id),
        actor_admin_id=actor.admin_id,
        actor_email=actor.email,
        restaurant_id=invoice.restaurant_id,
        reason=reason,
        request=request,
        after={
            "invoice_number": invoice.invoice_number,
            "amount_minor": payment.amount_minor,
            "method": method,
            "reference": normalized,
        },
    )
    db.commit()
    return {
        "payment": serialize_payment(payment),
        "invoice": serialize_invoice(db, invoice),
        "subscription": {
            "id": subscription.id,
            "status": subscription.status,
            "current_period_end": subscription.current_period_end,
        }
        if subscription
        else None,
        "payment_event_id": event.id,
        "audit_id": audit.id,
    }


# ---------------------------------------------------------------------------
# Payments
# ---------------------------------------------------------------------------


@router.get("/payments")
def list_payments(
    tenant_id: UUID | None = None,
    status_filter: str | None = Query(default=None, alias="status"),
    kind: str | None = None,
    from_: datetime | None = Query(default=None, alias="from"),
    to: datetime | None = None,
    page: int = 1,
    page_size: int = 25,
    actor: PlatformActor = Depends(require_platform_permission("invoice.view")),
    db: Session = Depends(get_db),
) -> dict:
    page, page_size = page_params(page, page_size)
    query = select(PlatformPayment)
    if tenant_id:
        query = query.where(PlatformPayment.restaurant_id == tenant_id)
    if status_filter:
        query = query.where(PlatformPayment.status == status_filter)
    if kind:
        query = query.where(PlatformPayment.kind == kind.upper())
    if from_:
        query = query.where(PlatformPayment.created_at >= from_)
    if to:
        query = query.where(PlatformPayment.created_at <= to)
    total = int(db.scalar(select(func.count()).select_from(query.subquery())) or 0)
    rows = db.scalars(
        query.order_by(PlatformPayment.created_at.desc())
        .limit(page_size)
        .offset((page - 1) * page_size)
    ).all()
    items = []
    for row in rows:
        data = serialize_payment(row)
        tenant = platform_directory.get_tenant(db, row.restaurant_id)
        invoice = db.get(PlatformInvoice, row.invoice_id)
        data["tenant_name"] = tenant["name"] if tenant else None
        data["invoice_number"] = invoice.invoice_number if invoice else None
        items.append(data)
    return paginated(items, total, page, page_size)


@router.get("/payments/{payment_id}")
def get_payment(
    payment_id: UUID,
    actor: PlatformActor = Depends(require_platform_permission("invoice.view")),
    db: Session = Depends(get_db),
) -> dict:
    payment = _payment(db, payment_id)
    data = serialize_payment(payment)
    data["tenant"] = platform_directory.get_tenant(db, payment.restaurant_id)
    invoice = db.get(PlatformInvoice, payment.invoice_id)
    data["invoice"] = serialize_invoice(db, invoice, include_lines=False) if invoice else None
    events = db.scalars(
        select(PlatformPaymentEvent)
        .where(PlatformPaymentEvent.payment_id == payment.id)
        .order_by(PlatformPaymentEvent.created_at.desc())
    ).all()
    data["events"] = [
        {
            "id": event.id,
            "event_type": event.event_type,
            "amount_minor": event.amount_minor,
            "currency_code": event.currency_code,
            "actor_admin_id": event.actor_admin_id,
            "reason": event.reason,
            "metadata": event.metadata_json,
            "created_at": event.created_at,
        }
        for event in events
    ]
    if payment.refund_of_payment_id:
        original = db.get(PlatformPayment, payment.refund_of_payment_id)
        data["original_payment"] = serialize_payment(original) if original else None
    return data


@router.get("/payments/{payment_id}/events")
def payment_events(
    payment_id: UUID,
    actor: PlatformActor = Depends(require_platform_permission("invoice.view")),
    db: Session = Depends(get_db),
) -> dict:
    _payment(db, payment_id)
    rows = db.scalars(
        select(PlatformPaymentEvent)
        .where(PlatformPaymentEvent.payment_id == payment_id)
        .order_by(PlatformPaymentEvent.created_at.asc())
    ).all()
    return {
        "items": [
            {
                "id": row.id,
                "event_type": row.event_type,
                "amount_minor": row.amount_minor,
                "currency_code": row.currency_code,
                "actor_admin_id": row.actor_admin_id,
                "reason": row.reason,
                "metadata": row.metadata_json,
                "created_at": row.created_at,
            }
            for row in rows
        ]
    }


@router.post("/payments/{payment_id}/void")
def void_payment(
    payment_id: UUID,
    payload: PaymentVoidRequest,
    request: Request,
    actor: PlatformActor = Depends(require_platform_permission("payment.void")),
    _: PlatformActor = Depends(require_platform_step_up),
    db: Session = Depends(get_db),
) -> dict:
    reason = require_reason(payload.reason)
    payment = _payment(db, payment_id)
    require_confirm(payload.confirm, payment.reference)
    if payment.kind != "PAYMENT":
        raise AppError(409, "PAYMENT_IMMUTABLE", "Conflict", "Only payments can be voided.")
    if payment.status != "CONFIRMED":
        raise AppError(
            409, "INVALID_STATUS_TRANSITION", "Conflict", "Only a confirmed payment can be voided."
        )
    invoice = _invoice(db, payment.invoice_id)
    if invoice.refunded_amount_minor > 0 or invoice.status == "REFUNDED":
        raise AppError(
            409, "PAYMENT_IMMUTABLE", "Conflict", "A payment with refunds cannot be voided."
        )
    payment.status = "VOIDED"
    payment.voided_at = now_utc()
    payment.void_reason = reason
    payment.updated_at = now_utc()
    add_payment_event(
        db,
        payment=payment,
        event_type="payment_voided",
        reason=reason,
        admin_id=actor.admin_id,
    )
    db.flush()
    paid_total = invoice_paid_total(db, invoice.id)
    if invoice.status == "PAID" and paid_total < invoice.total_minor:
        invoice.status = "OPEN"
        invoice.paid_at = None
    invoice.updated_at = now_utc()
    audit = write_platform_audit(
        db,
        action="PAYMENT_VOIDED",
        entity_type="platform_payment",
        entity_id=str(payment.id),
        actor_admin_id=actor.admin_id,
        actor_email=actor.email,
        restaurant_id=payment.restaurant_id,
        reason=reason,
        request=request,
        before={"status": "CONFIRMED"},
        after={"status": "VOIDED"},
    )
    db.commit()
    return {
        "payment": serialize_payment(payment),
        "invoice": serialize_invoice(db, invoice),
        "audit_id": audit.id,
    }


# ---------------------------------------------------------------------------
# Refunds
# ---------------------------------------------------------------------------


def _reserved_refund_total(db: Session, original: PlatformPayment) -> int:
    value = db.scalar(
        select(func.coalesce(func.sum(PlatformPayment.amount_minor), 0)).where(
            PlatformPayment.kind == "REFUND",
            PlatformPayment.refund_of_payment_id == original.id,
            PlatformPayment.status.in_(REFUND_RESERVING_STATUSES),
        )
    )
    return int(value or 0)


@router.post("/payments/{payment_id}/refund", status_code=status.HTTP_201_CREATED)
def request_refund(
    payment_id: UUID,
    payload: RefundRequest,
    request: Request,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    actor: PlatformActor = Depends(require_platform_permission("payment.refund.request")),
    _: PlatformActor = Depends(require_platform_step_up),
    db: Session = Depends(get_db),
) -> dict:
    reason = require_reason(payload.reason)
    key = _idempotency_key(idempotency_key)
    existing = _require_idempotent(db, key, "REFUND")
    if existing is not None:
        return {
            "refund": serialize_payment(existing),
            "second_approval_policy": "DEFERRED",
            "single_admin_approval": False,
        }

    original = _payment(db, payment_id)
    if original.kind != "PAYMENT" or original.status != "CONFIRMED":
        raise AppError(
            409, "REFUND_NOT_PENDING", "Conflict", "Only a confirmed payment can be refunded."
        )
    if normalize_reference(payload.original_reference) != original.normalized_reference:
        raise AppError(
            422,
            "ORIGINAL_REFERENCE_REQUIRED",
            "Invalid input",
            "The original payment reference does not match.",
        )
    if not payload.destination.strip():
        raise AppError(
            422, "REFUND_DESTINATION_REQUIRED", "Invalid input", "A refund destination is required."
        )
    if payload.reason_code.upper() not in REFUND_REASON_CODES:
        raise AppError(422, "INVALID_REASON_CODE", "Invalid input", "Unknown refund reason code.")

    reserved = _reserved_refund_total(db, original)
    available = original.amount_minor - reserved
    if available <= 0:
        raise AppError(409, "ALREADY_REFUNDED", "Conflict", "This payment is fully refunded.")
    if payload.amount_minor > available:
        raise AppError(
            409,
            "REFUND_EXCEEDS_PAID",
            "Conflict",
            f"Refund exceeds the refundable amount ({available} minor units).",
        )

    now = now_utc()
    refund = PlatformPayment(
        invoice_id=original.invoice_id,
        restaurant_id=original.restaurant_id,
        kind="REFUND",
        amount_minor=payload.amount_minor,
        currency_code=original.currency_code,
        method=original.method,
        reference=f"REFUND-{original.reference}"[:120],
        normalized_reference=None,
        provider="MANUAL",
        status="REFUND_PENDING",
        refund_of_payment_id=original.id,
        refund_original_reference=original.reference,
        refund_destination=payload.destination,
        refund_requested_by_admin_id=actor.admin_id,
        refund_requested_at=now,
        refund_reason_code=payload.reason_code.upper(),
        refund_reason_note=reason,
        refund_processed_outside_platform=payload.processed_outside_platform,
        evidence_type=payload.evidence_type,
        evidence_ref=payload.evidence_ref,
        idempotency_key=key,
    )
    db.add(refund)
    db.flush()
    single = original.confirmed_by_admin_id == actor.admin_id
    add_payment_event(
        db,
        payment=refund,
        event_type="refund_requested",
        reason=reason,
        admin_id=actor.admin_id,
        metadata={
            "original_payment_id": str(original.id),
            "original_reference": original.reference,
            "destination": payload.destination,
            "single_admin_approval": single,
            "second_approval_policy": "DEFERRED",
        },
    )
    write_platform_audit(
        db,
        action="REFUND_REQUESTED",
        entity_type="platform_payment",
        entity_id=str(refund.id),
        actor_admin_id=actor.admin_id,
        actor_email=actor.email,
        restaurant_id=refund.restaurant_id,
        reason=reason,
        request=request,
        after={
            "amount_minor": refund.amount_minor,
            "original_reference": original.reference,
            "destination": payload.destination,
        },
    )
    db.commit()
    return {
        "refund": serialize_payment(refund),
        "second_approval_policy": "DEFERRED",
        "single_admin_approval": single,
    }


@router.get("/refunds")
def list_refunds(
    status_filter: str | None = Query(default=None, alias="status"),
    tenant_id: UUID | None = None,
    page: int = 1,
    page_size: int = 25,
    actor: PlatformActor = Depends(require_platform_permission("invoice.view")),
    db: Session = Depends(get_db),
) -> dict:
    page, page_size = page_params(page, page_size)
    query = select(PlatformPayment).where(PlatformPayment.kind == "REFUND")
    if status_filter:
        query = query.where(PlatformPayment.status == status_filter)
    if tenant_id:
        query = query.where(PlatformPayment.restaurant_id == tenant_id)
    total = int(db.scalar(select(func.count()).select_from(query.subquery())) or 0)
    rows = db.scalars(
        query.order_by(PlatformPayment.created_at.desc())
        .limit(page_size)
        .offset((page - 1) * page_size)
    ).all()
    items = []
    for row in rows:
        data = serialize_payment(row)
        tenant = platform_directory.get_tenant(db, row.restaurant_id)
        data["tenant_name"] = tenant["name"] if tenant else None
        data["single_admin_approval"] = (
            row.refund_approved_by_admin_id is not None
            and row.refund_approved_by_admin_id == row.refund_requested_by_admin_id
        )
        items.append(data)
    return {
        **paginated(items, total, page, page_size),
        "second_approval_policy": "DEFERRED",
    }


def _refund(db: Session, refund_id: UUID) -> PlatformPayment:
    row = db.get(PlatformPayment, refund_id)
    if row is None or row.kind != "REFUND":
        raise AppError(404, "REFUND_NOT_FOUND", "Not found", "Refund not found.")
    return row


@router.post("/refunds/{refund_id}/approve")
def approve_refund(
    refund_id: UUID,
    payload: ReasonRequest,
    request: Request,
    actor: PlatformActor = Depends(require_platform_permission("payment.refund.approve")),
    _: PlatformActor = Depends(require_platform_step_up),
    db: Session = Depends(get_db),
) -> dict:
    reason = require_reason(payload.reason)
    refund = _refund(db, refund_id)
    if refund.status != "REFUND_PENDING":
        raise AppError(409, "REFUND_NOT_PENDING", "Conflict", "Refund is not pending approval.")
    now = now_utc()
    refund.status = "REFUND_APPROVED"
    refund.refund_approved_by_admin_id = actor.admin_id
    refund.refund_approved_at = now
    refund.updated_at = now
    single = refund.refund_requested_by_admin_id == actor.admin_id
    add_payment_event(
        db,
        payment=refund,
        event_type="refund_approved",
        reason=reason,
        admin_id=actor.admin_id,
        metadata={"single_admin_approval": single},
    )
    write_platform_audit(
        db,
        action="REFUND_APPROVED",
        entity_type="platform_payment",
        entity_id=str(refund.id),
        actor_admin_id=actor.admin_id,
        actor_email=actor.email,
        restaurant_id=refund.restaurant_id,
        reason=reason,
        request=request,
        after={"status": "REFUND_APPROVED", "single_admin_approval": single},
    )
    db.commit()
    return {**serialize_payment(refund), "single_admin_approval": single}


@router.post("/refunds/{refund_id}/reject")
def reject_refund(
    refund_id: UUID,
    payload: ReasonRequest,
    request: Request,
    actor: PlatformActor = Depends(require_platform_permission("payment.refund.approve")),
    _: PlatformActor = Depends(require_platform_step_up),
    db: Session = Depends(get_db),
) -> dict:
    reason = require_reason(payload.reason)
    refund = _refund(db, refund_id)
    if refund.status != "REFUND_PENDING":
        raise AppError(409, "REFUND_NOT_PENDING", "Conflict", "Refund is not pending approval.")
    refund.status = "REJECTED"
    refund.refund_rejected_reason = reason
    refund.updated_at = now_utc()
    add_payment_event(
        db,
        payment=refund,
        event_type="refund_rejected",
        reason=reason,
        admin_id=actor.admin_id,
    )
    write_platform_audit(
        db,
        action="REFUND_REJECTED",
        entity_type="platform_payment",
        entity_id=str(refund.id),
        actor_admin_id=actor.admin_id,
        actor_email=actor.email,
        restaurant_id=refund.restaurant_id,
        reason=reason,
        request=request,
        after={"status": "REJECTED"},
    )
    db.commit()
    return serialize_payment(refund)


@router.post("/refunds/{refund_id}/complete")
def complete_refund(
    refund_id: UUID,
    payload: RefundCompleteRequest,
    request: Request,
    actor: PlatformActor = Depends(require_platform_permission("payment.refund.complete")),
    _: PlatformActor = Depends(require_platform_step_up),
    db: Session = Depends(get_db),
) -> dict:
    reason = require_reason(payload.reason)
    refund = _refund(db, refund_id)
    if refund.status != "REFUND_APPROVED":
        raise AppError(409, "REFUND_NOT_APPROVED", "Conflict", "Approve the refund first.")
    if not payload.external_reference.strip():
        raise AppError(
            422,
            "EXTERNAL_REFUND_REFERENCE_REQUIRED",
            "Invalid input",
            "The external refund reference is required.",
        )
    now = now_utc()
    refund.status = "REFUNDED"
    refund.refund_completed_by_admin_id = actor.admin_id
    refund.refund_completed_at = payload.completed_at or now
    refund.refund_external_reference = payload.external_reference.strip()
    refund.refund_processed_outside_platform = payload.processed_outside_platform
    if payload.destination:
        refund.refund_destination = payload.destination
    refund.updated_at = now
    add_payment_event(
        db,
        payment=refund,
        event_type="refund_completed",
        reason=reason,
        admin_id=actor.admin_id,
        metadata={"external_reference": refund.refund_external_reference},
    )
    db.flush()
    invoice = _invoice(db, refund.invoice_id)
    refresh_invoice_refunded(db, invoice)
    write_platform_audit(
        db,
        action="REFUND_COMPLETED",
        entity_type="platform_payment",
        entity_id=str(refund.id),
        actor_admin_id=actor.admin_id,
        actor_email=actor.email,
        restaurant_id=refund.restaurant_id,
        reason=reason,
        request=request,
        after={
            "status": "REFUNDED",
            "external_reference": refund.refund_external_reference,
            "refunded_amount_minor": invoice.refunded_amount_minor,
        },
    )
    db.commit()
    return {
        "refund": serialize_payment(refund),
        "invoice": serialize_invoice(db, invoice),
    }
