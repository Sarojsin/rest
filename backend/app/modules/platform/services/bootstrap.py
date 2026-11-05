"""Platform bootstrap and development seed (PA-0.9).

Production: create exactly one Super Admin when no active one exists, using the
operator-supplied bootstrap credentials. Never seed a fictional second admin.

Development/test: seed role fixtures, clearly marked as non-production.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.security import hash_password
from app.modules.platform.models import PlatformAdmin
from app.modules.platform.services.audit import write_platform_audit
from app.modules.platform.services.crypto import encrypt_secret

BOOTSTRAP_ACTION = "PLATFORM_BOOTSTRAP_ADMIN_CREATED"
BOOTSTRAP_REENABLED_ACTION = "PLATFORM_BOOTSTRAP_ADMIN_REENABLED"

# Development/test only. These are not production launch credentials.
_DEV_MFA_SECRET = "JBSWY3DPEHPK3PXP"
DEV_PLATFORM_ADMINS = [
    ("platform@harbor.example", "PlatformOwner!1", "Platform Owner", "superadmin"),
    ("platform2@harbor.example", "PlatformOwner!2", "Second Super Admin", "superadmin"),
    ("support@harbor.example", "PlatformSupport!1", "Support Admin", "support"),
    ("billing@harbor.example", "PlatformBilling!1", "Billing Admin", "billing"),
    ("ops@harbor.example", "PlatformOps!1", "Operations Admin", "ops"),
]


def _active_superadmin_count(db: Session) -> int:
    return int(
        db.scalar(
            select(func.count())
            .select_from(PlatformAdmin)
            .where(
                PlatformAdmin.role == "superadmin",
                PlatformAdmin.status == "ACTIVE",
            )
        )
        or 0
    )


def bootstrap_platform(db: Session, settings: Settings) -> None:
    """Idempotent production bootstrap of the primary Super Admin."""
    if _active_superadmin_count(db) > 0:
        return

    email = (settings.platform_bootstrap_email or "").strip().lower()
    password = settings.platform_bootstrap_password or ""
    if not email or not password:
        raise RuntimeError(
            "No active platform superadmin exists. Set PLATFORM_BOOTSTRAP_EMAIL and "
            "PLATFORM_BOOTSTRAP_PASSWORD to create the primary Super Admin."
        )
    if len(password) < 12:
        raise RuntimeError("PLATFORM_BOOTSTRAP_PASSWORD must be at least 12 characters.")

    existing = db.scalar(select(PlatformAdmin).where(PlatformAdmin.email == email))
    if existing is not None:
        # Break-glass path: only re-enable the configured bootstrap account.
        # Never overwrite its password or MFA secret.
        if existing.status != "ACTIVE":
            existing.status = "ACTIVE"
            existing.disabled_reason = None
            write_platform_audit(
                db,
                action=BOOTSTRAP_REENABLED_ACTION,
                entity_type="platform_admin",
                entity_id=str(existing.id),
                actor_email=existing.email,
                reason="bootstrap re-enable",
                after={"status": "ACTIVE"},
            )
            db.commit()
        return

    admin = PlatformAdmin(
        email=email,
        password_hash=hash_password(password),
        display_name="Primary Super Admin",
        role="superadmin",
        status="ACTIVE",
        mfa_enabled_at=None,
        token_version=0,
        password_changed_at=datetime.now(UTC),
    )
    db.add(admin)
    db.flush()
    write_platform_audit(
        db,
        action=BOOTSTRAP_ACTION,
        entity_type="platform_admin",
        entity_id=str(admin.id),
        actor_email=admin.email,
        reason="initial bootstrap",
        after={"email": admin.email, "role": admin.role},
    )
    db.commit()


def seed_platform_billing_dev(db: Session) -> None:
    """Seed the plan catalogue and one demo billing record. Dev/test only.

    Idempotent: existing plans and a live subscription for the demo tenant are
    left untouched. Never called in production (bootstrap_platform only ensures
    settings defaults there).
    """
    from datetime import timedelta

    from app.modules.platform.models import PlatformPlan, PlatformSubscription
    from app.modules.platform.services.billing import create_invoice
    from app.modules.platform.services.settings import ensure_defaults

    ensure_defaults(db)

    plans = [
        ("starter", "Starter", "Single branch, QR ordering, core reporting.", 2_999_00, 0, 30),
        ("growth", "Growth", "Multi-branch operations, staff roles, exports.", 5_999_00, 1, 25),
        (
            "professional",
            "Professional",
            "Advanced analytics, loyalty, priority support.",
            9_999_00,
            2,
            20,
        ),
        ("enterprise", "Enterprise", "Custom limits, onboarding, and SLA.", 19_999_00, 3, 0),
    ]
    created_plans: dict[str, PlatformPlan] = {}
    for code, name, description, price, order, trial_days in plans:
        plan = db.scalar(select(PlatformPlan).where(PlatformPlan.code == code))
        if plan is None:
            plan = PlatformPlan(
                code=code,
                name=name,
                description=description,
                price_monthly_minor=price,
                price_annual_minor=price * 10,
                currency_code="NPR",
                trial_days=trial_days,
                entitlements={"branches": {"limit": order + 1}, "staff": {"limit": 25}},
                status="ACTIVE",
                is_public=True,
                sort_order=order,
            )
            db.add(plan)
            db.flush()
        created_plans[code] = plan
    db.commit()

    restaurant = db.execute(
        text("SELECT id, name FROM restaurants WHERE slug = :slug"),
        {"slug": "harbor-table"},
    ).mappings().first()
    if restaurant is None:
        return
    live = db.scalar(
        select(PlatformSubscription).where(
            PlatformSubscription.restaurant_id == restaurant["id"],
            PlatformSubscription.status.in_(
                ("TRIALING", "ACTIVE", "PAST_DUE", "GRACE", "SUSPENDED")
            ),
        )
    )
    if live is not None:
        return

    plan = created_plans["growth"]
    now = datetime.now(UTC)
    subscription = PlatformSubscription(
        restaurant_id=restaurant["id"],
        plan_id=plan.id,
        status="ACTIVE",
        trial_ends_at=None,
        current_period_start=now - timedelta(days=5),
        current_period_end=now + timedelta(days=25),
        cancel_at_period_end=False,
        price_snapshot_minor=plan.price_monthly_minor,
        currency_snapshot=plan.currency_code,
        billing_interval_snapshot="MONTHLY",
    )
    db.add(subscription)
    db.flush()
    invoice = create_invoice(
        db,
        tenant={"id": restaurant["id"], "name": restaurant["name"], "legal_name": None},
        subscription=subscription,
        lines=[
            {
                "kind": "PLAN",
                "description": f"{plan.name} plan — monthly",
                "quantity": 1,
                "unit_amount_minor": plan.price_monthly_minor,
            }
        ],
        due_at=now + timedelta(days=10),
        currency_code=plan.currency_code,
        notes="Demo invoice seeded in development only.",
        discount_minor=0,
        admin_id=None,
    )
    invoice.status = "OPEN"
    db.commit()


def seed_platform_dev(db: Session, settings: Settings) -> None:
    """Seed platform role fixtures. Never runs in production."""
    if settings.is_production:
        return

    mfa_secret = None
    if settings.platform_mfa_key:
        mfa_secret = encrypt_secret(_DEV_MFA_SECRET, key=settings.platform_mfa_key)

    for email, password, display_name, role in DEV_PLATFORM_ADMINS:
        existing = db.scalar(select(PlatformAdmin).where(PlatformAdmin.email == email))
        if existing is not None:
            continue
        db.add(
            PlatformAdmin(
                email=email,
                password_hash=hash_password(password),
                display_name=display_name,
                role=role,
                status="ACTIVE",
                mfa_secret_encrypted=mfa_secret,
                mfa_enabled_at=datetime.now(UTC) if mfa_secret else None,
                token_version=0,
            )
        )
    db.commit()
