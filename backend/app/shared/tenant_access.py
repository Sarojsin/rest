"""Pure tenant access-state rules (PA-0.11 / PA D-6).

Kept free of ORM imports so both the tenancy service and other modules (billing)
can share the exact same rule without adding a cross-module service coupling.
Callers pass the primitive fields they already have.
"""

from __future__ import annotations

from datetime import datetime

from app.shared.errors import AppError

ACTIVE = "ACTIVE"
SUSPENDED = "SUSPENDED"
CANCELLED = "CANCELLED"


def tenant_suspended_error() -> AppError:
    return AppError(
        403,
        "TENANT_SUSPENDED",
        "Tenant suspended",
        "This restaurant account is suspended. Contact the platform administrator.",
    )


def tenant_is_active(*, status: str, archived_at: datetime | None) -> bool:
    return status == ACTIVE and archived_at is None


def _comparison_pair(
    started_at: datetime | None, suspended_at: datetime | None
) -> tuple[datetime, datetime] | None:
    if started_at is None or suspended_at is None:
        return None
    if started_at.tzinfo is None and suspended_at.tzinfo is not None:
        suspended_at = suspended_at.replace(tzinfo=None)
    elif started_at.tzinfo is not None and suspended_at.tzinfo is None:
        started_at = started_at.replace(tzinfo=None)
    return started_at, suspended_at


def started_before_suspension(
    *, started_at: datetime | None, suspended_at: datetime | None
) -> bool:
    pair = _comparison_pair(started_at, suspended_at)
    return pair is not None and pair[0] < pair[1]


def inflight_allowed(
    *,
    status: str,
    archived_at: datetime | None,
    suspended_at: datetime | None,
    started_at: datetime | None,
) -> bool:
    """A suspended tenant may finish work that started before suspension."""
    if tenant_is_active(status=status, archived_at=archived_at):
        return True
    if status != SUSPENDED:
        return False
    return started_before_suspension(started_at=started_at, suspended_at=suspended_at)


def ensure_tenant_active(*, status: str, archived_at: datetime | None) -> None:
    if not tenant_is_active(status=status, archived_at=archived_at):
        raise tenant_suspended_error()


def ensure_inflight_allowed(
    *,
    status: str,
    archived_at: datetime | None,
    suspended_at: datetime | None,
    started_at: datetime | None,
) -> None:
    if inflight_allowed(
        status=status,
        archived_at=archived_at,
        suspended_at=suspended_at,
        started_at=started_at,
    ):
        return
    raise tenant_suspended_error()
