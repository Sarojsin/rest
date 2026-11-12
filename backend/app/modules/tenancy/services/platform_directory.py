"""Read/limited-write tenant directory used by the platform console (PA-1).

This is the one sanctioned ``platform -> tenancy`` service edge documented in
plan 04 §4.2. It deliberately uses SQL against the tenancy/identity tables
instead of importing their ORM models, so the module boundary inventory stays
at one entry and the platform console cannot start owning tenant business
logic.
"""

from __future__ import annotations

import secrets
from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.modules.tenancy.services.force_logout import force_logout_restaurant
from app.shared.errors import AppError

LIVE_STATUSES = ("TRIALING", "ACTIVE", "PAST_DUE", "GRACE", "SUSPENDED")
TENANT_STATUSES = ("ACTIVE", "SUSPENDED", "CANCELLED")

_BASE_SELECT = """
SELECT
    r.id,
    r.name,
    r.slug,
    r.status,
    r.timezone,
    r.currency_code,
    r.created_at,
    r.updated_at,
    r.archived_at,
    r.suspended_at,
    r.suspended_reason,
    r.contact_email,
    r.contact_phone,
    r.legal_name,
    (SELECT count(*) FROM branches b WHERE b.restaurant_id = r.id) AS branches,
    (SELECT count(*) FROM restaurant_memberships m
       WHERE m.restaurant_id = r.id AND m.status = 'ACTIVE') AS staff,
    (SELECT u.email FROM restaurant_memberships m
       JOIN users u ON u.id = m.user_id
      WHERE m.restaurant_id = r.id AND m.role = 'owner'
      ORDER BY m.created_at LIMIT 1) AS owner_email,
    live.status AS subscription_status,
    live.plan_code AS plan_code,
    live.plan_name AS plan_name,
    live.id AS subscription_id
FROM restaurants r
LEFT JOIN LATERAL (
    SELECT s.id, s.status, p.code AS plan_code, p.name AS plan_name
      FROM platform_subscriptions s
      JOIN platform_plans p ON p.id = s.plan_id
     WHERE s.restaurant_id = r.id
       AND s.status IN ('TRIALING','ACTIVE','PAST_DUE','GRACE','SUSPENDED')
     ORDER BY s.created_at DESC
     LIMIT 1
) live ON true
"""


def _rows(result) -> list[dict]:
    return [dict(row) for row in result.mappings().all()]


def list_tenants(
    db: Session,
    *,
    status: str | None = None,
    plan_code: str | None = None,
    q: str | None = None,
    page: int = 1,
    page_size: int = 25,
) -> tuple[list[dict], int]:
    where: list[str] = []
    params: dict = {}
    if status:
        where.append("r.status = :status")
        params["status"] = status
    if plan_code:
        where.append("live.plan_code = :plan_code")
        params["plan_code"] = plan_code
    if q:
        where.append(
            "(r.name ILIKE :q OR r.slug ILIKE :q OR EXISTS ("
            "SELECT 1 FROM restaurant_memberships qm JOIN users qu ON qu.id = qm.user_id "
            "WHERE qm.restaurant_id = r.id AND qm.role = 'owner' AND qu.email ILIKE :q))"
        )
        params["q"] = f"%{q.strip()}%"
    clause = ("WHERE " + " AND ".join(where)) if where else ""

    count_sql = f"""
        SELECT count(*) FROM (
            {_BASE_SELECT}
        ) r {clause}
    """
    total = int(db.execute(text(count_sql), params).scalar() or 0)

    offset = (page - 1) * page_size
    sql = f"""
        SELECT * FROM (
            {_BASE_SELECT}
        ) r
        {clause}
        ORDER BY r.created_at DESC, r.name ASC
        LIMIT :limit OFFSET :offset
    """
    items = _rows(
        db.execute(text(sql), {**params, "limit": page_size, "offset": offset})
    )
    return items, total


def get_tenant(db: Session, restaurant_id: UUID) -> dict | None:
    rows = _rows(
        db.execute(text(f"SELECT * FROM ({_BASE_SELECT}) r WHERE r.id = :id"), {"id": restaurant_id})
    )
    return rows[0] if rows else None


def get_tenant_by_slug(db: Session, slug: str) -> dict | None:
    rows = _rows(
        db.execute(
            text(f"SELECT * FROM ({_BASE_SELECT}) r WHERE r.slug = :slug"),
            {"slug": slug},
        )
    )
    return rows[0] if rows else None


def require_tenant(db: Session, restaurant_id: UUID) -> dict:
    tenant = get_tenant(db, restaurant_id)
    if tenant is None:
        raise AppError(404, "TENANT_NOT_FOUND", "Not found", "Tenant not found.")
    return tenant


def tenant_usage(db: Session, restaurant_id: UUID) -> dict:
    row = db.execute(
        text(
            """
            SELECT
              (SELECT count(*) FROM branches WHERE restaurant_id = :id) AS branches,
              (SELECT count(*) FROM restaurant_memberships
                 WHERE restaurant_id = :id AND status = 'ACTIVE') AS staff,
              (SELECT count(*) FROM orders
                 WHERE restaurant_id = :id
                   AND created_at >= date_trunc('month', now())) AS orders_this_month
            """
        ),
        {"id": restaurant_id},
    ).mappings().one()
    return {key: {"used": int(value)} for key, value in row.items()}


def update_tenant_fields(db: Session, restaurant_id: UUID, fields: dict) -> None:
    allowed = {
        "name",
        "contact_email",
        "contact_phone",
        "legal_name",
        "timezone",
        "currency_code",
    }
    values = {key: value for key, value in fields.items() if key in allowed}
    if not values:
        return
    assignments = ", ".join(f"{key} = :{key}" for key in values)
    db.execute(
        text(
            f"UPDATE restaurants SET {assignments}, updated_at = :updated_at "
            "WHERE id = :id"
        ),
        {**values, "updated_at": datetime.now(UTC), "id": restaurant_id},
    )


def set_tenant_status(
    db: Session,
    restaurant_id: UUID,
    *,
    status: str,
    reason: str | None = None,
    suspended_at: datetime | None = None,
) -> None:
    db.execute(
        text(
            """
            UPDATE restaurants
               SET status = :status,
                   suspended_at = :suspended_at,
                   suspended_reason = :reason,
                   updated_at = :updated_at
             WHERE id = :id
            """
        ),
        {
            "status": status,
            "suspended_at": suspended_at,
            "reason": reason,
            "updated_at": datetime.now(UTC),
            "id": restaurant_id,
        },
    )


def force_logout_tenant(db: Session, restaurant_id: UUID) -> int:
    return force_logout_restaurant(db, restaurant_id)


def create_tenant(
    db: Session,
    *,
    name: str,
    slug: str,
    owner_email: str,
    owner_display_name: str,
    contact_email: str | None,
    contact_phone: str | None,
    legal_name: str | None,
    timezone: str,
    currency_code: str,
) -> dict:
    """Create a tenant + invited owner identity in one transaction.

    The caller owns the transaction/commit. The owner receives a one-time
    invitation token and chooses their own password; this function never
    returns or stores a usable password.
    """
    normalized_slug = slug.strip().lower()
    normalized_email = owner_email.strip().lower()

    if db.execute(
        text("SELECT 1 FROM restaurants WHERE slug = :slug"), {"slug": normalized_slug}
    ).scalar():
        raise AppError(409, "SLUG_TAKEN", "Conflict", "That tenant slug is already taken.")
    if db.execute(
        text("SELECT 1 FROM users WHERE email = :email"), {"email": normalized_email}
    ).scalar():
        raise AppError(
            409, "OWNER_EMAIL_EXISTS", "Conflict", "An account with that email already exists."
        )

    now = datetime.now(UTC)
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
            "name": name.strip(),
            "slug": normalized_slug,
            "timezone": timezone,
            "currency_code": currency_code,
            "contact_email": contact_email,
            "contact_phone": contact_phone,
            "legal_name": legal_name,
            "now": now,
        },
    )
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
        {"rid": restaurant_id, "name": name.strip(), "slug": normalized_slug, "now": now},
    )
    db.execute(
        text(
            """
            INSERT INTO users
                (id, email, password_hash, display_name, status, mfa_enabled, created_at, updated_at)
            VALUES
                (:id, :email, :password_hash, :display_name, 'INVITED', False, :now, :now)
            """
        ),
        {
            "id": user_id,
            "email": normalized_email,
            "password_hash": hash_password(secrets.token_urlsafe(48)),
            "display_name": owner_display_name.strip() or normalized_email.split("@")[0],
            "now": now,
        },
    )
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
        {"id": membership_id, "rid": restaurant_id, "uid": user_id, "now": now},
    )
    return require_tenant(db, restaurant_id)


def accept_owner_invitation(
    db: Session, *, email: str, restaurant_id: UUID, display_name: str, password_hash: str
) -> None:
    """Activate an invited owner identity and set their password."""
    db.execute(
        text(
            """
            UPDATE users
               SET password_hash = :password_hash,
                   display_name = COALESCE(NULLIF(:display_name, ''), display_name),
                   status = 'ACTIVE',
                   updated_at = :now
             WHERE email = :email
            """
        ),
        {
            "password_hash": password_hash,
            "display_name": display_name,
            "now": datetime.now(UTC),
            "email": email,
        },
    )
    db.execute(
        text(
            """
            UPDATE restaurant_memberships
               SET status = 'ACTIVE', updated_at = :now
             WHERE restaurant_id = :rid
               AND user_id = (SELECT id FROM users WHERE email = :email)
            """
        ),
        {"now": datetime.now(UTC), "rid": restaurant_id, "email": email},
    )
