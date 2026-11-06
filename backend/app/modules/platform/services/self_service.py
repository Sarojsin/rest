"""Self-service registration service (Plan 04).

Allows restaurant owners to register themselves, select a plan, and start a
trial or purchase without platform admin involvement. Supports both automatic
approval (dev/test) and admin review (production).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import secrets
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.security import hash_password, hash_token, new_token
from app.modules.platform.models import (
    PlatformPlan,
    PlatformPlanVersion,
    PlatformSubscription,
    PlatformSubscriptionTrialHistory,
)
from app.modules.platform.services.audit import write_platform_audit
from app.modules.platform.services.bootstrap import seed_platform_billing_dev
from app.shared.errors import AppError

SELF_SERVICE_STATUSES = ("PENDING", "APPROVED", "REJECTED", "CANCELLED")


def require_platform_setting(db: Session, key: str, default=None):
    """Get a platform setting value."""
    row = db.execute(
        text("SELECT value_json FROM platform_settings WHERE key = :key"),
        {"key": key},
    ).fetchone()
    if row is not None:
        return row[0]
    return default


def require_self_service_enabled(db: Session) -> bool:
    """Check if self-service registration is enabled."""
    return bool(require_platform_setting(db, "platform.self_service_enabled", False))


def require_tenant_creation_enabled(db: Session) -> bool:
    """Check if self-service tenant creation is enabled."""
    return bool(require_platform_setting(db, "platform.self_service_tenant_creation", True))


def get_public_plans(db: Session) -> list[dict]:
    """Get all active, public plans for self-service selection."""
    plans = db.execute(
        text(
            """
            SELECT p.id, p.code, p.name, p.description, p.price_monthly_minor,
                   p.price_annual_minor, p.currency_code, p.trial_days,
                   p.status, p.is_public, p.sort_order,
                   pv.version, pv.price_monthly_minor as version_price_monthly,
                   pv.price_annual_minor as version_price_annual,
                   pv.trial_days as version_trial_days,
                   pv.effective_from, pv.is_active as version_active
            FROM platform_plans p
            LEFT JOIN LATERAL (
                SELECT * FROM platform_plan_versions pv
                WHERE pv.plan_id = p.id AND pv.is_active = true
                ORDER BY pv.version DESC
                LIMIT 1
            ) pv ON true
            WHERE p.status = 'ACTIVE' AND p.is_public = true
            ORDER BY p.sort_order, p.name
        """
        )
    ).all()

    plans_list = []
    for row in plans:
        plans_list.append(
            {
                "id": str(row.id),
                "code": row.code,
                "name": row.name,
                "description": row.description,
                "price_monthly_minor": row.price_monthly_minor,
                "price_annual_minor": row.price_annual_minor,
                "currency_code": row.currency_code,
                "trial_days": row.trial_days,
                "status": row.status,
                "is_public": row.is_public,
                "sort_order": row.sort_order,
                "version": row.version,
                "version_price_monthly": row.version_price_monthly,
                "version_price_annual": row.version_price_annual,
                "version_trial_days": row.version_trial_days,
                "effective_from": row.effective_from,
                "version_active": row.version_active,
            }
        )
    return plans_list


def create_self_service_registration(
    db: Session,
    *,
    restaurant_name: str,
    restaurant_slug: str,
    owner_email: str,
    owner_name: str,
    owner_phone: str | None,
    plan_code: str,
    trial_days: int,
    contact_email: str | None,
    contact_phone: str | None,
    legal_name: str | None,
    timezone: str,
    currency_code: str,
    source: str | None,
    reason: str,
    auto_approve: bool = False,
) -> dict:
    """Create a self-service tenant registration application.

    If auto_approve is True, the tenant and subscription are created immediately.
    Otherwise, the application is created in PENDING status for admin review.
    """
    # Check self-service is enabled
    if not require_self_service_enabled(db):
        raise AppError(
            403,
            "SELF_SERVICE_DISABLED",
            "Forbidden",
            "Self-service registration is not enabled.",
        )

    # Validate plan
    plan = db.scalar(
        __import__("sqlalchemy").select(PlatformPlan).where(
            PlatformPlan.code == plan_code,
            PlatformPlan.status == "ACTIVE",
            PlatformPlan.is_public == True,
        )
    )
    if plan is None:
        raise AppError(
            404,
            "PLAN_NOT_FOUND",
            "Not found",
            "Plan not found or not available for self-service.",
        )

    # Get active plan version
    plan_version = db.scalar(
        __import__("sqlalchemy").select(PlatformPlanVersion).where(
            PlatformPlanVersion.plan_id == plan.id,
            PlatformPlanVersion.is_active == True,
        )
    )
    if plan_version is None:
        raise AppError(
            409,
            "PLAN_VERSION_NOT_ACTIVE",
            "Conflict",
            "No active plan version for this plan.",
        )

    # Check slug uniqueness
    slug_exists = db.scalar(
        text("SELECT 1 FROM restaurants WHERE slug = :slug"),
        {"slug": restaurant_slug.strip().lower()},
    )
    if slug_exists:
        raise AppError(
            409,
            "SLUG_TAKEN",
            "Conflict",
            "That tenant slug is already taken.",
        )

    # Check owner email uniqueness
    email_exists = db.scalar(
        text("SELECT 1 FROM users WHERE email = :email"),
        {"email": owner_email.strip().lower()},
    )
    if email_exists:
        raise AppError(
            409,
            "OWNER_EMAIL_EXISTS",
            "Conflict",
            "An account with that email already exists.",
        )

    # Check existing self-service application. ``restaurant_slug`` and
    # ``owner_email`` are unique on this table for every status, so a clear
    # 409 must be returned before the INSERT rather than surfacing a
    # UniqueViolation from the database.
    existing_slug = db.scalar(
        text(
            "SELECT 1 FROM self_service_registrations "
            "WHERE restaurant_slug = :slug"
        ),
        {"slug": restaurant_slug.strip().lower()},
    )
    if existing_slug:
        raise AppError(
            409,
            "APPLICATION_EXISTS",
            "Conflict",
            "An application for this slug already exists.",
        )

    existing_email = db.scalar(
        text(
            "SELECT 1 FROM self_service_registrations "
            "WHERE owner_email = :email"
        ),
        {"email": owner_email.strip().lower()},
    )
    if existing_email:
        raise AppError(
            409,
            "OWNER_EMAIL_EXISTS",
            "Conflict",
            "An application with that email already exists.",
        )

    now = datetime.now(UTC)
    status = "APPROVED" if auto_approve else "PENDING"

    registration_id = uuid4()

    db.execute(
        text(
            """
            INSERT INTO self_service_registrations
                (id, restaurant_id, restaurant_name, restaurant_slug,
                 owner_email, owner_name, owner_phone, plan_code, trial_days,
                 status, contact_email, contact_phone, legal_name,
                 timezone, currency_code, source, reason, created_at, updated_at)
            VALUES
                (:id, :restaurant_id, :restaurant_name, :restaurant_slug,
                 :owner_email, :owner_name, :owner_phone, :plan_code, :trial_days,
                 :status, :contact_email, :contact_phone, :legal_name,
                 :timezone, :currency_code, :source, :reason, :now, :now)
        """
        ),
        {
            "id": registration_id,
            "restaurant_id": None,
            "restaurant_name": restaurant_name.strip(),
            "restaurant_slug": restaurant_slug.strip().lower(),
            "owner_email": owner_email.strip().lower(),
            "owner_name": owner_name.strip(),
            "owner_phone": owner_phone,
            "plan_code": plan_code,
            "trial_days": trial_days,
            "status": status,
            "contact_email": contact_email,
            "contact_phone": contact_phone,
            "legal_name": legal_name,
            "timezone": timezone,
            "currency_code": currency_code,
            "source": source,
            "reason": reason,
            "now": now,
        },
    )

    if auto_approve:
        # Create the restaurant and subscription immediately
        restaurant_id = uuid4()
        user_id = uuid4()
        membership_id = uuid4()

        db.execute(
            text(
                """
                INSERT INTO restaurants
                    (id, name, slug, status, timezone, currency_code,
                     contact_email, contact_phone, legal_name, created_at, updated_at)
                VALUES
                    (:id, :name, :slug, 'ACTIVE', :timezone, :currency_code,
                     :contact_email, :contact_phone, :legal_name, :now, :now)
            """
            ),
            {
                "id": restaurant_id,
                "name": restaurant_name.strip(),
                "slug": restaurant_slug.strip().lower(),
                "timezone": timezone,
                "currency_code": currency_code,
                "contact_email": contact_email,
                "contact_phone": contact_phone,
                "legal_name": legal_name,
                "now": now,
            },
        )

        # Create restaurant settings
        db.execute(
            text(
                """
                INSERT INTO restaurant_settings
                    (restaurant_id, locale, business_day_start_local, tax_rate_bps,
                     receipt_header, receipt_footer, qr_ordering_enabled,
                     online_payments_enabled, settings_version, customer_subdomain,
                     brand_logo_url, brand_accent_hex, created_at, updated_at)
                VALUES
                    (:rid, 'en-NP', '05:00', 1300, :name, 'Thank you', true,
                     false, 1, :slug, '', '', :now, :now)
            """
            ),
            {
                "rid": restaurant_id,
                "name": restaurant_name.strip(),
                "slug": restaurant_slug.strip().lower(),
                "now": now,
            },
        )

        # Create invited owner
        db.execute(
            text(
                """
                INSERT INTO users
                    (id, email, password_hash, display_name, status, created_at, updated_at)
                VALUES
                    (:id, :email, :password_hash, :display_name, 'INVITED', :now, :now)
            """
            ),
            {
                "id": user_id,
                "email": owner_email.strip().lower(),
                "password_hash": hash_password(secrets.token_urlsafe(48)),
                "display_name": owner_name.strip() or owner_email.split("@")[0],
                "now": now,
            },
        )

        # Create owner membership
        db.execute(
            text(
                """
                INSERT INTO restaurant_memberships
                    (id, restaurant_id, user_id, role, status, token_version,
                     created_at, updated_at)
                VALUES
                    (:id, :rid, :uid, 'owner', 'ACTIVE', 0, :now, :now)
            """
            ),
            {
                "id": membership_id,
                "rid": restaurant_id,
                "uid": user_id,
                "now": now,
            },
        )

        # Create subscription
        trial_ends_at = now + timedelta(days=trial_days) if trial_days else None
        sub_status = "TRIALING" if trial_days > 0 else "ACTIVE"
        db.execute(
            text(
                """
                INSERT INTO platform_subscriptions
                    (id, restaurant_id, plan_id, plan_version_id, status,
                     trial_ends_at, current_period_start, current_period_end,
                     cancel_at_period_end, price_snapshot_minor, currency_snapshot,
                     billing_interval_snapshot, created_by_admin_id, created_at, updated_at)
                VALUES
                    (:id, :rid, :pid, :pvid, :status, :trial_ends_at,
                     :cps, :cpe, :cancel_at_period_end, :price_snapshot,
                     :currency_snapshot, :billing_interval, NULL, :now, :now)
            """
            ),
            {
                "id": uuid4(),
                "rid": restaurant_id,
                "pid": plan.id,
                "pvid": plan_version.id,
                "status": sub_status,
                "trial_ends_at": trial_ends_at,
                "cps": now,
                "cpe": now + timedelta(days=trial_days or 30),
                "cancel_at_period_end": False,
                "price_snapshot": plan_version.price_monthly_minor,
                "currency_snapshot": plan_version.currency_code,
                "billing_interval": "MONTHLY",
                "now": now,
            },
        )

        # Create invitation token
        raw_token = new_token(32)
        db.execute(
            text(
                """
                INSERT INTO platform_one_time_tokens
                    (token_hash, purpose, email, restaurant_id, expires_at,
                     created_by_admin_id, created_at)
                VALUES
                    (:token_hash, 'OWNER_INVITE', :email, :rid, :expires_at,
                     NULL, :now)
            """
            ),
            {
                "token_hash": hash_token(raw_token),
                "email": owner_email.strip().lower(),
                "rid": restaurant_id,
                "expires_at": now + timedelta(hours=72),
                "now": now,
            },
        )

        # Update registration
        db.execute(
            text(
                """
                UPDATE self_service_registrations
                SET restaurant_id = :rid, updated_at = :now
                WHERE id = :reg_id
            """
            ),
            {"rid": restaurant_id, "now": now, "reg_id": registration_id},
        )

        db.commit()

        return {
            "id": str(registration_id),
            "status": status,
            "restaurant_id": str(restaurant_id),
            "owner_email": owner_email.strip().lower(),
            "invitation_token": raw_token,
            "invitation_expires_at": now + timedelta(hours=72),
        }

    db.commit()

    return {
        "id": str(registration_id),
        "status": status,
        "restaurant_id": None,
        "owner_email": owner_email.strip().lower(),
        "invitation_token": None,
        "invitation_expires_at": None,
    }


def get_self_service_registration(
    db: Session, registration_id: UUID
) -> dict | None:
    """Get a self-service registration by ID."""
    row = db.execute(
        text(
            "SELECT * FROM self_service_registrations WHERE id = :id"
        ),
        {"id": registration_id},
    ).mappings().first()
    if row is None:
        return None
    return dict(row)


def list_self_service_registrations(
    db: Session, status: str | None = None, page: int = 1, page_size: int = 25
) -> tuple[list[dict], int]:
    """List self-service registrations with optional status filter."""
    where = ""
    params = {}
    if status:
        where = "WHERE status = :status"
        params["status"] = status

    count_sql = f"SELECT count(*) FROM self_service_registrations {where}"
    total = int(db.execute(text(count_sql), params).scalar() or 0)

    offset = (page - 1) * page_size
    sql = f"""
        SELECT * FROM self_service_registrations {where}
        ORDER BY created_at DESC
        LIMIT :limit OFFSET :offset
    """
    rows = db.execute(
        text(sql), {**params, "limit": page_size, "offset": offset}
    ).mappings().all()

    return [dict(r) for r in rows], total


def approve_self_service_registration(
    db: Session,
    *,
    registration_id: UUID,
    admin_id: UUID,
    reason: str,
    request=None,
) -> dict:
    """Approve a pending self-service registration and create the tenant."""

    reg = db.execute(
        text("SELECT * FROM self_service_registrations WHERE id = :id"),
        {"id": registration_id},
    ).mappings().first()
    if reg is None:
        raise AppError(404, "REGISTRATION_NOT_FOUND", "Not found", "Registration not found.")
    if reg["status"] != "PENDING":
        raise AppError(
            409,
            "REGISTRATION_NOT_PENDING",
            "Conflict",
            f"Registration is already {reg['status']}.",
        )

    plan = db.scalar(
        __import__("sqlalchemy").select(PlatformPlan).where(
            PlatformPlan.code == reg["plan_code"],
            PlatformPlan.status == "ACTIVE",
        )
    )
    if plan is None:
        raise AppError(
            404,
            "PLAN_NOT_FOUND",
            "Not found",
            "Plan not found.",
        )

    plan_version = db.scalar(
        __import__("sqlalchemy").select(PlatformPlanVersion).where(
            PlatformPlanVersion.plan_id == plan.id,
            PlatformPlanVersion.is_active == True,
        )
    )
    if plan_version is None:
        raise AppError(
            409,
            "PLAN_VERSION_NOT_ACTIVE",
            "Conflict",
            "No active plan version.",
        )

    # Check slug still available
    slug_exists = db.scalar(
        text("SELECT 1 FROM restaurants WHERE slug = :slug"),
        {"slug": reg["restaurant_slug"]},
    )
    if slug_exists:
        raise AppError(
            409,
            "SLUG_TAKEN",
            "Conflict",
            "That tenant slug is now taken.",
        )

    # Create the restaurant
    restaurant_id = uuid4()
    user_id = uuid4()
    membership_id = uuid4()
    now = datetime.now(UTC)

    db.execute(
        text(
            """
            INSERT INTO restaurants
                (id, name, slug, status, timezone, currency_code,
                 contact_email, contact_phone, legal_name, created_at, updated_at)
            VALUES
                (:id, :name, :slug, 'ACTIVE', :timezone, :currency_code,
                 :contact_email, :contact_phone, :legal_name, :now, :now)
        """
        ),
        {
            "id": restaurant_id,
            "name": reg["restaurant_name"],
            "slug": reg["restaurant_slug"],
            "timezone": reg["timezone"],
            "currency_code": reg["currency_code"],
            "contact_email": reg["contact_email"],
            "contact_phone": reg["contact_phone"],
            "legal_name": reg["legal_name"],
            "now": now,
        },
    )

    # Create restaurant settings
    db.execute(
        text(
            """
            INSERT INTO restaurant_settings
                (restaurant_id, locale, business_day_start_local, tax_rate_bps,
                 receipt_header, receipt_footer, qr_ordering_enabled,
                 online_payments_enabled, settings_version, customer_subdomain,
                 brand_logo_url, brand_accent_hex, created_at, updated_at)
            VALUES
                (:rid, 'en-NP', '05:00', 1300, :name, 'Thank you', true,
                 false, 1, :slug, '', '', :now, :now)
        """
        ),
        {
            "rid": restaurant_id,
            "name": reg["restaurant_name"],
            "slug": reg["restaurant_slug"],
            "now": now,
        },
    )

    # Create invited owner
    db.execute(
        text(
            """
            INSERT INTO users
                (id, email, password_hash, display_name, status, created_at, updated_at)
            VALUES
                (:id, :email, :password_hash, :display_name, 'INVITED', :now, :now)
        """
        ),
        {
            "id": user_id,
            "email": reg["owner_email"],
            "password_hash": hash_password(new_token(32)),
            "display_name": reg["owner_name"],
            "now": now,
        },
    )

    # Create owner membership
    db.execute(
        text(
            """
            INSERT INTO restaurant_memberships
                (id, restaurant_id, user_id, role, status, token_version,
                 created_at, updated_at)
            VALUES
                (:id, :rid, :uid, 'owner', 'ACTIVE', 0, :now, :now)
        """
        ),
        {
            "id": membership_id,
            "rid": restaurant_id,
            "uid": user_id,
            "now": now,
        },
    )

    # Create subscription
    trial_ends_at = now + timedelta(days=reg["trial_days"]) if reg["trial_days"] else None
    sub_status = "TRIALING" if reg["trial_days"] > 0 else "ACTIVE"
    db.execute(
        text(
            """
            INSERT INTO platform_subscriptions
                (id, restaurant_id, plan_id, plan_version_id, status,
                 trial_ends_at, current_period_start, current_period_end,
                 cancel_at_period_end, price_snapshot_minor, currency_snapshot,
                 billing_interval_snapshot, trial_extension_count,
                 trial_extension_total_days, created_by_admin_id,
                 created_at, updated_at)
            VALUES
                (:id, :rid, :pid, :pvid, :status, :trial_ends_at,
                 :cps, :cpe, :cancel_at_period_end, :price_snapshot,
                 :currency_snapshot, :billing_interval, 0, 0, :admin_id,
                 :now, :now)
        """
        ),
        {
            "id": uuid4(),
            "rid": restaurant_id,
            "pid": plan.id,
            "pvid": plan_version.id,
            "status": sub_status,
            "trial_ends_at": trial_ends_at,
            "cps": now,
            "cpe": now + timedelta(days=reg["trial_days"] or 30),
            "cancel_at_period_end": False,
            "price_snapshot": plan_version.price_monthly_minor,
            "currency_snapshot": plan_version.currency_code,
            "billing_interval": "MONTHLY",
            "admin_id": admin_id,
            "now": now,
        },
    )

    # Create invitation token
    raw_token = new_token(32)
    db.execute(
        text(
            """
            INSERT INTO platform_one_time_tokens
                (id, token_hash, purpose, email, restaurant_id, expires_at,
                 created_by_admin_id, created_at)
            VALUES
                (:id, :token_hash, 'OWNER_INVITE', :email, :rid, :expires_at,
                 :admin_id, :now)
        """
        ),
        {
            "id": uuid4(),
            "token_hash": hash_token(raw_token),
            "email": reg["owner_email"],
            "rid": restaurant_id,
            "expires_at": now + timedelta(hours=72),
            "admin_id": admin_id,
            "now": now,
        },
    )

    # Update registration
    db.execute(
        text(
            """
            UPDATE self_service_registrations
            SET restaurant_id = :rid, status = 'APPROVED',
                reviewed_by_admin_id = :admin_id, reviewed_at = :now,
                updated_at = :now
            WHERE id = :reg_id
        """
        ),
        {
            "rid": restaurant_id,
            "admin_id": admin_id,
            "now": now,
            "reg_id": registration_id,
        },
    )

    db.commit()

    return {
        "id": str(registration_id),
        "status": "APPROVED",
        "restaurant_id": str(restaurant_id),
        "owner_email": reg["owner_email"],
        "invitation_token": raw_token,
        "invitation_expires_at": now + timedelta(hours=72),
    }


def reject_self_service_registration(
    db: Session,
    *,
    registration_id: UUID,
    admin_id: UUID,
    reason: str,
) -> dict:
    """Reject a pending self-service registration."""
    reg = db.execute(
        text("SELECT * FROM self_service_registrations WHERE id = :id"),
        {"id": registration_id},
    ).mappings().first()
    if reg is None:
        raise AppError(404, "REGISTRATION_NOT_FOUND", "Not found", "Registration not found.")
    if reg["status"] != "PENDING":
        raise AppError(
            409,
            "REGISTRATION_NOT_PENDING",
            "Conflict",
            f"Registration is already {reg['status']}.",
        )

    db.execute(
        text(
            """
            UPDATE self_service_registrations
            SET status = 'REJECTED', reviewed_by_admin_id = :admin_id,
                reviewed_at = :now, review_reason = :reason, updated_at = :now
            WHERE id = :reg_id
        """
        ),
        {
            "admin_id": admin_id,
            "now": datetime.now(UTC),
            "reason": reason,
            "reg_id": registration_id,
        },
    )
    db.commit()

    return {
        "id": str(registration_id),
        "status": "REJECTED",
    }
