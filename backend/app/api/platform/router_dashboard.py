"""Dashboard, platform health, and tenant diagnostics (plan 05 §3)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.modules.platform.deps import PlatformActor, require_platform_permission
from app.modules.platform.models import PlatformAuditLog
from app.modules.platform.services.audit import write_platform_audit
from app.modules.platform.services.settings import get_setting

router = APIRouter(tags=["platform-dashboard"])

_DEFINITIONS_VERSION = 1


def _default_range(from_: datetime | None, to: datetime | None) -> tuple[datetime, datetime]:
    to_value = to or datetime.now(UTC)
    from_value = from_ or (to_value - timedelta(days=30))
    return from_value, to_value


@router.get("/dashboard")
def dashboard(
    from_: datetime | None = Query(default=None, alias="from"),
    to: datetime | None = None,
    actor: PlatformActor = Depends(require_platform_permission("platform.dashboard.view")),
    db: Session = Depends(get_db),
) -> dict:
    from_value, to_value = _default_range(from_, to)
    params = {"from": from_value, "to": to_value}

    row = db.execute(
        text(
            """
            SELECT
              (SELECT count(*) FROM restaurants WHERE archived_at IS NULL) AS tenants_total,
              (SELECT count(*) FROM restaurants WHERE archived_at IS NULL AND status = 'ACTIVE') AS tenants_active,
              (SELECT count(*) FROM platform_subscriptions WHERE status = 'TRIALING') AS tenants_trial,
              (SELECT count(*) FROM restaurants WHERE archived_at IS NULL AND status = 'SUSPENDED') AS tenants_suspended,
              (SELECT count(*) FROM restaurants WHERE archived_at IS NULL AND status = 'CANCELLED') AS tenants_cancelled,
              (SELECT count(*) FROM branches b JOIN restaurants r ON r.id = b.restaurant_id
                 WHERE r.archived_at IS NULL) AS branches_total,
              (SELECT count(*) FROM restaurant_memberships m JOIN restaurants r ON r.id = m.restaurant_id
                 WHERE r.archived_at IS NULL AND m.status = 'ACTIVE') AS staff_total,
              (SELECT count(*) FROM platform_admins WHERE status = 'ACTIVE') AS platform_users_total,
              (SELECT count(*) FROM platform_subscriptions
                 WHERE status IN ('TRIALING','ACTIVE','PAST_DUE','GRACE')) AS active_subscriptions,
              (SELECT COALESCE(sum(
                  CASE WHEN s.billing_interval_snapshot = 'ANNUAL'
                       THEN s.price_snapshot_minor / 12
                       ELSE s.price_snapshot_minor END), 0)
                 FROM platform_subscriptions s
                WHERE s.status = 'ACTIVE') AS mrr_minor,
              (SELECT COALESCE(sum(p.amount_minor), 0) FROM platform_payments p
                 WHERE p.kind = 'PAYMENT' AND p.status = 'CONFIRMED'
                   AND p.paid_at >= :from AND p.paid_at <= :to) AS collected_minor,
              (SELECT COALESCE(sum(p.amount_minor), 0) FROM platform_payments p
                 WHERE p.kind = 'REFUND' AND p.status = 'REFUNDED'
                   AND p.refund_completed_at >= :from AND p.refund_completed_at <= :to) AS refunded_minor,
              (SELECT count(*) FROM platform_invoices i
                 WHERE i.status IN ('OPEN','OVERDUE')
                   AND NOT EXISTS (SELECT 1 FROM platform_payments p
                                    WHERE p.invoice_id = i.id AND p.kind = 'PAYMENT'
                                      AND p.status = 'CONFIRMED')) AS pending_payments,
              (SELECT count(*) FROM platform_payments p
                 WHERE p.status = 'FAILED' AND p.created_at >= :from AND p.created_at <= :to) AS failed_payments,
              (SELECT count(*) FROM restaurants WHERE archived_at IS NULL
                 AND created_at >= :from AND created_at <= :to) AS new_tenants,
              (SELECT count(*) FROM platform_subscription_events e
                 WHERE e.event_type = 'RENEWED' AND e.created_at >= :from AND e.created_at <= :to) AS renewals,
              (SELECT count(*) FROM platform_subscription_events e
                 WHERE e.from_status IN ('ACTIVE','PAST_DUE','GRACE')
                   AND e.event_type IN ('RENEWED','EXPIRED') AND e.created_at >= :from AND e.created_at <= :to) AS renewals_due,
              (SELECT count(*) FROM platform_subscription_events e
                 WHERE e.event_type IN ('CANCELLED','EXPIRED')
                   AND e.created_at >= :from AND e.created_at <= :to) AS churned,
              (SELECT count(*) FROM platform_subscriptions WHERE created_at < :from
                 AND status IN ('TRIALING','ACTIVE','PAST_DUE','GRACE')) AS active_at_start,
              (SELECT count(*) FROM platform_subscription_events e
                 WHERE e.from_status = 'TRIALING' AND e.to_status = 'ACTIVE'
                   AND e.created_at >= :from AND e.created_at <= :to) AS trials_converted,
              (SELECT count(*) FROM platform_subscription_events e
                 WHERE e.from_status = 'TRIALING'
                   AND e.to_status IN ('ACTIVE','EXPIRED','CANCELLED')
                   AND e.created_at >= :from AND e.created_at <= :to) AS trials_ended
            """
        ),
        params,
    ).mappings().one()

    mrr = int(row["mrr_minor"] or 0)
    collections = int(row["collected_minor"] or 0) - int(row["refunded_minor"] or 0)
    trials_ended = int(row["trials_ended"] or 0)
    renewals_due = int(row["renewals_due"] or 0)
    active_at_start = int(row["active_at_start"] or 0)
    currency = str(get_setting(db, "platform.default_currency", "NPR") or "NPR")

    recent = db.scalars(
        select(PlatformAuditLog).order_by(PlatformAuditLog.created_at.desc()).limit(10)
    ).all()

    return {
        "from": from_value,
        "to": to_value,
        "definitions_version": _DEFINITIONS_VERSION,
        "metrics": {
            "tenants_total": int(row["tenants_total"] or 0),
            "tenants_active": int(row["tenants_active"] or 0),
            "tenants_trial": int(row["tenants_trial"] or 0),
            "tenants_suspended": int(row["tenants_suspended"] or 0),
            "tenants_cancelled": int(row["tenants_cancelled"] or 0),
            "branches_total": int(row["branches_total"] or 0),
            "staff_total": int(row["staff_total"] or 0),
            "platform_users_total": int(row["platform_users_total"] or 0),
            "active_subscriptions": int(row["active_subscriptions"] or 0),
            "mrr_minor": mrr,
            "arr_minor": mrr * 12,
            "collections_minor": collections,
            "pending_payments": int(row["pending_payments"] or 0),
            "failed_payments": int(row["failed_payments"] or 0),
            "trial_conversion_rate": (
                round(int(row["trials_converted"] or 0) / trials_ended, 4)
                if trials_ended
                else None
            ),
            "new_tenants": int(row["new_tenants"] or 0),
            "renewal_rate": (
                round(int(row["renewals"] or 0) / renewals_due, 4) if renewals_due else None
            ),
            "churn_rate": (
                round(int(row["churned"] or 0) / active_at_start, 4)
                if active_at_start
                else None
            ),
            "currency_code": currency,
        },
        "health": {
            "api": "ok",
            "database": "ok" if _database_ok(db) else "error",
            "migrations": _migration_state(db),
        },
        "recent_activity": [
            {
                "id": entry.id,
                "action": entry.action,
                "actor_email": entry.actor_email_snapshot,
                "entity_type": entry.entity_type,
                "entity_id": entry.entity_id,
                "tenant_id": entry.restaurant_id,
                "created_at": entry.created_at,
            }
            for entry in recent
        ],
    }


def _database_ok(db: Session) -> bool:
    try:
        db.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


def _migration_state(db: Session) -> str:
    try:
        stamp = db.execute(text("SELECT version_num FROM alembic_version")).scalar_one_or_none()
    except Exception:
        return "unknown"
    try:
        from alembic.config import Config
        from alembic.script import ScriptDirectory

        from pathlib import Path

        config = Config(str(Path(__file__).resolve().parents[3] / "alembic.ini"))
        head = ScriptDirectory.from_config(config).get_current_head()
        return "head" if stamp == head else f"behind ({stamp or 'none'})"
    except Exception:
        return stamp or "unknown"


@router.get("/diagnostics/health")
def diagnostics_health(
    actor: PlatformActor = Depends(require_platform_permission("diagnostics.view")),
    db: Session = Depends(get_db),
) -> dict:
    return {
        "api": "ok",
        "database": "ok" if _database_ok(db) else "error",
        "migrations": _migration_state(db),
        "checked_at": datetime.now(UTC),
    }


@router.get("/tenants/{tenant_id}/diagnostics")
def tenant_diagnostics(
    tenant_id: UUID,
    actor: PlatformActor = Depends(require_platform_permission("diagnostics.view")),
    db: Session = Depends(get_db),
) -> dict:
    from app.modules.tenancy.services import platform_directory

    tenant = platform_directory.require_tenant(db, tenant_id)

    owner_count = int(
        db.execute(
            text(
                "SELECT count(*) FROM restaurant_memberships "
                "WHERE restaurant_id = :id AND role = 'owner' AND status = 'ACTIVE'"
            ),
            {"id": tenant_id},
        ).scalar()
        or 0
    )
    settings_exists = bool(
        db.execute(
            text("SELECT 1 FROM restaurant_settings WHERE restaurant_id = :id"),
            {"id": tenant_id},
        ).scalar()
    )
    branch_count = int(
        db.execute(
            text("SELECT count(*) FROM branches WHERE restaurant_id = :id"),
            {"id": tenant_id},
        ).scalar()
        or 0
    )
    last_audit = db.scalar(
        select(PlatformAuditLog.created_at)
        .where(PlatformAuditLog.restaurant_id == tenant_id)
        .order_by(PlatformAuditLog.created_at.desc())
        .limit(1)
    )

    checks = [
        {
            "key": "owner_membership",
            "status": "ok" if owner_count == 1 else ("warning" if owner_count else "error"),
            "detail": f"{owner_count} active owner",
        },
        {
            "key": "settings_row",
            "status": "ok" if settings_exists else "error",
            "detail": "settings present" if settings_exists else "settings row missing",
        },
        {
            "key": "tenant_status",
            "status": "ok" if tenant["status"] == "ACTIVE" else "warning",
            "detail": tenant["status"],
        },
        {
            "key": "branch_count",
            "status": "ok" if branch_count else "warning",
            "detail": f"{branch_count} branches",
        },
        {
            "key": "recent_audit",
            "status": "ok" if last_audit else "warning",
            "detail": (
                f"last action {last_audit.isoformat()}" if last_audit else "no platform audit yet"
            ),
        },
    ]

    subscription_status = tenant.get("subscription_status")
    if subscription_status == "TRIALING":
        checks.insert(
            2,
            {
                "key": "active_subscription",
                "status": "ok",
                "detail": f"trial subscription {tenant.get('plan_code')}",
            },
        )
    elif subscription_status in ("ACTIVE", "PAST_DUE", "GRACE"):
        checks.insert(
            2,
            {
                "key": "active_subscription",
                "status": "ok",
                "detail": f"{subscription_status} · {tenant.get('plan_code')}",
            },
        )
    else:
        checks.insert(
            2,
            {
                "key": "active_subscription",
                "status": "error",
                "detail": "no live subscription",
            },
        )

    write_platform_audit(
        db,
        action="TENANT_DIAGNOSTICS_VIEWED",
        entity_type="restaurant",
        entity_id=str(tenant_id),
        actor_admin_id=actor.admin_id,
        actor_email=actor.email,
        restaurant_id=tenant_id,
        reason="diagnostics",
    )
    db.commit()

    return {"tenant_id": tenant_id, "checks": checks, "checked_at": datetime.now(UTC)}
