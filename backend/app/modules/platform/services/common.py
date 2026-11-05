"""Shared validation and paging helpers for platform console routes."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.modules.platform.services.audit import MIN_MUTATION_REASON_LENGTH
from app.shared.errors import AppError


def require_reason(value: str | None) -> str:
    normalized = (value or "").strip()
    if len(normalized) < MIN_MUTATION_REASON_LENGTH:
        raise AppError(
            422,
            "REASON_REQUIRED",
            "Invalid input",
            f"A reason of at least {MIN_MUTATION_REASON_LENGTH} characters is required.",
        )
    return normalized


def require_confirm(value: str | None, expected: str) -> None:
    if (value or "").strip() != expected:
        raise AppError(
            422,
            "CONFIRMATION_MISMATCH",
            "Invalid input",
            f"Type {expected!r} to confirm this action.",
        )


def page_params(page: int, page_size: int) -> tuple[int, int]:
    return max(1, page), min(100, max(1, page_size))


def paginated(items: list, total: int, page: int, page_size: int) -> dict:
    return {"items": items, "total": total, "page": page, "page_size": page_size}


def now_utc() -> datetime:
    return datetime.now(UTC)


def serialize_audit(row: Any) -> dict:
    return {
        "id": row.id,
        "action": row.action,
        "actor_admin_id": row.actor_admin_id,
        "actor_email": row.actor_email_snapshot,
        "entity_type": row.entity_type,
        "entity_id": row.entity_id,
        "tenant_id": row.restaurant_id,
        "restaurant_id": row.restaurant_id,
        "reason": row.reason,
        "request_id": row.request_id,
        "ip": row.ip,
        "user_agent": row.user_agent,
        "before": row.before_json,
        "after": row.after_json,
        "created_at": row.created_at,
    }
