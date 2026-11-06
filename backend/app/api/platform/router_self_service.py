"""Self-service registration API (Plan 04).

Public endpoints for restaurant owner self-registration:
- GET /api/platform/public/plans - List available plans (no auth)
- POST /api/platform/public/register - Register a restaurant (no auth)
- GET /api/platform/self-service/registrations - List registrations (auth required)
- POST /api/platform/self-service/registrations/{id}/approve - Approve registration (auth required)
- POST /api/platform/self-service/registrations/{id}/reject - Reject registration (auth required)
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.modules.platform.deps import (
    PlatformActor,
    require_platform_permission,
    require_platform_step_up,
)
from app.modules.platform.schemas_admin import ReasonConfirmRequest
from app.modules.platform.services.common import require_confirm
from app.modules.platform.services.self_service import (
    approve_self_service_registration,
    create_self_service_registration,
    get_public_plans,
    get_self_service_registration,
    list_self_service_registrations,
    reject_self_service_registration,
    require_platform_setting,
    require_self_service_enabled,
    require_tenant_creation_enabled,
)
from app.modules.platform.services.trial import can_create_trial
from app.shared.errors import AppError

router = APIRouter(tags=["platform-self-service"])


@router.get("/public/plans")
def list_public_plans(
    db: Session = Depends(get_db),
) -> dict:
    """List available plans for self-service registration (no auth required)."""
    if not require_self_service_enabled(db):
        raise AppError(
            403,
            "SELF_SERVICE_DISABLED",
            "Forbidden",
            "Self-service registration is not enabled.",
        )

    plans = get_public_plans(db)
    return {"items": plans}


@router.post("/public/register", status_code=status.HTTP_201_CREATED)
async def register_tenant(
    request: Request,
    db: Session = Depends(get_db),
) -> dict:
    """Self-service tenant registration (no auth required).

    Body:
    {
      "restaurant_name": "string",
      "restaurant_slug": "string",
      "owner_email": "string",
      "owner_name": "string",
      "owner_phone": "string",
      "plan_code": "string",
      "trial_days": 14,
      "contact_email": "string",
      "contact_phone": "string",
      "legal_name": "string",
      "timezone": "string",
      "currency_code": "string",
      "source": "string",
      "reason": "string"
    }
    """
    if not require_self_service_enabled(db):
        raise AppError(
            403,
            "SELF_SERVICE_DISABLED",
            "Forbidden",
            "Self-service registration is not enabled.",
        )

    if not require_tenant_creation_enabled(db):
        raise AppError(
            403,
            "SELF_SERVICE_TENANT_CREATION_DISABLED",
            "Forbidden",
            "Self-service tenant creation is not enabled.",
        )

    body = await request.json()

    restaurant_name = body.get("restaurant_name")
    restaurant_slug = body.get("restaurant_slug")
    owner_email = body.get("owner_email")
    owner_name = body.get("owner_name")
    owner_phone = body.get("owner_phone")
    plan_code = body.get("plan_code")
    trial_days = body.get("trial_days", 14)
    contact_email = body.get("contact_email")
    contact_phone = body.get("contact_phone")
    legal_name = body.get("legal_name")
    timezone = body.get("timezone", "UTC")
    currency_code = body.get("currency_code", "USD")
    source = body.get("source", "self_service")
    reason = body.get("reason", "Self-service registration")

    # Validate required fields
    if not restaurant_name:
        raise AppError(422, "MISSING_RESTAURANT_NAME", "Invalid input", "Restaurant name is required.")
    if not restaurant_slug:
        raise AppError(422, "MISSING_RESTAURANT_SLUG", "Invalid input", "Restaurant slug is required.")
    if not owner_email:
        raise AppError(422, "MISSING_OWNER_EMAIL", "Invalid input", "Owner email is required.")
    if not owner_name:
        raise AppError(422, "MISSING_OWNER_NAME", "Invalid input", "Owner name is required.")
    if not plan_code:
        raise AppError(422, "MISSING_PLAN_CODE", "Invalid input", "Plan code is required.")

    # Auto-approve setting (default off; operators opt in per deployment).
    auto_approve = bool(
        require_platform_setting(db, "platform.self_service_auto_approve", False)
    )

    result = create_self_service_registration(
        db,
        restaurant_name=restaurant_name,
        restaurant_slug=restaurant_slug,
        owner_email=owner_email,
        owner_name=owner_name,
        owner_phone=owner_phone,
        plan_code=plan_code,
        trial_days=trial_days,
        contact_email=contact_email,
        contact_phone=contact_phone,
        legal_name=legal_name,
        timezone=timezone,
        currency_code=currency_code,
        source=source,
        reason=reason,
        auto_approve=auto_approve,
    )

    return result


@router.get("/self-service/registrations")
def list_registrations(
    status: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    actor: PlatformActor = Depends(require_platform_permission("tenant.view")),
    db: Session = Depends(get_db),
) -> dict:
    """List self-service registrations (platform admin only)."""
    items, total = list_self_service_registrations(db, status=status, page=page, page_size=page_size)
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/self-service/registrations/{registration_id}")
def get_registration(
    registration_id: UUID,
    actor: PlatformActor = Depends(require_platform_permission("tenant.view")),
    db: Session = Depends(get_db),
) -> dict:
    """Get a self-service registration by ID."""
    reg = get_self_service_registration(db, registration_id)
    if reg is None:
        raise AppError(404, "REGISTRATION_NOT_FOUND", "Not found", "Registration not found.")
    return reg


@router.post("/self-service/registrations/{registration_id}/approve")
def approve_registration(
    registration_id: UUID,
    payload: ReasonConfirmRequest,
    request: Request,
    actor: PlatformActor = Depends(require_platform_permission("tenant.create")),
    _: PlatformActor = Depends(require_platform_step_up),
    db: Session = Depends(get_db),
) -> dict:
    """Approve a pending self-service registration."""
    reg = get_self_service_registration(db, registration_id)
    if reg is None:
        raise AppError(
            404, "REGISTRATION_NOT_FOUND", "Not found", "Registration not found."
        )
    require_confirm(payload.confirm, reg["restaurant_slug"])
    result = approve_self_service_registration(
        db,
        registration_id=registration_id,
        admin_id=actor.admin_id,
        reason=payload.reason,
        request=request,
    )
    return result


@router.post("/self-service/registrations/{registration_id}/reject")
def reject_registration(
    registration_id: UUID,
    payload: ReasonConfirmRequest,
    request: Request,
    actor: PlatformActor = Depends(require_platform_permission("tenant.create")),
    _: PlatformActor = Depends(require_platform_step_up),
    db: Session = Depends(get_db),
) -> dict:
    """Reject a pending self-service registration."""
    reg = get_self_service_registration(db, registration_id)
    if reg is None:
        raise AppError(
            404, "REGISTRATION_NOT_FOUND", "Not found", "Registration not found."
        )
    require_confirm(payload.confirm, reg["restaurant_slug"])
    result = reject_self_service_registration(
        db,
        registration_id=registration_id,
        admin_id=actor.admin_id,
        reason=payload.reason,
    )
    return result


@router.get("/self-service/can-create-trial")
def can_create_trial_endpoint(
    actor: PlatformActor = Depends(require_platform_permission("tenant.view")),
    db: Session = Depends(get_db),
) -> dict:
    """Check if self-service trial creation is possible (for demo/testing)."""
    # This is a helper endpoint - in practice, restaurant_id would come from context
    restaurant_id = actor.admin_id  # Using admin_id as placeholder for demo
    eligible, reason = can_create_trial(db, restaurant_id=restaurant_id)
    return {
        "eligible": eligible,
        "reason": reason,
    }
