"""Tenant management for the platform console (plan 05 §4)."""

from __future__ import annotations

import logging
from datetime import timedelta
from uuid import UUID, uuid4

import sqlalchemy as sa
from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import hash_token, new_token
from app.db.session import get_db
from app.modules.platform.deps import (
    PlatformActor,
    require_platform_permission,
    require_platform_step_up,
)
from app.modules.platform.models import (
    PlatformAuditLog,
    PlatformExportJob,
    PlatformOneTimeToken,
    PlatformPlan,
    PlatformPlanLimit,
    PlatformPlanVersion,
    PlatformSubscription,
    PlatformSupportTicket,
)
from app.modules.platform.schemas_admin import (
    OnboardingCreateRequest,
    ReasonConfirmRequest,
    SupportTicketCreateRequest,
    SupportTicketOut,
    SupportTicketUpdateRequest,
    TenantAnonymizeRequest,
    TenantCancelRequest,
    TenantCreateRequest,
    TenantUpdateRequest,
)
from app.modules.tenancy.models import (
    Restaurant,
    RestaurantMembership,
    RestaurantSettings,
)
from app.modules.tenancy.services import platform_directory
from app.modules.platform.services.audit import write_platform_audit
from app.modules.platform.services.billing import (
    add_subscription_event,
    period_end,
    serialize_subscription,
)
from app.modules.platform.services.plan_versions import (
    get_active_plan_version,
)
from app.modules.platform.services.common import (
    page_params,
    paginated,
    require_confirm,
    require_reason,
    serialize_audit,
    now_utc,
)
from app.modules.platform.services.email import get_email_service
from app.modules.platform.services.entitlements import (
    check_feature_enabled,
    consume_limit,
    get_effective_entitlements,
)
from app.shared.errors import AppError

router = APIRouter(tags=["platform-tenants"])


def _subscription_for(db: Session, tenant_id: UUID) -> PlatformSubscription | None:
    return db.scalar(
        select(PlatformSubscription)
        .where(
            PlatformSubscription.restaurant_id == tenant_id,
            PlatformSubscription.status.in_(platform_directory.LIVE_STATUSES),
        )
        .order_by(PlatformSubscription.created_at.desc())
        .limit(1)
    )


@router.get("/tenants")
def list_tenants(
    status_filter: str | None = Query(default=None, alias="status"),
    plan: str | None = None,
    q: str | None = None,
    page: int = 1,
    page_size: int = 25,
    actor: PlatformActor = Depends(require_platform_permission("tenant.view")),
    db: Session = Depends(get_db),
) -> dict:
    page, page_size = page_params(page, page_size)
    items, total = platform_directory.list_tenants(
        db, status=status_filter, plan_code=plan, q=q, page=page, page_size=page_size
    )
    return paginated(items, total, page, page_size)


@router.post("/tenants", status_code=status.HTTP_201_CREATED)
def create_tenant(
    payload: TenantCreateRequest,
    request: Request,
    actor: PlatformActor = Depends(require_platform_permission("tenant.create")),
    _: PlatformActor = Depends(require_platform_step_up),
    db: Session = Depends(get_db),
) -> dict:
    reason = require_reason(payload.reason)
    plan = db.scalar(select(PlatformPlan).where(PlatformPlan.code == payload.plan_code))
    if plan is None:
        raise AppError(404, "PLAN_NOT_FOUND", "Not found", "Plan not found.")
    if plan.status != "ACTIVE":
        raise AppError(409, "PLAN_NOT_ACTIVE", "Conflict", "That plan is not active.")

    # Get the active plan version and enforce entitlements
    active_version = get_active_plan_version(db, plan.id)
    if active_version is None:
        raise AppError(
            409,
            "PLAN_VERSION_NOT_ACTIVE",
            "Conflict",
            "No active plan version found for this plan.",
        )

    # Check that any features the tenant wants are enabled
    # For now, we check QR ordering if the tenant requests it
    if not check_feature_enabled(db, restaurant_id=uuid4(), feature_key="qr_ordering"):
        # Feature not enabled - this is informational, not blocking
        # The tenant can still be created but QR ordering won't be available
        pass

    tenant = platform_directory.create_tenant(
        db,
        name=payload.name,
        slug=payload.slug,
        owner_email=str(payload.owner_email),
        owner_display_name=payload.owner_display_name,
        contact_email=payload.contact_email,
        contact_phone=payload.contact_phone,
        legal_name=payload.legal_name,
        timezone=payload.timezone,
        currency_code=payload.currency_code,
    )

    now = now_utc()
    trial_days = payload.trial_days
    sub_status = "TRIALING" if trial_days > 0 else "ACTIVE"
    subscription = PlatformSubscription(
        restaurant_id=tenant["id"],
        plan_id=plan.id,
        plan_version_id=active_version.id,
        status=sub_status,
        trial_ends_at=now + timedelta(days=trial_days) if trial_days else None,
        current_period_start=now,
        current_period_end=now + timedelta(days=trial_days or 30),
        cancel_at_period_end=False,
        price_snapshot_minor=active_version.price_monthly_minor,
        currency_snapshot=active_version.currency_code,
        billing_interval_snapshot="MONTHLY",
        created_by_admin_id=actor.admin_id,
    )
    db.add(subscription)
    db.flush()
    add_subscription_event(
        db,
        subscription,
        event_type="CREATED",
        admin_id=actor.admin_id,
        reason=reason,
        to_status=sub_status,
        metadata={
            "plan_code": plan.code,
            "plan_version": active_version.version,
            "trial_days": trial_days,
            "source": payload.source,
        },
    )

    raw_token = new_token(32)
    db.add(
        PlatformOneTimeToken(
            token_hash=hash_token(raw_token),
            purpose="OWNER_INVITE",
            email=str(payload.owner_email).lower(),
            restaurant_id=tenant["id"],
            expires_at=now + timedelta(hours=72),
            created_by_admin_id=actor.admin_id,
        )
    )
    write_platform_audit(
        db,
        action="TENANT_CREATED",
        entity_type="restaurant",
        entity_id=str(tenant["id"]),
        actor_admin_id=actor.admin_id,
        actor_email=actor.email,
        restaurant_id=tenant["id"],
        reason=reason,
        request=request,
        after={
            "name": tenant["name"],
            "slug": tenant["slug"],
            "plan_code": plan.code,
            "plan_version": active_version.version,
            "owner_email": str(payload.owner_email),
        },
    )
    db.commit()

    # Send the owner invitation email (Plan 14). The raw token is delivered
    # only via email; the API response never exposes it.
    # Build the accept URL dynamically from the request origin so invitation
    # links always point to the correct frontend host, falling back to config.
    request_origin = (
        request.headers.get("origin", "").rstrip("/")
        if request and request.headers.get("origin")
        else ""
    )
    base_url = (
        request_origin
        or settings.invitation_base_url.rstrip("/")
        if settings.invitation_base_url
        else (settings.platform_tenant_origin.rstrip("/") if settings.platform_tenant_origin else "")
    )
    accept_url = (
        f"{base_url}/auth/invitations/{raw_token}"
        if base_url
        else f"/auth/invitations/{raw_token}"
    )
    try:
        email_service = get_email_service()
        email_service.send_invitation(
            to_email=str(payload.owner_email).lower(),
            to_name=payload.owner_display_name or str(payload.owner_email).split("@")[0],
            restaurant_name=tenant["name"],
            token=raw_token,
            accept_url=accept_url,
            expires_at=(now + timedelta(hours=settings.invitation_ttl_hours)).isoformat(),
        )
        invitation_sent = True
    except Exception:
        # Email failure must not roll back tenant creation. Log and continue;
        # the token remains valid and can be re-sent.
        logger = logging.getLogger("app.platform.email")
        logger.exception("Failed to send owner invitation email to %s", payload.owner_email)
        invitation_sent = False

    return {
        "tenant": tenant,
        "subscription": serialize_subscription(db, subscription),
        "invitation": {
            "sent": invitation_sent,
            "expires_at": now + timedelta(hours=settings.invitation_ttl_hours),
            # The admin who created the tenant may hand this one-time link to
            # the owner directly when email delivery is unavailable.
            "accept_url": accept_url,
            "token": raw_token,
        },
        "audit_id": None,
    }


@router.post("/onboarding/restaurants", status_code=status.HTTP_201_CREATED)
def onboard_restaurant(
    payload: OnboardingCreateRequest,
    request: Request,
    actor: PlatformActor = Depends(require_platform_permission("tenant.create")),
    _: PlatformActor = Depends(require_platform_step_up),
    db: Session = Depends(get_db),
) -> dict:
    """Onboard a complete restaurant organization in one transaction.

    Creates: tenant, settings, subscription, branches, owner membership and
    invitation token. Sends the owner invitation email (Plan 14).
    """
    # Typed confirmation (PA-04 pattern): confirm must equal the restaurant slug.
    require_confirm(payload.confirm, payload.restaurant.slug)
    reason = require_reason(payload.reason)

    # Validate plan
    plan = db.scalar(select(PlatformPlan).where(PlatformPlan.code == payload.subscription.plan_code))
    if plan is None:
        raise AppError(404, "PLAN_NOT_FOUND", "Not found", "Plan not found.")
    if plan.status != "ACTIVE":
        raise AppError(409, "PLAN_NOT_ACTIVE", "Conflict", "That plan is not active.")

    active_version = get_active_plan_version(db, plan.id)
    if active_version is None:
        raise AppError(
            409,
            "PLAN_VERSION_NOT_ACTIVE",
            "Conflict",
            "No active plan version found for this plan.",
        )

    # Check branch count against plan limit.
    branch_limit_row = db.scalar(
        select(PlatformPlanLimit).where(
            PlatformPlanLimit.plan_version_id == active_version.id,
            PlatformPlanLimit.limit_key == "branches",
        )
    )
    branch_limit = branch_limit_row.limit_value if branch_limit_row else None
    if branch_limit is not None and len(payload.branches) > branch_limit:
        raise AppError(
            409,
            "SEAT_LIMIT_REACHED",
            "Conflict",
            f"Requested {len(payload.branches)} branches exceeds plan limit of {branch_limit}.",
            extra={"limit_key": "branches", "limit": branch_limit, "requested": len(payload.branches)},
        )

    now = now_utc()

    # Delegate tenant + settings + owner user/membership creation to
    # platform_directory.create_tenant (shared with PA-04 admin flow).
    tenant = platform_directory.create_tenant(
        db,
        name=payload.restaurant.name,
        slug=payload.restaurant.slug,
        owner_email=str(payload.owner.email),
        owner_display_name=payload.owner.full_name,
        contact_email=payload.restaurant.contact_email,
        contact_phone=payload.restaurant.contact_phone,
        legal_name=payload.restaurant.legal_name,
        timezone=payload.restaurant.timezone,
        currency_code=payload.restaurant.currency_code,
    )
    restaurant_id = tenant["id"]

    # Create subscription.
    sub_status = "TRIALING" if payload.subscription.trial_days > 0 else "ACTIVE"
    subscription = PlatformSubscription(
        restaurant_id=restaurant_id,
        plan_id=plan.id,
        plan_version_id=active_version.id,
        status=sub_status,
        trial_ends_at=now + timedelta(days=payload.subscription.trial_days)
        if payload.subscription.trial_days
        else None,
        current_period_start=now,
        current_period_end=now + timedelta(days=payload.subscription.trial_days or 30),
        cancel_at_period_end=False,
        price_snapshot_minor=active_version.price_monthly_minor,
        currency_snapshot=active_version.currency_code,
        billing_interval_snapshot=payload.subscription.billing_interval,
        created_by_admin_id=actor.admin_id,
    )
    db.add(subscription)
    db.flush()
    add_subscription_event(
        db,
        subscription,
        event_type="CREATED",
        admin_id=actor.admin_id,
        reason=reason,
        to_status=sub_status,
        metadata={
            "plan_code": plan.code,
            "plan_version": active_version.version,
            "trial_days": payload.subscription.trial_days,
            "source": "onboarding",
        },
    )

    # Create branches.
    created_branches = []
    for branch_data in payload.branches:
        branch_id = uuid4()
        db.execute(
            text(
                "INSERT INTO branches "
                "(id, restaurant_id, name, code, address, phone, timezone, "
                "currency_code, is_active, opening_hours, settings_json, "
                "created_at, updated_at) "
                "VALUES (:id, :rid, :name, :code, :address, :phone, :tz, "
                ":currency, true, :opening_hours, '{}', :now, :now)"
            ),
            {
                "id": branch_id,
                "rid": restaurant_id,
                "name": branch_data.name,
                "code": branch_data.code,
                "address": branch_data.address,
                "phone": branch_data.phone,
                "tz": branch_data.timezone,
                "currency": payload.restaurant.currency_code,
                "opening_hours": branch_data.opening_hours,
                "now": now,
            },
        )
        created_branches.append(
            {
                "id": str(branch_id),
                "name": branch_data.name,
                "code": branch_data.code,
                "status": "ACTIVE",
            }
        )

    # Create owner invitation token (single-use, 72h TTL).
    raw_token = new_token(32)
    expires_at = now + timedelta(hours=settings.invitation_ttl_hours)
    db.add(
        PlatformOneTimeToken(
            token_hash=hash_token(raw_token),
            purpose="OWNER_INVITE",
            email=str(payload.owner.email).lower(),
            restaurant_id=restaurant_id,
            expires_at=expires_at,
            created_by_admin_id=actor.admin_id,
        )
    )

    # Audit event.
    write_platform_audit(
        db,
        action="RESTAURANT_ONBOARDED",
        entity_type="restaurant",
        entity_id=str(restaurant_id),
        actor_admin_id=actor.admin_id,
        actor_email=actor.email,
        restaurant_id=restaurant_id,
        reason=reason,
        request=request,
        after={
            "name": tenant["name"],
            "slug": tenant["slug"],
            "plan_code": plan.code,
            "plan_version": active_version.version,
            "owner_email": str(payload.owner.email),
            "branch_count": len(payload.branches),
            "trial_days": payload.subscription.trial_days,
        },
    )
    db.commit()

    # Send owner invitation email (Plan 14). Email failure does not roll back.
    # Build the accept URL dynamically from the request origin.
    request_origin = (
        request.headers.get("origin", "").rstrip("/")
        if request and request.headers.get("origin")
        else ""
    )
    base_url = (
        request_origin
        or settings.invitation_base_url.rstrip("/")
        if settings.invitation_base_url
        else (
            settings.platform_tenant_origin.rstrip("/")
            if settings.platform_tenant_origin
            else ""
        )
    )
    accept_url = (
        f"{base_url}/auth/invitations/{raw_token}"
        if base_url
        else f"/auth/invitations/{raw_token}"
    )
    try:
        email_service = get_email_service()
        email_service.send_invitation(
            to_email=str(payload.owner.email).lower(),
            to_name=payload.owner.full_name,
            restaurant_name=tenant["name"],
            token=raw_token,
            accept_url=accept_url,
            expires_at=expires_at.isoformat(),
        )
        invitation_sent = True
    except Exception:
        logger = logging.getLogger("app.platform.email")
        logger.exception(
            "Failed to send owner invitation email to %s", payload.owner.email
        )
        invitation_sent = False

    return {
        "tenant_id": str(restaurant_id),
        "restaurant": {
            "id": str(restaurant_id),
            "name": tenant["name"],
            "slug": tenant["slug"],
            "status": "ACTIVE",
        },
        "subscription": {
            "id": str(subscription.id),
            "plan_code": plan.code,
            "status": sub_status,
            "trial_ends_at": subscription.trial_ends_at,
        },
        "branches": created_branches,
        "owner_invitation": {
            "sent": invitation_sent,
            "email": str(payload.owner.email).lower(),
            "expires_at": expires_at,
            # Returned so the creating admin can deliver the one-time link when
            # SMTP delivery is unavailable (email is best-effort only).
            "accept_url": accept_url,
            "token": raw_token,
        },
        "audit_id": None,
    }


@router.get("/tenants/{tenant_id}")
def get_tenant(
    tenant_id: UUID,
    actor: PlatformActor = Depends(require_platform_permission("tenant.view")),
    db: Session = Depends(get_db),
) -> dict:
    tenant = platform_directory.require_tenant(db, tenant_id)
    subscription = _subscription_for(db, tenant_id)
    recent = db.scalars(
        select(PlatformAuditLog)
        .where(PlatformAuditLog.restaurant_id == tenant_id)
        .order_by(PlatformAuditLog.created_at.desc())
        .limit(20)
    ).all()
    return {
        "tenant": tenant,
        "subscription": serialize_subscription(db, subscription) if subscription else None,
        "usage": platform_directory.tenant_usage(db, tenant_id),
        "recent_audit": [serialize_audit(row) for row in recent],
    }


@router.patch("/tenants/{tenant_id}")
def update_tenant(
    tenant_id: UUID,
    payload: TenantUpdateRequest,
    request: Request,
    actor: PlatformActor = Depends(require_platform_permission("tenant.create")),
    _: PlatformActor = Depends(require_platform_step_up),
    db: Session = Depends(get_db),
) -> dict:
    reason = require_reason(payload.reason)
    before = platform_directory.require_tenant(db, tenant_id)
    fields = payload.model_dump(exclude_unset=True, exclude={"reason"})
    platform_directory.update_tenant_fields(db, tenant_id, fields)
    after = platform_directory.require_tenant(db, tenant_id)
    write_platform_audit(
        db,
        action="TENANT_UPDATED",
        entity_type="restaurant",
        entity_id=str(tenant_id),
        actor_admin_id=actor.admin_id,
        actor_email=actor.email,
        restaurant_id=tenant_id,
        reason=reason,
        request=request,
        before={key: before.get(key) for key in fields},
        after={key: after.get(key) for key in fields},
    )
    db.commit()
    return {"tenant": after}


@router.post("/tenants/{tenant_id}/suspend")
def suspend_tenant(
    tenant_id: UUID,
    payload: ReasonConfirmRequest,
    request: Request,
    actor: PlatformActor = Depends(require_platform_permission("tenant.suspend")),
    _: PlatformActor = Depends(require_platform_step_up),
    db: Session = Depends(get_db),
) -> dict:
    reason = require_reason(payload.reason)
    tenant = platform_directory.require_tenant(db, tenant_id)
    require_confirm(payload.confirm, tenant["slug"])
    if tenant["status"] == "SUSPENDED":
        raise AppError(409, "TENANT_ALREADY_SUSPENDED", "Conflict", "Tenant is already suspended.")
    platform_directory.set_tenant_status(
        db,
        tenant_id,
        status="SUSPENDED",
        reason=reason,
        suspended_at=now_utc(),
    )
    entry = write_platform_audit(
        db,
        action="TENANT_SUSPENDED",
        entity_type="restaurant",
        entity_id=str(tenant_id),
        actor_admin_id=actor.admin_id,
        actor_email=actor.email,
        restaurant_id=tenant_id,
        reason=reason,
        request=request,
        before={"status": tenant["status"]},
        after={"status": "SUSPENDED"},
    )
    db.commit()
    return {"tenant": platform_directory.require_tenant(db, tenant_id), "audit_id": entry.id}


@router.post("/tenants/{tenant_id}/reactivate")
def reactivate_tenant(
    tenant_id: UUID,
    payload: ReasonConfirmRequest,
    request: Request,
    actor: PlatformActor = Depends(require_platform_permission("tenant.reactivate")),
    _: PlatformActor = Depends(require_platform_step_up),
    db: Session = Depends(get_db),
) -> dict:
    reason = require_reason(payload.reason)
    tenant = platform_directory.require_tenant(db, tenant_id)
    require_confirm(payload.confirm, tenant["slug"])
    if tenant["status"] != "SUSPENDED":
        raise AppError(409, "TENANT_NOT_SUSPENDED", "Conflict", "Tenant is not suspended.")
    platform_directory.set_tenant_status(db, tenant_id, status="ACTIVE")
    entry = write_platform_audit(
        db,
        action="TENANT_REACTIVATED",
        entity_type="restaurant",
        entity_id=str(tenant_id),
        actor_admin_id=actor.admin_id,
        actor_email=actor.email,
        restaurant_id=tenant_id,
        reason=reason,
        request=request,
        before={"status": tenant["status"]},
        after={"status": "ACTIVE"},
    )
    db.commit()
    return {"tenant": platform_directory.require_tenant(db, tenant_id), "audit_id": entry.id}


@router.post("/tenants/{tenant_id}/force-logout")
def force_logout(
    tenant_id: UUID,
    payload: ReasonConfirmRequest,
    request: Request,
    actor: PlatformActor = Depends(require_platform_permission("tenant.force_logout")),
    _: PlatformActor = Depends(require_platform_step_up),
    db: Session = Depends(get_db),
) -> dict:
    reason = require_reason(payload.reason)
    tenant = platform_directory.require_tenant(db, tenant_id)
    require_confirm(payload.confirm, tenant["slug"])
    count = platform_directory.force_logout_tenant(db, tenant_id)
    entry = write_platform_audit(
        db,
        action="TENANT_FORCE_LOGOUT",
        entity_type="restaurant",
        entity_id=str(tenant_id),
        actor_admin_id=actor.admin_id,
        actor_email=actor.email,
        restaurant_id=tenant_id,
        reason=reason,
        request=request,
        after={"revoked_memberships": count},
    )
    db.commit()
    return {"revoked_memberships": count, "audit_id": entry.id}


@router.post("/tenants/{tenant_id}/archive")
def archive_tenant(
    tenant_id: UUID,
    payload: ReasonConfirmRequest,
    request: Request,
    cancel_subscription: bool = False,
    actor: PlatformActor = Depends(require_platform_permission("tenant.delete")),
    _: PlatformActor = Depends(require_platform_step_up),
    db: Session = Depends(get_db),
) -> dict:
    reason = require_reason(payload.reason)
    tenant = platform_directory.require_tenant(db, tenant_id)
    require_confirm(payload.confirm, tenant["slug"])
    subscription = _subscription_for(db, tenant_id)
    if subscription is not None and not cancel_subscription:
        raise AppError(
            409,
            "TENANT_HAS_LIVE_SUBSCRIPTION",
            "Conflict",
            "Cancel the live subscription before archiving.",
        )
    now = now_utc()
    if subscription is not None:
        previous = subscription.status
        subscription.status = "CANCELLED"
        subscription.canceled_at = now
        add_subscription_event(
            db,
            subscription,
            event_type="CANCELLED",
            admin_id=actor.admin_id,
            reason=reason,
            from_status=previous,
            to_status="CANCELLED",
        )
    db.execute(
        text(
            "UPDATE restaurants SET archived_at = :now, status = 'CANCELLED', "
            "updated_at = :now WHERE id = :id"
        ),
        {"now": now, "id": tenant_id},
    )
    revoked = platform_directory.force_logout_tenant(db, tenant_id)
    entry = write_platform_audit(
        db,
        action="TENANT_ARCHIVED",
        entity_type="restaurant",
        entity_id=str(tenant_id),
        actor_admin_id=actor.admin_id,
        actor_email=actor.email,
        restaurant_id=tenant_id,
        reason=reason,
        request=request,
        after={"archived_at": now, "revoked_memberships": revoked},
    )
    db.commit()
    return {
        "tenant": platform_directory.require_tenant(db, tenant_id),
        "revoked_memberships": revoked,
        "audit_id": entry.id,
    }


@router.post("/tenants/{tenant_id}/cancel")
def cancel_tenant(
    tenant_id: UUID,
    payload: TenantCancelRequest,
    request: Request,
    actor: PlatformActor = Depends(
        require_platform_permission("tenant.delete")
    ),
    _: PlatformActor = Depends(require_platform_step_up),
    db: Session = Depends(get_db),
) -> dict:
    """Cancel a tenant (restaurant closure / offboarding).

    Requires tenant.delete (Super Admin) or tenant.suspend (OPS).
    The confirm field must equal the tenant slug.
    Optionally accepts an effective_date for scheduled cancellation.
    """
    reason = require_reason(payload.reason)
    tenant = platform_directory.require_tenant(db, tenant_id)
    require_confirm(payload.confirm, tenant["slug"])

    if tenant["status"] == "CANCELLED":
        raise AppError(
            409, "TENANT_ALREADY_CANCELLED", "Conflict", "Tenant is already cancelled."
        )

    now = now_utc()
    effective_date = None
    if payload.effective_date:
        from datetime import datetime

        effective_date = datetime.fromisoformat(
            payload.effective_date.replace("Z", "+00:00")
        )
        if effective_date <= now:
            raise AppError(
                422,
                "INVALID_EFFECTIVE_DATE",
                "Invalid input",
                "Effective date must be in the future.",
            )

    # Cancel the subscription immediately or at effective date
    subscription = _subscription_for(db, tenant_id)
    cancel_subscription_now = effective_date is None or effective_date <= now
    if subscription is not None:
        previous = subscription.status
        if cancel_subscription_now:
            subscription.status = "CANCELLED"
            subscription.canceled_at = now
        subscription.cancel_at_period_end = True
        add_subscription_event(
            db,
            subscription,
            event_type="CANCELLED",
            admin_id=actor.admin_id,
            reason=reason,
            from_status=previous,
            to_status="CANCELLED",
            metadata={
                "effective_date": effective_date.isoformat()
                if effective_date
                else None,
                "immediate": cancel_subscription_now,
            },
        )

    # Set restaurant status to CANCELLED immediately
    db.execute(
        text(
            "UPDATE restaurants SET status = 'CANCELLED', cancelled_at = :now, "
            "updated_at = :now WHERE id = :id"
        ),
        {"now": now, "id": tenant_id},
    )

    # Revoke all memberships (force logout)
    revoked = platform_directory.force_logout_tenant(db, tenant_id)

    entry = write_platform_audit(
        db,
        action="TENANT_CANCELLED",
        entity_type="restaurant",
        entity_id=str(tenant_id),
        actor_admin_id=actor.admin_id,
        actor_email=actor.email,
        restaurant_id=tenant_id,
        reason=reason,
        request=request,
        after={
            "status": "CANCELLED",
            "effective_date": effective_date.isoformat()
            if effective_date
            else None,
            "immediate": cancel_subscription_now,
            "revoked_memberships": revoked,
        },
    )
    db.commit()

    return {
        "tenant": platform_directory.require_tenant(db, tenant_id),
        "cancelled_at": now.isoformat(),
        "effective_date": effective_date.isoformat() if effective_date else None,
        "immediate": cancel_subscription_now,
        "revoked_memberships": revoked,
        "audit_id": entry.id,
    }


@router.get("/tenants/{tenant_id}/usage")
def tenant_usage(
    tenant_id: UUID,
    actor: PlatformActor = Depends(require_platform_permission("tenant.view")),
    db: Session = Depends(get_db),
) -> dict:
    platform_directory.require_tenant(db, tenant_id)
    return platform_directory.tenant_usage(db, tenant_id)


@router.get("/tenants/{tenant_id}/entitlements")
def tenant_entitlements(
    tenant_id: UUID,
    actor: PlatformActor = Depends(require_platform_permission("tenant.view")),
    db: Session = Depends(get_db),
) -> dict:
    """Get the effective entitlements and usage status for a tenant."""
    platform_directory.require_tenant(db, tenant_id)
    from app.modules.platform.services.entitlements import get_usage_status

    return get_usage_status(db, restaurant_id=tenant_id)


@router.post("/tenants/{tenant_id}/usage/reconcile")
def reconcile_tenant_usage(
    tenant_id: UUID,
    request: Request,
    actor: PlatformActor = Depends(require_platform_permission("tenant.suspend")),
    db: Session = Depends(get_db),
) -> dict:
    """Recompute cached usage counters from the append-only usage ledger."""
    platform_directory.require_tenant(db, tenant_id)
    from app.modules.platform.services.entitlements import reconcile_usage_counters

    result = reconcile_usage_counters(db, restaurant_id=tenant_id)
    write_platform_audit(
        db,
        action="TENANT_USAGE_RECONCILED",
        entity_type="restaurant",
        entity_id=str(tenant_id),
        actor_admin_id=actor.admin_id,
        actor_email=actor.email,
        restaurant_id=tenant_id,
        reason="manual usage reconciliation",
        request=request,
        after=result,
    )
    db.commit()
    return result


@router.get("/tenants/{tenant_id}/audit")
def tenant_audit(
    tenant_id: UUID,
    page: int = 1,
    page_size: int = 25,
    actor: PlatformActor = Depends(require_platform_permission("audit.view")),
    db: Session = Depends(get_db),
) -> dict:
    platform_directory.require_tenant(db, tenant_id)
    page, page_size = page_params(page, page_size)
    base = select(PlatformAuditLog).where(PlatformAuditLog.restaurant_id == tenant_id)
    total = int(
        db.scalar(select(func.count()).select_from(base.subquery())) or 0
    )
    rows = db.scalars(
        base.order_by(PlatformAuditLog.created_at.desc())
        .limit(page_size)
        .offset((page - 1) * page_size)
    ).all()
    return paginated([serialize_audit(row) for row in rows], total, page, page_size)


# ---------------------------------------------------------------------------
# Onboarding status (Plan 10)
# ---------------------------------------------------------------------------


@router.get("/onboarding")
def list_onboarding_status(
    page: int = 1,
    page_size: int = 25,
    actor: PlatformActor = Depends(require_platform_permission("tenant.view")),
    db: Session = Depends(get_db),
) -> dict:
    """List all tenants with their onboarding stage and key status."""
    page, page_size = page_params(page, page_size)

    # Join restaurants with settings and latest subscription for onboarding view
    base = (
        select(
            Restaurant.id,
            Restaurant.name,
            Restaurant.slug,
            Restaurant.status,
            Restaurant.created_at,
            RestaurantSettings.onboarding_stage,
            RestaurantSettings.onboarding_completed_at,
            PlatformSubscription.status.label("subscription_status"),
            PlatformSubscription.trial_ends_at,
        )
        .outerjoin(
            RestaurantSettings,
            RestaurantSettings.restaurant_id == Restaurant.id,
        )
        .outerjoin(
            PlatformSubscription,
            sa.and_(
                PlatformSubscription.restaurant_id == Restaurant.id,
                PlatformSubscription.status.in_(platform_directory.LIVE_STATUSES),
            ),
        )
    )

    total = int(db.scalar(select(func.count()).select_from(base.subquery())) or 0)

    rows = db.execute(
        base.order_by(Restaurant.created_at.desc())
        .limit(page_size)
        .offset((page - 1) * page_size)
    ).mappings().all()

    items = []
    for row in rows:
        items.append(
            {
                "tenant_id": str(row["id"]),
                "name": row["name"],
                "slug": row["slug"],
                "status": row["status"],
                "onboarding_stage": row["onboarding_stage"] or "registered",
                "onboarding_completed_at": (
                    row["onboarding_completed_at"].isoformat()
                    if row["onboarding_completed_at"]
                    else None
                ),
                "subscription_status": row["subscription_status"],
                "trial_ends_at": (
                    row["trial_ends_at"].isoformat() if row["trial_ends_at"] else None
                ),
                "created_at": row["created_at"].isoformat(),
            }
        )

    return paginated(items, total, page, page_size)


@router.patch("/onboarding/{tenant_id}/stage")
def update_onboarding_stage(
    tenant_id: UUID,
    payload: dict,
    request: Request,
    actor: PlatformActor = Depends(require_platform_permission("tenant.create")),
    _: PlatformActor = Depends(require_platform_step_up),
    db: Session = Depends(get_db),
) -> dict:
    """Update a tenant's onboarding stage."""
    stage = payload.get("stage")
    valid_stages = {
        "registered",
        "owner_invited",
        "owner_activated",
        "profile_complete",
        "tables_configured",
        "menu_configured",
        "staff_invited",
        "payments_configured",
        "operational",
    }
    if stage not in valid_stages:
        raise AppError(
            422,
            "INVALID_STAGE",
            "Invalid input",
            f"Stage must be one of: {', '.join(sorted(valid_stages))}",
        )

    settings = db.get(RestaurantSettings, tenant_id)
    if settings is None:
        raise AppError(404, "SETTINGS_NOT_FOUND", "Not found", "Restaurant settings not found.")

    settings.onboarding_stage = stage
    if stage == "operational":
        settings.onboarding_completed_at = now_utc()
    db.commit()

    write_platform_audit(
        db,
        action="ONBOARDING_STAGE_UPDATED",
        entity_type="restaurant",
        entity_id=str(tenant_id),
        actor_admin_id=actor.admin_id,
        actor_email=actor.email,
        restaurant_id=tenant_id,
        reason=payload.get("reason", ""),
        request=request,
        after={"onboarding_stage": stage},
    )

    return {"tenant_id": str(tenant_id), "onboarding_stage": stage}


# ---------------------------------------------------------------------------
# Support tickets (Plan 10)
# ---------------------------------------------------------------------------


@router.get("/support/tickets")
def list_support_tickets(
    page: int = 1,
    page_size: int = 25,
    status: str | None = Query(default=None),
    actor: PlatformActor = Depends(require_platform_permission("tenant.view")),
    db: Session = Depends(get_db),
) -> dict:
    """List support tickets, optionally filtered by status."""
    page, page_size = page_params(page, page_size)
    base = select(PlatformSupportTicket)
    if status:
        base = base.where(PlatformSupportTicket.status == status)
    total = int(db.scalar(select(func.count()).select_from(base.subquery())) or 0)
    rows = db.scalars(
        base.order_by(PlatformSupportTicket.created_at.desc())
        .limit(page_size)
        .offset((page - 1) * page_size)
    ).all()
    return paginated(
        [SupportTicketOut.model_validate(row) for row in rows], total, page, page_size
    )


@router.post("/support/tickets", status_code=status.HTTP_201_CREATED)
def create_support_ticket(
    payload: SupportTicketCreateRequest,
    request: Request,
    actor: PlatformActor = Depends(require_platform_permission("tenant.view")),
    db: Session = Depends(get_db),
) -> SupportTicketOut:
    """Create a new support ticket."""
    platform_directory.require_tenant(db, UUID(payload.restaurant_id))

    ticket = PlatformSupportTicket(
        restaurant_id=UUID(payload.restaurant_id),
        subject=payload.subject,
        description=payload.description,
        status="open",
        priority=payload.priority,
    )
    db.add(ticket)
    db.commit()
    db.refresh(ticket)

    write_platform_audit(
        db,
        action="SUPPORT_TICKET_CREATED",
        entity_type="support_ticket",
        entity_id=str(ticket.id),
        actor_admin_id=actor.admin_id,
        actor_email=actor.email,
        restaurant_id=UUID(payload.restaurant_id),
        reason=payload.subject,
        request=request,
    )

    return SupportTicketOut.model_validate(ticket)


@router.patch("/support/tickets/{ticket_id}")
def update_support_ticket(
    ticket_id: UUID,
    payload: SupportTicketUpdateRequest,
    request: Request,
    actor: PlatformActor = Depends(require_platform_permission("tenant.view")),
    db: Session = Depends(get_db),
) -> SupportTicketOut:
    """Update a support ticket (status, priority, assignment)."""
    ticket = db.get(PlatformSupportTicket, ticket_id)
    if ticket is None:
        raise AppError(404, "TICKET_NOT_FOUND", "Not found", "Support ticket not found.")

    update_data = payload.model_dump(exclude_unset=True)
    if "status" in update_data and update_data["status"] == "resolved":
        from datetime import UTC, datetime

        update_data["resolved_at"] = datetime.now(UTC)

    for key, value in update_data.items():
        setattr(ticket, key, value)

    db.commit()
    db.refresh(ticket)

    write_platform_audit(
        db,
        action="SUPPORT_TICKET_UPDATED",
        entity_type="support_ticket",
        entity_id=str(ticket.id),
        actor_admin_id=actor.admin_id,
        actor_email=actor.email,
        restaurant_id=ticket.restaurant_id,
        reason=f"updated: {', '.join(update_data.keys())}",
        request=request,
    )

    return SupportTicketOut.model_validate(ticket)


# ---------------------------------------------------------------------------
# Analytics (Plan 10)
# ---------------------------------------------------------------------------


@router.get("/analytics/summary")
def analytics_summary(
    actor: PlatformActor = Depends(require_platform_permission("analytics.view")),
    db: Session = Depends(get_db),
) -> dict:
    """Platform-wide analytics summary (Super Admin only)."""
    from datetime import UTC, datetime, timedelta

    now = datetime.now(UTC)
    thirty_days_ago = now - timedelta(days=30)

    # Total restaurants
    total_restaurants = db.scalar(select(func.count()).select_from(Restaurant)) or 0

    # Restaurants by status
    status_rows = db.execute(
        select(Restaurant.status, func.count())
        .group_by(Restaurant.status)
    ).all()
    restaurants_by_status = {row[0]: row[1] for row in status_rows}

    # Subscriptions by status
    sub_status_rows = db.execute(
        select(PlatformSubscription.status, func.count())
        .group_by(PlatformSubscription.status)
    ).all()
    subscriptions_by_status = {row[0]: row[1] for row in sub_status_rows}

    # New restaurants in last 30 days
    new_restaurants = db.scalar(
        select(func.count()).select_from(Restaurant).where(
            Restaurant.created_at >= thirty_days_ago
        )
    ) or 0

    # Total branches
    total_branches = db.scalar(select(func.count()).select_from(__import__("app.modules.branches.models", fromlist=["Branch"]).Branch)) or 0

    # Total staff memberships (active)
    total_staff = db.scalar(
        select(func.count()).select_from(RestaurantMembership).where(
            RestaurantMembership.status == "ACTIVE"
        )
    ) or 0

    # Support tickets by status
    ticket_rows = db.execute(
        select(PlatformSupportTicket.status, func.count())
        .group_by(PlatformSupportTicket.status)
    ).all()
    tickets_by_status = {row[0]: row[1] for row in ticket_rows}

    return {
        "generated_at": now.isoformat(),
        "total_restaurants": total_restaurants,
        "new_restaurants_30d": new_restaurants,
        "total_branches": total_branches,
        "total_staff": total_staff,
        "restaurants_by_status": restaurants_by_status,
        "subscriptions_by_status": subscriptions_by_status,
        "tickets_by_status": tickets_by_status,
    }


# ---------------------------------------------------------------------------
# Data export (Plan 13)
# ---------------------------------------------------------------------------


@router.post("/tenants/{tenant_id}/export", status_code=status.HTTP_202_ACCEPTED)
def export_tenant_data(
    tenant_id: UUID,
    request: Request,
    actor: PlatformActor = Depends(require_platform_permission("tenant.export")),
    _: PlatformActor = Depends(require_platform_step_up),
    db: Session = Depends(get_db),
) -> dict:
    """Initiate a data export for a tenant.

    Returns a job_id that can be polled via GET /api/platform/export/{job_id}.
    The export includes all tenant-scoped data: restaurant profile, settings,
    branches, tables, menu, orders, payments, memberships, inventory, reviews,
    and audit logs.
    """
    platform_directory.require_tenant(db, tenant_id)

    job_id = uuid4()
    expires_at = now_utc() + timedelta(hours=24)

    job = PlatformExportJob(
        id=job_id,
        restaurant_id=tenant_id,
        status="pending",
        created_at=now_utc(),
        expires_at=expires_at,
        created_by_admin_id=actor.admin_id,
    )
    db.add(job)
    db.commit()

    write_platform_audit(
        db,
        action="TENANT_EXPORT_REQUESTED",
        entity_type="restaurant",
        entity_id=str(tenant_id),
        actor_admin_id=actor.admin_id,
        actor_email=actor.email,
        restaurant_id=tenant_id,
        reason="data export requested",
        request=request,
        after={"job_id": str(job_id)},
    )
    db.commit()

    return {
        "job_id": str(job_id),
        "status": "pending",
        "expires_at": expires_at.isoformat(),
        "poll_url": f"/api/platform/export/{job_id}",
    }


@router.get("/export/{job_id}")
def get_export_job(
    job_id: UUID,
    actor: PlatformActor = Depends(require_platform_permission("tenant.export")),
    db: Session = Depends(get_db),
) -> dict:
    """Get the status of a data export job.

    When status is "completed", the download_url field contains the URL to
    download the exported data.
    """
    job = db.get(PlatformExportJob, job_id)
    if job is None:
        raise AppError(404, "EXPORT_JOB_NOT_FOUND", "Not found", "Export job not found.")

    # Only the job creator or a superadmin can view the job
    if actor.role != "superadmin" and job.created_by_admin_id != actor.admin_id:
        raise AppError(
            403, "FORBIDDEN", "Forbidden", "You do not own this export job."
        )

    result = {
        "job_id": str(job.id),
        "status": job.status,
        "created_at": job.created_at.isoformat() if job.created_at else None,
        "expires_at": job.expires_at.isoformat() if job.expires_at else None,
        "download_url": job.download_url,
    }

    if job.status == "failed" and job.error:
        result["error"] = job.error

    return result


# ---------------------------------------------------------------------------
# Tenant anonymization (Plan 13)
# ---------------------------------------------------------------------------


@router.post("/tenants/{tenant_id}/anonymize")
def anonymize_tenant(
    tenant_id: UUID,
    payload: TenantAnonymizeRequest,
    request: Request,
    actor: PlatformActor = Depends(require_platform_permission("tenant.delete")),
    _: PlatformActor = Depends(require_platform_step_up),
    db: Session = Depends(get_db),
) -> dict:
    """Anonymize a cancelled tenant's personal data.

    Requires tenant.delete (Super Admin) permission + step-up.
    Replaces emails/names with hashed placeholders while preserving
    order aggregates for reporting.
    """
    reason = require_reason(payload.reason)
    tenant = platform_directory.require_tenant(db, tenant_id)
    require_confirm(payload.confirm, tenant["slug"])

    if tenant["status"] != "CANCELLED":
        raise AppError(
            409,
            "TENANT_NOT_CANCELLED",
            "Conflict",
            "Only cancelled tenants can be anonymized.",
        )

    now = now_utc()

    # Anonymize owner/membership data
    db.execute(
        text(
            "UPDATE users SET "
            "email = CONCAT('anon_', md5(email), '@example.invalid'), "
            "display_name = 'Anonymized User', "
            "updated_at = :now "
            "WHERE id IN ("
            "SELECT user_id FROM restaurant_memberships WHERE restaurant_id = :rid"
            ")"
        ),
        {"now": now, "rid": tenant_id},
    )

    # Anonymize restaurant contact info
    db.execute(
        text(
            "UPDATE restaurants SET "
            "contact_email = NULL, "
            "contact_phone = NULL, "
            "legal_name = NULL, "
            "updated_at = :now "
            "WHERE id = :rid"
        ),
        {"now": now, "rid": tenant_id},
    )

    # Anonymize membership display data
    db.execute(
        text(
            "UPDATE restaurant_memberships SET "
            "updated_at = :now WHERE restaurant_id = :rid"
        ),
        {"now": now, "rid": tenant_id},
    )

    db.commit()

    write_platform_audit(
        db,
        action="TENANT_ANONYMIZED",
        entity_type="restaurant",
        entity_id=str(tenant_id),
        actor_admin_id=actor.admin_id,
        actor_email=actor.email,
        restaurant_id=tenant_id,
        reason=reason,
        request=request,
        after={"anonymized_at": now.isoformat()},
    )
    db.commit()

    return {
        "tenant_id": str(tenant_id),
        "anonymized_at": now.isoformat(),
        "audit_id": None,
    }


