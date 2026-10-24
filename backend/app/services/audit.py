from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.audit import AuditEvent, OutboxEvent


def record_audit(
    db: Session,
    *,
    restaurant_id: UUID,
    action: str,
    entity_type: str,
    entity_id: UUID | str,
    actor_user_id: UUID | None = None,
    actor_membership_id: UUID | None = None,
    request_id: str | None = None,
    detail: str = "",
) -> None:
    db.add(
        AuditEvent(
            restaurant_id=restaurant_id,
            actor_user_id=actor_user_id,
            actor_membership_id=actor_membership_id,
            action=action,
            entity_type=entity_type,
            entity_id=str(entity_id),
            occurred_at=datetime.now(UTC),
            request_id=request_id,
            detail=detail,
        )
    )


def record_outbox(
    db: Session,
    *,
    restaurant_id: UUID,
    event_type: str,
    aggregate_type: str,
    aggregate_id: UUID | str,
    payload: str = "{}",
) -> None:
    db.add(
        OutboxEvent(
            restaurant_id=restaurant_id,
            event_type=event_type,
            aggregate_type=aggregate_type,
            aggregate_id=str(aggregate_id),
            payload=payload,
            occurred_at=datetime.now(UTC),
        )
    )
