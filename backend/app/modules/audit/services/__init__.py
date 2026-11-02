from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.orm import Session

from app.modules.audit.models import AuditEvent


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
