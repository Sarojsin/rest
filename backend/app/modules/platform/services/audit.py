"""Append-only platform audit writer (PA-0.8).

The caller owns the transaction: this function only adds the row so an audit
record and its business mutation commit or roll back together.

Rules (plan 03 §5):

- Mutations must pass a meaningful reason (>= 10 chars after trimming).
- Before/after snapshots are redacted by key and bounded in depth/size.
- Security events (login, MFA, refresh, logout) do not require a long reason.
- Nothing here updates or deletes an existing row.
"""

from __future__ import annotations

from typing import Any

from fastapi import Request
from sqlalchemy.orm import Session

from app.modules.platform.models import PlatformAuditLog

REDACTED = "[redacted]"
OMITTED = "[omitted]"

_SENSITIVE_FRAGMENTS = (
    "password",
    "passwd",
    "secret",
    "token",
    "recovery",
    "hash",
    "authorization",
    "cookie",
    "csrf",
    "api_key",
    "private_key",
)

MAX_REASON_LENGTH = 1000
MIN_MUTATION_REASON_LENGTH = 10
_MAX_DEPTH = 6
_MAX_ITEMS = 100
_MAX_STRING = 2000


def _redact(value: Any, depth: int = 0) -> Any:
    if depth > _MAX_DEPTH:
        return OMITTED
    if isinstance(value, dict):
        result = {}
        for index, (key, item) in enumerate(value.items()):
            if index >= _MAX_ITEMS:
                result[OMITTED] = True
                break
            lowered = str(key).lower()
            if any(fragment in lowered for fragment in _SENSITIVE_FRAGMENTS):
                result[str(key)] = REDACTED
            else:
                result[str(key)] = _redact(item, depth + 1)
        return result
    if isinstance(value, (list, tuple)):
        return [_redact(item, depth + 1) for item in list(value)[:_MAX_ITEMS]]
    if isinstance(value, str):
        return value[:_MAX_STRING]
    if isinstance(value, (int, float, bool)) or value is None:
        return value
    return str(value)[:_MAX_STRING]


def write_platform_audit(
    db: Session,
    *,
    action: str,
    entity_type: str,
    entity_id: str,
    actor_admin_id=None,
    actor_email: str | None = None,
    restaurant_id=None,
    reason: str = "",
    request: Request | None = None,
    before: dict | None = None,
    after: dict | None = None,
    require_reason: bool = False,
) -> PlatformAuditLog:
    normalized_reason = (reason or "").strip()
    if require_reason and len(normalized_reason) < MIN_MUTATION_REASON_LENGTH:
        raise ValueError(
            f"Audit reason must be at least {MIN_MUTATION_REASON_LENGTH} characters "
            "for mutations"
        )
    normalized_reason = normalized_reason[:MAX_REASON_LENGTH]

    request_id = None
    ip = None
    user_agent = None
    if request is not None:
        request_id = getattr(request.state, "request_id", None)
        ip = request.client.host if request.client else None
        user_agent = request.headers.get("user-agent")

    entry = PlatformAuditLog(
        actor_admin_id=actor_admin_id,
        actor_email_snapshot=actor_email,
        action=action,
        entity_type=entity_type,
        entity_id=str(entity_id)[:64],
        restaurant_id=restaurant_id,
        reason=normalized_reason,
        request_id=(request_id or None) and str(request_id)[:64],
        ip=(ip or None) and str(ip)[:64],
        user_agent=((user_agent or "")[:255] or None),
        before_json=_redact(before) if before is not None else None,
        after_json=_redact(after) if after is not None else None,
    )
    db.add(entry)
    return entry
