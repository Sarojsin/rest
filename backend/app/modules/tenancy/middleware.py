"""Tenant-context middleware — Phase 1 M2 (plan 22 §11).

Injects `request.tenant_id` from the `x-tenant-id` header into every request.
The gate helper (`GET /api/v1/tenant`) returns the current tenant's restaurant info.
"""

from fastapi import Request

tenant_context = type("TenantContext", (), {"tenant_id": None})()


def set_tenant_context(request: Request) -> None:
    """Extract tenant_id from x-tenant-id header and store it.

    If no header is provided, tenant_id stays None (opt-in per route).
    """
    tid = request.headers.get("x-tenant-id")
    if tid:
        tenant_context.tenant_id = tid
    else:
        tenant_context.tenant_id = None


def clear_tenant_context() -> None:
    """Reset at boundary between requests."""
    tenant_context.tenant_id = None


def get_tenant_id() -> str | None:
    """Return the current request's tenant_id, if any."""
    return getattr(tenant_context, "tenant_id", None)