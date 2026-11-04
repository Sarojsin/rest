"""Platform role → permission map (PA-0.4).

Default deny. ``superadmin`` is intentionally spelled out rather than treated
as a wildcard so that adding a permission produces a visible diff in this file.

Platform roles are independent of tenant roles: a restaurant ``owner`` has no
platform permissions and vice versa.
"""

from __future__ import annotations

from collections.abc import Iterable

SUPPORT = "support"
BILLING = "billing"
OPS = "ops"
SUPERADMIN = "superadmin"

PLATFORM_ROLES: frozenset[str] = frozenset({SUPPORT, BILLING, OPS, SUPERADMIN})

PLATFORM_ROLE_PERMISSIONS: dict[str, frozenset[str]] = {
    SUPPORT: frozenset(
        {
            "platform.dashboard.view",
            "tenant.view",
            "tenant.search",
            "plan.view",
            "subscription.view",
            "invoice.view",
            "audit.view",
            "settings.view",
            "diagnostics.view",
            "analytics.view",
        }
    ),
    BILLING: frozenset(
        {
            "platform.dashboard.view",
            "tenant.view",
            "tenant.search",
            "plan.view",
            "subscription.view",
            "subscription.manage",
            "invoice.view",
            "invoice.manage",
            "payment.confirm",
            "payment.refund.request",
            "payment.refund.approve",
            "payment.refund.complete",
            "audit.view",
            "settings.view",
            "diagnostics.view",
            "analytics.view",
        }
    ),
    OPS: frozenset(
        {
            "platform.dashboard.view",
            "tenant.view",
            "tenant.search",
            "tenant.create",
            "tenant.suspend",
            "tenant.reactivate",
            "tenant.force_logout",
            "tenant.export",
            "plan.view",
            "subscription.view",
            "invoice.view",
            "audit.view",
            "settings.view",
            "diagnostics.view",
            "analytics.view",
        }
    ),
    SUPERADMIN: frozenset(
        {
            "platform.dashboard.view",
            "tenant.view",
            "tenant.search",
            "tenant.create",
            "tenant.suspend",
            "tenant.reactivate",
            "tenant.force_logout",
            "tenant.export",
            "tenant.delete",
            "plan.view",
            "plan.manage",
            "subscription.view",
            "subscription.manage",
            "subscription.override",
            "invoice.view",
            "invoice.manage",
            "payment.confirm",
            "payment.void",
            "payment.refund.request",
            "payment.refund.approve",
            "payment.refund.complete",
            "platform_user.view",
            "platform_user.manage",
            "audit.view",
            "settings.view",
            "settings.manage",
            "diagnostics.view",
            "analytics.view",
        }
    ),
}

PLATFORM_PERMISSIONS: frozenset[str] = frozenset().union(
    *PLATFORM_ROLE_PERMISSIONS.values()
)

# Result codes for the maker–checker helper. These are audit labels, not
# permission decisions: refund self-approval is allowed while the dual-approval
# policy is deferred, but it is flagged.
MAKER_CHECKER_DISTINCT = "distinct_admins"
MAKER_CHECKER_SELF = "single_admin_approval"
MAKER_CHECKER_ONLY_ONE = "single_admin_platform"


def permissions_for(role: str) -> frozenset[str]:
    """Return the explicit permission set for a platform role (default deny)."""
    return PLATFORM_ROLE_PERMISSIONS.get(role, frozenset())


def has_permission(role: str, permission: str) -> bool:
    return permission in permissions_for(role)


def is_platform_role(role: str) -> bool:
    return role in PLATFORM_ROLES


def permissions_are_known(permissions: Iterable[str]) -> bool:
    """True when every permission exists in the map (used by config tests)."""
    return all(permission in PLATFORM_PERMISSIONS for permission in permissions)


def maker_checker_status(
    *,
    maker_admin_id,
    checker_admin_id,
    active_admin_count: int,
) -> str:
    """Classify a maker–checker decision for audit metadata.

    - one active admin → ``single_admin_platform``
    - same admin when others exist → ``single_admin_approval`` (flagged)
    - different admins → ``distinct_admins``
    """
    if active_admin_count <= 1:
        return MAKER_CHECKER_ONLY_ONE
    if maker_admin_id == checker_admin_id:
        return MAKER_CHECKER_SELF
    return MAKER_CHECKER_DISTINCT
