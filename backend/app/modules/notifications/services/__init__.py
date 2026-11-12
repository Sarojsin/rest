from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any
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
    payload: str | dict | None = None,
    title: str | None = None,
    body: str | None = None,
    data: dict[str, Any] | None = None,
    tokens: list[str] | None = None,
    roles: list[str] | None = None,
) -> OutboxEvent:
    """Queue a notification event for the FCM outbox worker.

    ``title`` / ``body`` are what the user actually sees on their device.
    ``data`` carries machine-readable routing hints (order_id, table_id, …)
    and is always stringified because FCM only accepts string values.
    ``tokens`` targets specific devices; when omitted the worker broadcasts to
    every device registered for the restaurant.
    """
    envelope: dict[str, Any] = {}

    if isinstance(payload, dict):
        envelope.update(payload)
    elif payload:
        try:
            parsed = json.loads(payload)
            if isinstance(parsed, dict):
                envelope.update(parsed)
            else:
                envelope["payload"] = parsed
        except (TypeError, ValueError):
            envelope["detail"] = str(payload)

    if title:
        envelope["title"] = title
    if body:
        envelope["body"] = body
    if data:
        envelope["data"] = {str(k): str(v) for k, v in data.items() if v is not None}
    if tokens:
        envelope["tokens"] = [str(token) for token in tokens if token]
    if roles:
        envelope["roles"] = [str(role) for role in roles]

    event = OutboxEvent(
        restaurant_id=restaurant_id,
        event_type=event_type,
        aggregate_type=aggregate_type,
        aggregate_id=str(aggregate_id),
        payload=json.dumps(envelope),
        occurred_at=datetime.now(UTC),
    )
    db.add(event)
    return event
