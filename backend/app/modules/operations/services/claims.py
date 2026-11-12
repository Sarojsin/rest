"""Waiter claim service (plan 08).

A waiter can claim an order ("I am handling this"), escalate it to a
supervisor when they cannot resolve it, and claims time out automatically:
the sweep escalates expired claims so the queue never stalls behind a
forgotten claim.

- Concurrency: claim writes are compare-and-swap on the order version, so two
  waiters can never both end up owning one order.
- Rate limiting: per-waiter sliding-window counters (in-memory, per worker
  process — production multi-worker deployments move them to Redis; the
  account-lockout store in app.core.security makes the same trade-off).
- Audit: every claim/escalate/release/timeout records an audit event with
  actor ids (plan 08 §Audit requirements), plus an outbox event when a
  supervisor-facing escalation starts.
"""

from collections import defaultdict
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.config import settings
from app.modules.audit.services import record_audit
from app.modules.notifications.services import record_outbox
from app.modules.operations.models import Order
from app.modules.operations.services.orders import _load_order
from app.shared.enums import OrderStatus
from app.shared.errors import AppError

_STATE_CLAIMED = "CLAIMED"
_STATE_ESCALATED = "ESCALATED"

# Sliding-window rate limiter: {(membership_id, action): [timestamps]}


_rate_counts: defaultdict[tuple[UUID, str], list[datetime]] = defaultdict(list)


def _rate_scope(membership_id: UUID, action: str, limit: int) -> None:
    """429 when this membership exceeded the hourly cap for the action."""
    now = datetime.now(UTC)
    window_start = now - timedelta(hours=1)
    key = (membership_id, action)
    bucket = [ts for ts in _rate_counts[key] if ts > window_start]
    if len(bucket) >= limit:
        raise AppError(
            429,
            "RATE_LIMIT_EXCEEDED",
            "Too many requests",
            f"Maximum {limit} {action}s per hour reached. Try again later.",
        )
    bucket.append(now)
    _rate_counts[key] = bucket


def clear_rate_limits() -> None:
    """Test seam: the in-process counter must not leak between tests."""
    _rate_counts.clear()


def _assign(
    db, order: Order, seen_version: int, **fields
) -> bool:
    """Compare-and-swap update on the order version; False = lost the race."""
    result = db.execute(
        update(Order)
        .where(
            Order.id == order.id,
            Order.restaurant_id == order.restaurant_id,
            Order.version == seen_version,
        )
        .values(version=seen_version + 1, **fields)
    )
    return bool(result.rowcount)


def claim_order(
    db: Session, membership, order_id: UUID,
) -> Order:
    """Waiter takes responsibility for an open order (plan 08 §Claim flow)."""
    _rate_scope(membership.id, "claim", settings.claims_per_hour_limit)
    order = _load_order(db, membership.restaurant_id, order_id)
    status = OrderStatus(order.status)
    if status not in (OrderStatus.PENDING_CONFIRMATION, OrderStatus.ACCEPTED):
        raise AppError(
            409, "ORDER_NOT_CLAIMABLE", "State conflict",
            "This order no longer needs a claim.",
        )
    if order.claim_state == _STATE_ESCALATED:
        raise AppError(
            409, "ORDER_ESCALATED", "State conflict",
            "This order was escalated to a supervisor.",
        )
    # Idempotent for the same claimant: re-tapping Claim keeps the ownership.
    if order.claim_state == _STATE_CLAIMED:
        if order.claimed_by_membership_id == membership.id:
            return order
        raise AppError(
            409,
            "ORDER_ALREADY_CLAIMED",
            "State conflict",
            "Another staff member already claimed this order.",
        )

    now = datetime.now(UTC)
    timeout_at = now + timedelta(minutes=settings.claim_timeout_minutes)
    if not _assign(
        db, order, order.version,
        claim_state=_STATE_CLAIMED,
        claimed_by_membership_id=membership.id,
        claimed_at=now,
        claim_timeout_at=timeout_at,
    ):
        raise AppError(
            409,
            "ORDER_ALREADY_CLAIMED",
            "State conflict",
            "Another staff member already claimed this order.",
        )
    record_audit(
        db,
        restaurant_id=membership.restaurant_id,
        action="orders.claim",
        entity_type="order",
        entity_id=order.id,
        actor_user_id=membership.user_id,
        actor_membership_id=membership.id,
        detail="Order claimed",
    )
    db.commit()
    return _load_order(db, membership.restaurant_id, order.id)


def escalate_order(
    db: Session, membership, order_id: UUID, note: str = "",
    *,
    is_supervisor: bool = False,
) -> Order:
    """Hand the order to a supervisor (plan 08 §Escalation flow).

    `is_supervisor` is injected by the router layer (actor permissions), so
    this module keeps no dependency on role definitions.
    """
    _rate_scope(membership.id, "escalate", settings.escalations_per_hour_limit)
    order = _load_order(db, membership.restaurant_id, order_id)
    if order.claim_state != _STATE_CLAIMED:
        raise AppError(
            409, "ORDER_NOT_CLAIMED", "State conflict",
            "Claim the order before escalating it.",
        )
    if order.claimed_by_membership_id != membership.id and not is_supervisor:
        raise AppError(
            403, "FORBIDDEN", "Forbidden",
            "Only the claimant or a supervisor can escalate.",
        )
    now = datetime.now(UTC)
    detail_escalated = (
        ("Escalated to supervisor: " + note.strip()) if note.strip() else "Escalated to supervisor"
    )
    if not _assign(
        db, order, order.version,
        claim_state=_STATE_ESCALATED,
        escalated_by_membership_id=membership.id,
        escalated_at=now,
    ):
        raise AppError(
            409, "ORDER_ALREADY_ESCALATED", "State conflict",
            "This order is already escalated.",
        )
    record_audit(
        db,
        restaurant_id=membership.restaurant_id,
        action="orders.escalate",
        entity_type="order",
        entity_id=order.id,
        actor_user_id=membership.user_id,
        actor_membership_id=membership.id,
        detail=detail_escalated,
    )
    record_outbox(
        db,
        restaurant_id=membership.restaurant_id,
        event_type="order.escalated",
        aggregate_type="order",
        aggregate_id=order.id,
        title="Order escalated",
        body=detail_escalated,
        data={
            "order_id": str(order.id),
            "table_id": str(order.table_id),
            "route": "/staff",
        },
        roles=["owner", "manager"],
    )
    db.commit()
    return _load_order(db, membership.restaurant_id, order.id)


def release_claim(
    db: Session, membership, order_id: UUID,
    *,
    is_supervisor: bool = False,
) -> Order:
    """Return an order to the shared queue (voluntary hand-off or resolve).

    `is_supervisor` is injected by the router layer (actor permissions), so
    this module keeps no dependency on role definitions.
    """
    order = _load_order(db, membership.restaurant_id, order_id)
    if not order.claim_state:
        raise AppError(
            409, "ORDER_NOT_CLAIMED", "State conflict",
            "This order is not claimed.",
        )
    if order.claimed_by_membership_id != membership.id and not is_supervisor:
        raise AppError(
            403, "FORBIDDEN", "Forbidden",
            "You cannot release someone else's claim.",
        )
    if not _assign(
        db, order, order.version,
        claim_state="",
        claimed_by_membership_id=None,
        claimed_at=None,
        claim_timeout_at=None,
    ):
        raise AppError(
            409, "ORDER_STATE_CONFLICT", "State conflict",
            "The order was updated concurrently. Retry.",
        )
    record_audit(
        db,
        restaurant_id=membership.restaurant_id,
        action="orders.release",
        entity_type="order",
        entity_id=order.id,
        actor_user_id=membership.user_id,
        actor_membership_id=membership.id,
        detail="Order released back to the queue",
    )
    db.commit()
    return _load_order(db, membership.restaurant_id, order.id)


def sweep_expired_claims(db: Session, restaurant_id: UUID) -> int:
    """Auto-escalate claims that ran past their timeout (plan 08 §Timeout).

    Lazy sweep: called by claim/list endpoints so no separate worker process
    is required today; a worker beat can also invoke it directly later.
    Returns how many claims were escalated.
    """
    now = datetime.now(UTC)
    expired = db.scalars(
        select(Order).where(
            Order.restaurant_id == restaurant_id,
            Order.claim_state == _STATE_CLAIMED,
            Order.claim_timeout_at is not None,
            Order.claim_timeout_at < now,
            Order.status.in_([OrderStatus.PENDING_CONFIRMATION, OrderStatus.ACCEPTED]),
        )
        .limit(100)
    ).all()
    for order in expired:
        order.claim_state = _STATE_ESCALATED
        order.escalated_at = now
        record_audit(
            db,
            restaurant_id=restaurant_id,
            action="orders.claim_timeout",
            entity_type="order",
            entity_id=order.id,
            detail=f"Claim timed out after {settings.claim_timeout_minutes} min — escalated",
        )
        record_outbox(
            db,
            restaurant_id=restaurant_id,
            event_type="order.escalated",
            aggregate_type="order",
            aggregate_id=order.id,
        )
    if expired:
        db.commit()
    return len(expired)