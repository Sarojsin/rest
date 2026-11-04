"""Tenant lifecycle enforcement (PA-0.11, plan 03 §6.2 / PA D-6).

Suspension is a platform action, but enforcement lives in the staff request
path. Two narrow helpers are used:

``ensure_tenant_active``
    Block *new* work for a tenant that is not ``ACTIVE``.

``ensure_inflight_allowed``
    Preserve an operation that legitimately started before the suspension
    (finishing/cancelling an existing order, billing and settling the current
    visit). The test is a timestamp comparison against ``suspended_at`` — not a
    broad string match — so a new operation on a suspended tenant is rejected.

Nothing here writes or commits; callers own the transaction.
"""

from __future__ import annotations

from datetime import datetime

from app.modules.tenancy.models import Restaurant
from app.shared import tenant_access
from app.shared.errors import AppError

ACTIVE = tenant_access.ACTIVE
SUSPENDED = tenant_access.SUSPENDED
CANCELLED = tenant_access.CANCELLED


def is_active(restaurant: Restaurant) -> bool:
    return tenant_access.tenant_is_active(
        status=restaurant.status, archived_at=restaurant.archived_at
    )


def tenant_suspended_error() -> AppError:
    return tenant_access.tenant_suspended_error()


def ensure_tenant_active(restaurant: Restaurant) -> None:
    """Reject any new action when the tenant is not active."""
    tenant_access.ensure_tenant_active(
        status=restaurant.status, archived_at=restaurant.archived_at
    )


def started_before_suspension(
    restaurant: Restaurant, started_at: datetime | None
) -> bool:
    """True when ``started_at`` predates the suspension timestamp."""
    return tenant_access.started_before_suspension(
        started_at=started_at, suspended_at=restaurant.suspended_at
    )


def ensure_inflight_allowed(
    restaurant: Restaurant, started_at: datetime | None
) -> None:
    """Allow finishing work that began before suspension; block new work.

    Only a ``SUSPENDED`` tenant gets the grace path. A ``CANCELLED`` tenant is
    terminal and gets no in-flight exception.
    """
    tenant_access.ensure_inflight_allowed(
        status=restaurant.status,
        archived_at=restaurant.archived_at,
        suspended_at=restaurant.suspended_at,
        started_at=started_at,
    )
