from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.orm import Session

from app.modules.notifications.models import OutboxEvent


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
