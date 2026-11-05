"""Platform staff identities (plan 05 §8)."""

from __future__ import annotations

import json
import secrets
from datetime import timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import hash_password, hash_token, new_token
from app.db.session import get_db
from app.modules.platform.deps import (
    PlatformActor,
    require_platform_permission,
    require_platform_step_up,
)
from app.modules.platform.models import (
    PlatformAdmin,
    PlatformOneTimeToken,
    PlatformRefreshToken,
)
from app.modules.platform.permissions import PLATFORM_ROLES, SUPERADMIN
from app.modules.platform.schemas_admin import (
    PlatformUserCreateRequest,
    PlatformUserUpdateRequest,
    ReasonConfirmRequest,
    ReasonRequest,
)
from app.modules.platform.services.audit import write_platform_audit
from app.modules.platform.services.common import (
    page_params,
    paginated,
    require_confirm,
    require_reason,
    now_utc,
)
from app.shared.errors import AppError

router = APIRouter(tags=["platform-admins"])


def _serialize(row: PlatformAdmin) -> dict:
    remaining = None
    if row.mfa_recovery_codes_hash:
        try:
            remaining = len(json.loads(row.mfa_recovery_codes_hash))
        except (TypeError, ValueError):
            remaining = None
    return {
        "id": row.id,
        "email": row.email,
        "display_name": row.display_name,
        "role": row.role,
        "status": row.status,
        "mfa_enabled": row.mfa_enabled_at is not None,
        "recovery_codes_remaining": remaining,
        "last_login_at": row.last_login_at,
        "last_auth_at": row.last_auth_at,
        "created_at": row.created_at,
    }


def _active_superadmins(db: Session, exclude_id: UUID | None = None) -> int:
    query = select(func.count()).select_from(PlatformAdmin).where(
        PlatformAdmin.role == SUPERADMIN,
        PlatformAdmin.status == "ACTIVE",
    )
    if exclude_id is not None:
        query = query.where(PlatformAdmin.id != exclude_id)
    return int(db.scalar(query) or 0)


def _revoke_sessions(db: Session, admin_id: UUID, reason: str) -> None:
    db.execute(
        update(PlatformRefreshToken)
        .where(
            PlatformRefreshToken.admin_id == admin_id,
            PlatformRefreshToken.revoked_at.is_(None),
        )
        .values(revoked_at=now_utc(), revoked_reason=reason)
    )


def _get(db: Session, admin_id: UUID) -> PlatformAdmin:
    row = db.get(PlatformAdmin, admin_id)
    if row is None:
        raise AppError(404, "PLATFORM_USER_NOT_FOUND", "Not found", "Administrator not found.")
    return row


@router.get("/platform-users")
def list_platform_users(
    role: str | None = None,
    status_filter: str | None = Query(default=None, alias="status"),
    q: str | None = None,
    page: int = 1,
    page_size: int = 25,
    actor: PlatformActor = Depends(require_platform_permission("platform_user.view")),
    db: Session = Depends(get_db),
) -> dict:
    page, page_size = page_params(page, page_size)
    query = select(PlatformAdmin)
    if role:
        query = query.where(PlatformAdmin.role == role)
    if status_filter:
        query = query.where(PlatformAdmin.status == status_filter)
    if q:
        needle = f"%{q.strip()}%"
        query = query.where(
            PlatformAdmin.email.ilike(needle) | PlatformAdmin.display_name.ilike(needle)
        )
    total = int(db.scalar(select(func.count()).select_from(query.subquery())) or 0)
    rows = db.scalars(
        query.order_by(PlatformAdmin.created_at)
        .limit(page_size)
        .offset((page - 1) * page_size)
    ).all()
    return {
        **paginated([_serialize(row) for row in rows], total, page, page_size),
        "active_superadmins": _active_superadmins(db),
        "launch_requires_two": True,
    }


@router.post("/platform-users", status_code=status.HTTP_201_CREATED)
def create_platform_user(
    payload: PlatformUserCreateRequest,
    request: Request,
    actor: PlatformActor = Depends(require_platform_permission("platform_user.manage")),
    _: PlatformActor = Depends(require_platform_step_up),
    db: Session = Depends(get_db),
) -> dict:
    reason = require_reason(payload.reason)
    email = str(payload.email).strip().lower()
    role = payload.role.strip().lower()
    if role not in PLATFORM_ROLES:
        raise AppError(422, "INVALID_ROLE", "Invalid input", "Unknown platform role.")
    if db.scalar(select(PlatformAdmin).where(PlatformAdmin.email == email)):
        raise AppError(409, "PLATFORM_USER_EXISTS", "Conflict", "That email is already invited.")

    now = now_utc()
    row = PlatformAdmin(
        email=email,
        password_hash=hash_password(secrets.token_urlsafe(48)),
        display_name=payload.display_name.strip(),
        role=role,
        status="INVITED",
        token_version=0,
        created_by_admin_id=actor.admin_id,
    )
    db.add(row)
    db.flush()
    raw_token = new_token(32)
    expires_at = now + timedelta(hours=72)
    db.add(
        PlatformOneTimeToken(
            token_hash=hash_token(raw_token),
            purpose="ADMIN_INVITE",
            email=email,
            platform_admin_id=row.id,
            expires_at=expires_at,
            created_by_admin_id=actor.admin_id,
        )
    )
    write_platform_audit(
        db,
        action="PLATFORM_USER_INVITED",
        entity_type="platform_admin",
        entity_id=str(row.id),
        actor_admin_id=actor.admin_id,
        actor_email=actor.email,
        reason=reason,
        request=request,
        after={"email": email, "role": role},
    )
    db.commit()
    origin = settings.platform_admin_origin or ""
    return {
        "admin": _serialize(row),
        "invitation": {
            "token": raw_token,
            "expires_at": expires_at,
            "accept_url": (
                f"{origin.rstrip('/')}/admin/invite/{raw_token}"
                if origin
                else f"/admin/invite/{raw_token}"
            ),
        },
    }


@router.patch("/platform-users/{admin_id}")
def update_platform_user(
    admin_id: UUID,
    payload: PlatformUserUpdateRequest,
    request: Request,
    actor: PlatformActor = Depends(require_platform_permission("platform_user.manage")),
    _: PlatformActor = Depends(require_platform_step_up),
    db: Session = Depends(get_db),
) -> dict:
    reason = require_reason(payload.reason)
    row = _get(db, admin_id)
    changes = payload.model_dump(exclude_unset=True, exclude={"reason"})
    if "role" in changes:
        role = str(changes["role"]).strip().lower()
        if role not in PLATFORM_ROLES:
            raise AppError(422, "INVALID_ROLE", "Invalid input", "Unknown platform role.")
        changes["role"] = role
    if "status" in changes:
        new_status = str(changes["status"]).strip().upper()
        if new_status not in {"INVITED", "ACTIVE", "DISABLED"}:
            raise AppError(422, "INVALID_STATUS", "Invalid input", "Unknown administrator status.")
        changes["status"] = new_status

    loses_superadmin = (
        row.role == SUPERADMIN
        and row.status == "ACTIVE"
        and (
            changes.get("role", SUPERADMIN) != SUPERADMIN
            or changes.get("status", "ACTIVE") != "ACTIVE"
        )
    )
    if loses_superadmin and _active_superadmins(db, exclude_id=row.id) < 1:
        raise AppError(
            409, "LAST_SUPERADMIN", "Conflict", "At least one active superadmin must remain."
        )

    before = {"role": row.role, "status": row.status}
    for key, value in changes.items():
        setattr(row, key, value)
    if changes.get("role") != before["role"] or changes.get("status") == "DISABLED":
        row.token_version += 1
        _revoke_sessions(db, row.id, "ADMIN_DISABLED" if changes.get("status") == "DISABLED" else "ROLE_CHANGED")
    row.updated_at = now_utc()
    write_platform_audit(
        db,
        action="PLATFORM_USER_UPDATED",
        entity_type="platform_admin",
        entity_id=str(row.id),
        actor_admin_id=actor.admin_id,
        actor_email=actor.email,
        reason=reason,
        request=request,
        before=before,
        after={"role": row.role, "status": row.status},
    )
    db.commit()
    return _serialize(row)


@router.post("/platform-users/{admin_id}/disable")
def disable_platform_user(
    admin_id: UUID,
    payload: ReasonConfirmRequest,
    request: Request,
    actor: PlatformActor = Depends(require_platform_permission("platform_user.manage")),
    _: PlatformActor = Depends(require_platform_step_up),
    db: Session = Depends(get_db),
) -> dict:
    reason = require_reason(payload.reason)
    row = _get(db, admin_id)
    require_confirm(payload.confirm, row.email)
    if row.role == SUPERADMIN and row.status == "ACTIVE" and _active_superadmins(db, exclude_id=row.id) < 1:
        raise AppError(
            409, "LAST_SUPERADMIN", "Conflict", "At least one active superadmin must remain."
        )
    row.status = "DISABLED"
    row.disabled_reason = reason
    row.token_version += 1
    row.updated_at = now_utc()
    _revoke_sessions(db, row.id, "ADMIN_DISABLED")
    write_platform_audit(
        db,
        action="PLATFORM_USER_DISABLED",
        entity_type="platform_admin",
        entity_id=str(row.id),
        actor_admin_id=actor.admin_id,
        actor_email=actor.email,
        reason=reason,
        request=request,
        before={"status": "ACTIVE"},
        after={"status": "DISABLED"},
    )
    db.commit()
    return _serialize(row)


@router.post("/platform-users/{admin_id}/reset-mfa")
def reset_platform_user_mfa(
    admin_id: UUID,
    payload: ReasonConfirmRequest,
    request: Request,
    actor: PlatformActor = Depends(require_platform_permission("platform_user.manage")),
    _: PlatformActor = Depends(require_platform_step_up),
    db: Session = Depends(get_db),
) -> dict:
    if actor.role != SUPERADMIN:
        raise AppError(403, "FORBIDDEN", "Forbidden", "Only a superadmin can reset MFA.")
    reason = require_reason(payload.reason)
    row = _get(db, admin_id)
    require_confirm(payload.confirm, row.email)
    row.mfa_secret_encrypted = None
    row.mfa_enabled_at = None
    row.mfa_recovery_codes_hash = None
    row.token_version += 1
    row.updated_at = now_utc()
    _revoke_sessions(db, row.id, "MFA_RESET")
    write_platform_audit(
        db,
        action="PLATFORM_USER_MFA_RESET",
        entity_type="platform_admin",
        entity_id=str(row.id),
        actor_admin_id=actor.admin_id,
        actor_email=actor.email,
        reason=reason,
        request=request,
        after={"mfa_enabled": False},
    )
    db.commit()
    return _serialize(row)


@router.post("/platform-users/{admin_id}/reset-password")
def reset_platform_user_password(
    admin_id: UUID,
    payload: ReasonRequest,
    request: Request,
    actor: PlatformActor = Depends(require_platform_permission("platform_user.manage")),
    _: PlatformActor = Depends(require_platform_step_up),
    db: Session = Depends(get_db),
) -> dict:
    reason = require_reason(payload.reason)
    row = _get(db, admin_id)
    now = now_utc()
    raw_token = new_token(32)
    expires_at = now + timedelta(hours=72)
    db.add(
        PlatformOneTimeToken(
            token_hash=hash_token(raw_token),
            purpose="ADMIN_PASSWORD_RESET",
            email=row.email,
            platform_admin_id=row.id,
            expires_at=expires_at,
            created_by_admin_id=actor.admin_id,
        )
    )
    write_platform_audit(
        db,
        action="PLATFORM_USER_PASSWORD_RESET_ISSUED",
        entity_type="platform_admin",
        entity_id=str(row.id),
        actor_admin_id=actor.admin_id,
        actor_email=actor.email,
        reason=reason,
        request=request,
        after={"expires_at": expires_at},
    )
    db.commit()
    origin = settings.platform_admin_origin or ""
    return {
        "token": raw_token,
        "expires_at": expires_at,
        "accept_url": (
            f"{origin.rstrip('/')}/admin/reset/{raw_token}"
            if origin
            else f"/admin/reset/{raw_token}"
        ),
    }
