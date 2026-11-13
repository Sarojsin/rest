"""Platform invoicing and payment ledger helpers (plan 04 §1.7–1.11).

All money is integer minor units. Invoice numbers are allocated under a
per-fiscal-year row lock; confirmed payments and the payment event ledger are
never updated or deleted by these helpers.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.modules.platform.models import (
    PlatformInvoice,
    PlatformInvoiceLine,
    PlatformInvoiceSequence,
    PlatformPayment,
    PlatformPaymentEvent,
    PlatformPlan,
    PlatformPlanVersion,
    PlatformSubscription,
    PlatformSubscriptionEvent,
)
from app.modules.platform.services.common import now_utc
from app.modules.platform.services.settings import get_setting
from app.shared.errors import AppError

PAYMENT_STATUSES = (
    "CONFIRMED",
    "REFUND_PENDING",
    "REFUND_APPROVED",
    "REFUNDED",
)
REFUND_RESERVING_STATUSES = ("REFUND_PENDING", "REFUND_APPROVED", "REFUNDED")


def fiscal_year_label(issued_at: datetime, start_month: int) -> str:
    """Return the fiscal-year label used in invoice numbers.

    The default (start month 7, Nepal) is rendered in Bikram Sambat because
    that is the accounting label operators expect; other start months use the
    Gregorian fiscal year. The mapping is intentionally simple and documented:
    a full BS calendar conversion is out of PA-1 scope.
    """
    if start_month == 7:
        # BS is Gregorian + 56 until mid-year, + 57 after Shrawan.
        return str(issued_at.year + (57 if issued_at.month >= 7 else 56))
    fy_start = issued_at.year if issued_at.month >= start_month else issued_at.year - 1
    return str(fy_start)


def allocate_invoice_number(
    db: Session, *, issued_at: datetime, prefix: str
) -> tuple[str, str, int]:
    start_month = int(get_setting(db, "platform.fiscal_year_start_month", 7) or 7)
    fiscal_year = fiscal_year_label(issued_at, start_month)

    bind = db.get_bind()
    if bind.dialect.name == "postgresql":
        db.execute(
            pg_insert(PlatformInvoiceSequence)
            .values(fiscal_year=fiscal_year, next_sequence=1, updated_at=now_utc())
            .on_conflict_do_nothing(index_elements=["fiscal_year"])
        )
    row = db.execute(
        select(PlatformInvoiceSequence)
        .where(PlatformInvoiceSequence.fiscal_year == fiscal_year)
        .with_for_update()
    ).scalar_one_or_none()
    if row is None:
        row = PlatformInvoiceSequence(
            fiscal_year=fiscal_year, next_sequence=1, updated_at=now_utc()
        )
        db.add(row)
        db.flush()

    sequence = int(row.next_sequence)
    row.next_sequence = sequence + 1
    row.updated_at = now_utc()
    number = f"{prefix}-{fiscal_year}-{sequence:06d}"
    return number, fiscal_year, sequence


def invoice_paid_total(db: Session, invoice_id: UUID) -> int:
    value = db.scalar(
        select(func.coalesce(func.sum(PlatformPayment.amount_minor), 0)).where(
            PlatformPayment.invoice_id == invoice_id,
            PlatformPayment.kind == "PAYMENT",
            PlatformPayment.status == "CONFIRMED",
        )
    )
    return int(value or 0)


def invoice_refunded_total(db: Session, invoice_id: UUID) -> int:
    value = db.scalar(
        select(func.coalesce(func.sum(PlatformPayment.amount_minor), 0)).where(
            PlatformPayment.invoice_id == invoice_id,
            PlatformPayment.kind == "REFUND",
            PlatformPayment.status.in_(REFUND_RESERVING_STATUSES),
        )
    )
    return int(value or 0)


def refresh_invoice_refunded(db: Session, invoice: PlatformInvoice) -> None:
    refunded = invoice_refunded_total(db, invoice.id)
    invoice.refunded_amount_minor = refunded
    if invoice.status == "PAID" and refunded >= invoice.total_minor > 0:
        invoice.status = "REFUNDED"
    elif invoice.status == "REFUNDED" and refunded < invoice.total_minor:
        invoice.status = "PAID"
    invoice.updated_at = now_utc()


def recalculate_invoice(db: Session, invoice: PlatformInvoice) -> None:
    subtotal = db.scalar(
        select(func.coalesce(func.sum(PlatformInvoiceLine.amount_minor), 0)).where(
            PlatformInvoiceLine.invoice_id == invoice.id
        )
    )
    invoice.subtotal_minor = int(subtotal or 0)
    invoice.total_minor = max(0, invoice.subtotal_minor - invoice.discount_minor)
    invoice.updated_at = now_utc()


def create_invoice(
    db: Session,
    *,
    tenant: dict,
    subscription: PlatformSubscription | None,
    lines: list[dict],
    due_at: datetime,
    currency_code: str,
    notes: str | None,
    discount_minor: int,
    admin_id: UUID,
) -> PlatformInvoice:
    issued_at = now_utc()
    prefix = str(get_setting(db, "platform.invoice_prefix", "INV") or "INV")
    number, fiscal_year, sequence = allocate_invoice_number(
        db, issued_at=issued_at, prefix=prefix
    )

    invoice = PlatformInvoice(
        invoice_number=number,
        fiscal_year=fiscal_year,
        sequence_number=sequence,
        restaurant_id=tenant["id"],
        subscription_id=subscription.id if subscription else None,
        status="OPEN",
        subtotal_minor=0,
        discount_minor=discount_minor,
        total_minor=0,
        refunded_amount_minor=0,
        currency_code=currency_code,
        issued_at=issued_at,
        due_at=due_at,
        invoice_type="PLATFORM_SUBSCRIPTION",
        issuer_name=get_setting(db, "platform.invoice.issuer_name", "") or "",
        issuer_address=get_setting(db, "platform.invoice.issuer_address", "") or None,
        issuer_pan=get_setting(db, "platform.invoice.issuer_pan", "") or None,
        issuer_vat_registered=bool(
            get_setting(db, "platform.invoice.issuer_vat_registered", False)
        ),
        issuer_vat_number=get_setting(db, "platform.invoice.issuer_vat_number", "") or None,
        buyer_name=tenant.get("legal_name") or tenant.get("name"),
        buyer_pan=None,
        buyer_address=None,
        tax_treatment=str(
            get_setting(db, "platform.invoice.tax_treatment", "UNCONFIRMED")
            or "UNCONFIRMED"
        ),
        tax_amount_minor=0,
        template_version=get_setting(
            db, "platform.invoice.default_template_version", "v1-unapproved"
        ),
        notes=notes,
        created_by_admin_id=admin_id,
    )
    db.add(invoice)
    db.flush()

    for index, line in enumerate(lines):
        amount = int(line["quantity"]) * int(line["unit_amount_minor"])
        db.add(
            PlatformInvoiceLine(
                invoice_id=invoice.id,
                kind=str(line.get("kind") or "PLAN"),
                description=str(line["description"])[:255],
                quantity=int(line["quantity"]),
                unit_amount_minor=int(line["unit_amount_minor"]),
                amount_minor=amount,
                sort_order=index,
            )
        )
    db.flush()
    recalculate_invoice(db, invoice)
    if invoice.total_minor <= 0:
        raise AppError(
            422, "INVALID_AMOUNT", "Invalid amount", "An invoice must have a positive total."
        )
    return invoice


def add_payment_event(
    db: Session,
    *,
    payment: PlatformPayment,
    event_type: str,
    reason: str,
    admin_id: UUID | None,
    metadata: dict | None = None,
) -> PlatformPaymentEvent:
    event = PlatformPaymentEvent(
        payment_id=payment.id,
        invoice_id=payment.invoice_id,
        restaurant_id=payment.restaurant_id,
        event_type=event_type,
        amount_minor=payment.amount_minor,
        currency_code=payment.currency_code,
        actor_admin_id=admin_id,
        reason=reason,
        metadata_json=metadata,
    )
    db.add(event)
    return event


def normalize_reference(reference: str) -> str:
    return " ".join(reference.strip().upper().split())


def find_payment_by_reference(
    db: Session, normalized: str
) -> PlatformPayment | None:
    return db.scalar(
        select(PlatformPayment).where(
            PlatformPayment.normalized_reference == normalized,
            PlatformPayment.status.in_(PAYMENT_STATUSES),
        )
    )


def serialize_payment(payment: PlatformPayment) -> dict:
    return {
        "id": payment.id,
        "invoice_id": payment.invoice_id,
        "tenant_id": payment.restaurant_id,
        "restaurant_id": payment.restaurant_id,
        "kind": payment.kind,
        "amount_minor": payment.amount_minor,
        "currency_code": payment.currency_code,
        "method": payment.method,
        "reference": payment.reference,
        "normalized_reference": payment.normalized_reference,
        "provider": payment.provider,
        "provider_reference": payment.provider_reference,
        "evidence_type": payment.evidence_type,
        "evidence_ref": payment.evidence_ref,
        "exception_reason": payment.exception_reason,
        "status": payment.status,
        "paid_at": payment.paid_at,
        "recorded_by_admin_id": payment.recorded_by_admin_id,
        "confirmed_by_admin_id": payment.confirmed_by_admin_id,
        "confirmed_at": payment.confirmed_at,
        "voided_at": payment.voided_at,
        "void_reason": payment.void_reason,
        "refund_of_payment_id": payment.refund_of_payment_id,
        "refund_original_reference": payment.refund_original_reference,
        "refund_destination": payment.refund_destination,
        "refund_requested_by_admin_id": payment.refund_requested_by_admin_id,
        "refund_requested_at": payment.refund_requested_at,
        "refund_reason_code": payment.refund_reason_code,
        "refund_reason_note": payment.refund_reason_note,
        "refund_approved_by_admin_id": payment.refund_approved_by_admin_id,
        "refund_approved_at": payment.refund_approved_at,
        "refund_completed_by_admin_id": payment.refund_completed_by_admin_id,
        "refund_completed_at": payment.refund_completed_at,
        "refund_external_reference": payment.refund_external_reference,
        "refund_processed_outside_platform": payment.refund_processed_outside_platform,
        "refund_rejected_reason": payment.refund_rejected_reason,
        "created_at": payment.created_at,
        "updated_at": payment.updated_at,
    }


def serialize_invoice(
    db: Session, invoice: PlatformInvoice, *, include_lines: bool = True
) -> dict:
    data: dict[str, Any] = {
        "id": invoice.id,
        "invoice_number": invoice.invoice_number,
        "fiscal_year": invoice.fiscal_year,
        "sequence_number": invoice.sequence_number,
        "tenant_id": invoice.restaurant_id,
        "restaurant_id": invoice.restaurant_id,
        "subscription_id": invoice.subscription_id,
        "status": invoice.status,
        "subtotal_minor": invoice.subtotal_minor,
        "discount_minor": invoice.discount_minor,
        "total_minor": invoice.total_minor,
        "refunded_amount_minor": invoice.refunded_amount_minor,
        "currency_code": invoice.currency_code,
        "issued_at": invoice.issued_at,
        "due_at": invoice.due_at,
        "paid_at": invoice.paid_at,
        "voided_at": invoice.voided_at,
        "void_reason": invoice.void_reason,
        "notes": invoice.notes,
        "invoice_type": invoice.invoice_type,
        "issuer_name": invoice.issuer_name,
        "issuer_address": invoice.issuer_address,
        "issuer_pan": invoice.issuer_pan,
        "issuer_vat_registered": invoice.issuer_vat_registered,
        "issuer_vat_number": invoice.issuer_vat_number,
        "buyer_name": invoice.buyer_name,
        "buyer_pan": invoice.buyer_pan,
        "buyer_address": invoice.buyer_address,
        "tax_treatment": invoice.tax_treatment,
        "tax_amount_minor": invoice.tax_amount_minor,
        "template_version": invoice.template_version,
        "created_at": invoice.created_at,
        "updated_at": invoice.updated_at,
        "paid_minor": invoice_paid_total(db, invoice.id),
    }
    if include_lines:
        lines = db.scalars(
            select(PlatformInvoiceLine)
            .where(PlatformInvoiceLine.invoice_id == invoice.id)
            .order_by(PlatformInvoiceLine.sort_order)
        ).all()
        data["lines"] = [
            {
                "id": line.id,
                "kind": line.kind,
                "description": line.description,
                "quantity": line.quantity,
                "unit_amount_minor": line.unit_amount_minor,
                "amount_minor": line.amount_minor,
                "sort_order": line.sort_order,
            }
            for line in lines
        ]
    return data


def period_end(start: datetime, interval: str) -> datetime:
    if interval == "ANNUAL":
        return start + timedelta(days=365)
    return start + timedelta(days=30)


def invoice_status_after_payment(invoice: PlatformInvoice, paid_total: int) -> str:
    if invoice.status in ("VOID", "REFUNDED"):
        return invoice.status
    if paid_total >= invoice.total_minor:
        return "PAID"
    return invoice.status


def add_subscription_event(
    db: Session,
    subscription: PlatformSubscription,
    *,
    event_type: str,
    admin_id: UUID | None,
    reason: str | None,
    from_status: str | None = None,
    to_status: str | None = None,
    metadata: dict | None = None,
):
    event = PlatformSubscriptionEvent(
        subscription_id=subscription.id,
        event_type=event_type,
        from_status=from_status,
        to_status=to_status,
        actor_admin_id=admin_id,
        reason=reason,
        metadata_json=metadata,
    )
    db.add(event)
    return event


def serialize_subscription(db: Session, subscription: PlatformSubscription) -> dict:
    plan = db.get(PlatformPlan, subscription.plan_id)
    events = db.scalars(
        select(PlatformSubscriptionEvent)
        .where(PlatformSubscriptionEvent.subscription_id == subscription.id)
        .order_by(PlatformSubscriptionEvent.created_at.desc())
        .limit(20)
    ).all()
    return {
        "id": subscription.id,
        "tenant_id": subscription.restaurant_id,
        "restaurant_id": subscription.restaurant_id,
        "plan_id": subscription.plan_id,
        "plan_code": plan.code if plan else None,
        "plan_name": plan.name if plan else None,
        "status": subscription.status,
        "trial_ends_at": subscription.trial_ends_at,
        "current_period_start": subscription.current_period_start,
        "current_period_end": subscription.current_period_end,
        "cancel_at_period_end": subscription.cancel_at_period_end,
        "canceled_at": subscription.canceled_at,
        "grace_ends_at": subscription.grace_ends_at,
        "price_snapshot_minor": subscription.price_snapshot_minor,
        "currency_snapshot": subscription.currency_snapshot,
        "billing_interval_snapshot": subscription.billing_interval_snapshot,
        "created_at": subscription.created_at,
        "updated_at": subscription.updated_at,
        "events": [
            {
                "id": event.id,
                "event_type": event.event_type,
                "from_status": event.from_status,
                "to_status": event.to_status,
                "actor_admin_id": event.actor_admin_id,
                "reason": event.reason,
                "metadata": event.metadata_json,
                "created_at": event.created_at,
            }
            for event in events
        ],
    }


def auto_renew_subscription(
    db: Session,
    *,
    subscription: PlatformSubscription,
    admin_id: UUID,
    reason: str = "Automatic renewal",
) -> PlatformInvoice:
    """Auto-generate an invoice on subscription renewal.

    This function:
    1. Creates an invoice for the upcoming billing period
    2. Sets the due date based on the billing interval
    3. Returns the created invoice
    """
    from app.modules.platform.models import PlatformInvoice, PlatformInvoiceLine

    # Determine billing interval and period
    if subscription.billing_interval_snapshot == "ANNUAL":
        period_days = 365
        prefix = "ANN"
    else:
        period_days = 30
        prefix = "MTH"

    from datetime import timedelta
    issued_at = datetime.now(UTC)
    due_at = issued_at + timedelta(days=15)  # 15-day payment window

    # Get the plan version for pricing
    plan_version = (
        db.execute(
            select(PlatformPlanVersion).where(
                PlatformPlanVersion.plan_id == subscription.plan_id,
                PlatformPlanVersion.is_active == True,
            )
        )
        .scalars()
        .first()
    )

    # Determine pricing
    if plan_version and subscription.billing_interval_snapshot == "ANNUAL":
        subtotal_minor = plan_version.price_annual_minor or 0
    elif plan_version:
        subtotal_minor = plan_version.price_monthly_minor or 0
    else:
        subtotal_minor = 0

    # Create the invoice
    invoice = PlatformInvoice(
        restaurant_id=subscription.restaurant_id,
        subscription_id=subscription.id,
        platform_plan_version_id=plan_version.id if plan_version else None,
        status="OPEN",
        billing_interval=subscription.billing_interval_snapshot,
        period_start=subscription.current_period_end,
        period_end=subscription.current_period_end + timedelta(days=period_days),
        due_date=due_at,
        subtotal_minor=subtotal_minor,
        discount_minor=0,
        total_minor=subtotal_minor,
        refunded_amount_minor=0,
        currency_code=subscription.currency_snapshot or "NPR",
        issued_at=issued_at,
        due_at=due_at,
        invoice_type="AUTO_RENEWAL",
        issuer_name=get_setting(db, "platform.invoice.issuer_name", "") or "",
        issuer_address=get_setting(db, "platform.invoice.issuer_address", "") or None,
        issuer_pan=get_setting(db, "platform.invoice.issuer_pan", "") or None,
        issuer_vat_registered=bool(
            get_setting(db, "platform.invoice.issuer_vat_registered", False)
        ),
        issuer_vat_number=get_setting(db, "platform.invoice.issuer_vat_number", "") or None,
        buyer_name="",
        buyer_pan=None,
        buyer_address=None,
        tax_treatment=str(
            get_setting(db, "platform.invoice.tax_treatment", "UNCONFIRMED") or "UNCONFIRMED"
        ),
        tax_amount_minor=0,
        template_version=get_setting(
            db, "platform.invoice.default_template_version", "v1-unapproved"
        ),
        notes=reason,
        created_by_admin_id=admin_id,
    )
    db.add(invoice)
    db.flush()

    # Add invoice line for the plan
    plan_row = db.get(PlatformPlan, subscription.plan_id)
    db.add(
        PlatformInvoiceLine(
            invoice_id=invoice.id,
            kind="PLAN",
            description=(
                f"{plan_row.name if plan_row else 'Plan'} subscription "
                f"({subscription.billing_interval_snapshot})"
            ),
            quantity=1,
            unit_amount_minor=subtotal_minor,
            amount_minor=subtotal_minor,
            sort_order=0,
        )
    )
    db.flush()
    recalculate_invoice(db, invoice)

    # Add payment event for invoice creation
    from app.modules.platform.models import PlatformPaymentEvent

    event = PlatformPaymentEvent(
        payment_id=None,
        invoice_id=invoice.id,
        restaurant_id=subscription.restaurant_id,
        event_type="INVOICE_CREATED",
        amount_minor=subtotal_minor,
        currency_code=subscription.currency_snapshot or "NPR",
        actor_admin_id=admin_id,
        reason=reason,
        metadata_json={"auto_renewed": True},
    )
    db.add(event)
    db.flush()

    return invoice


def check_grace_period(
    db: Session, *, restaurant_id: UUID, subscription: PlatformSubscription
) -> dict:
    """Check if a subscription is in grace period and return status.

    Returns:
        {
            "in_grace_period": bool,
            "grace_ends_at": datetime | None,
            "days_remaining": int,
            "should_suspend": bool,
        }
    """
    from datetime import datetime as dt_now

    now = dt_now.now(UTC)
    grace_ends = subscription.grace_ends_at

    if not grace_ends or now < grace_ends:
        days_remaining = max(0, int((grace_ends - now).total_seconds() / 86400)) if grace_ends else 0
        return {
            "in_grace_period": False,
            "grace_ends_at": grace_ends,
            "days_remaining": days_remaining,
            "should_suspend": False,
        }

    # Past grace period - subscription should be suspended
    return {
        "in_grace_period": True,
        "grace_ends_at": grace_ends,
        "days_remaining": 0,
        "should_suspend": True,
    }


def process_payment_webhook(
    db: Session,
    *,
    subscription_id: UUID,
    event_type: str,
    amount_minor: int | None = None,
    currency_code: str | None = None,
    payment_id: UUID | None = None,
    status: str = "pending",
    metadata: dict | None = None,
) -> dict:
    """Process a payment webhook event from a payment provider.

    Handles:
    - Payment confirmation
    - Invoice marking as paid
    - Grace period reset
    - Subscription status updates
    """
    from app.modules.platform.models import (
        PlatformPayment,
        PlatformPaymentEvent,
        PlatformInvoice,
    )

    # Find or create the payment record
    payment = (
        db.execute(
            select(PlatformPayment).where(
                PlatformPayment.subscription_id == subscription_id,
                PlatformPayment.payment_id == payment_id,
            )
        )
        .scalars()
        .first()
    )

    if not payment:
        # Create new payment record
        payment = PlatformPayment(
            subscription_id=subscription_id,
            payment_id=payment_id,
            kind="PAYMENT" if event_type in ("payment_success", "charge_success") else "REFUND",
            amount_minor=amount_minor or 0,
            currency_code=currency_code or "NPR",
            status=status,
            provider=metadata.get("provider") if metadata else None,
            provider_reference=metadata.get("provider_reference") if metadata else None,
            evidence_type=metadata.get("evidence_type") if metadata else None,
            evidence_ref=metadata.get("evidence_ref") if metadata else None,
            created_by_admin_id=metadata.get("admin_id") if metadata else None,
            metadata_json=metadata,
        )
        db.add(payment)
        db.flush()
    else:
        # Update existing payment
        payment.status = status
        payment.amount_minor = amount_minor or payment.amount_minor
        payment.currency_code = currency_code or payment.currency_code
        if payment_id:
            payment.payment_id = payment_id
        if metadata:
            payment.metadata_json = dict(payment.metadata_json or {}, **(metadata or {}))
        db.flush()

    # Create payment event record
    event = PlatformPaymentEvent(
        payment_id=payment.id,
        invoice_id=payment.invoice_id,
        restaurant_id=payment.restaurant_id,
        event_type=event_type,
        amount_minor=payment.amount_minor,
        currency_code=payment.currency_code,
        actor_admin_id=metadata.get("admin_id") if metadata else None,
        reason=metadata.get("reason") if metadata else None,
        metadata_json=metadata,
    )
    db.add(event)
    db.flush()

    # Handle based on event type
    now = datetime.now(UTC)
    if event_type in ("payment_success", "charge_success"):
        # Mark invoice as paid
        if payment.invoice_id:
            invoice = db.get(PlatformInvoice, payment.invoice_id)
            if invoice:
                from app.modules.platform.services.billing import invoice_status_after_payment

                new_status = invoice_status_after_payment(invoice, payment.amount_minor)
                invoice.status = new_status
                invoice.paid_at = now
                # Reset grace period on successful payment
                grace_days = get_setting(db, "platform.subscription.grace_period_days", 7) or 7
                invoice.grace_ends_at = now + timedelta(days=grace_days)
                db.flush()

                # Add payment event for payment confirmation
                pay_event = PlatformPaymentEvent(
                    payment_id=payment.id,
                    invoice_id=invoice.id,
                    restaurant_id=invoice.restaurant_id,
                    event_type="PAYMENT_CONFIRMED",
                    amount_minor=payment.amount_minor,
                    currency_code=invoice.currency_code,
                    actor_admin_id=metadata.get("admin_id") if metadata else None,
                    reason="Payment webhook confirmed payment",
                    metadata_json=metadata,
                )
                db.add(pay_event)
                db.flush()

    elif event_type in ("payment_failed", "charge_failed"):
        # Handle payment failure - extend grace period
        if payment.invoice_id:
            invoice = db.get(PlatformInvoice, payment.invoice_id)
            if invoice:
                # Extend grace period by 7 days
                grace_days = get_setting(db, "platform.subscription.grace_period_days", 7) or 7
                current_grace = invoice.grace_ends_at or now
                invoice.grace_ends_at = current_grace + timedelta(days=grace_days)
                db.flush()

    # Return summary
    return {
        "payment_id": payment.id,
        "invoice_id": payment.invoice_id,
        "status": payment.status,
        "event_type": event_type,
        "amount_minor": payment.amount_minor,
        "invoice_status": invoice.status if payment.invoice_id else None,
    }


