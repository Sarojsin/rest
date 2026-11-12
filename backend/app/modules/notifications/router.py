"""Notification / FCM device-token routes (staff realm)."""

from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import Actor, require_permission_on_active_tenant
from app.core.config import settings
from app.db.session import get_db
from app.modules.identity.models import User
from app.modules.notifications.models import DeviceToken, OutboxEvent
from app.modules.notifications.schemas import (
    DeviceTokenIn,
    DeviceTokenListOut,
    DeviceTokenOut,
    FCMMessageIn,
    FCMMessageOut,
)
from app.modules.notifications.services.fcm import process_outbox, send_to_restaurant
from app.shared.errors import AppError

router = APIRouter(tags=["notifications"])


def _resolve_user(db: Session, actor: Actor, user_id: UUID | None) -> User:
    """Return the target user: self, or any user of the restaurant for staff."""
    target_id = user_id or actor.user.id
    user = db.scalar(select(User).where(User.id == target_id))
    if user is None:
        raise AppError(404, "USER_NOT_FOUND", "Not found", "User was not found.")
    # Staff can only manage their own device tokens, or any user in their restaurant.
    if target_id != actor.user.id:
        membership_ids = {m.id for m in user.memberships}
        if actor.membership.id not in membership_ids and actor.membership.restaurant_id not in {
            m.restaurant_id for m in user.memberships
        }:
            raise AppError(403, "FORBIDDEN", "Forbidden", "Not your device token.")
    return user


@router.post("/devices", response_model=DeviceTokenOut, status_code=201)
def register_device(
    payload: DeviceTokenIn,
    actor: Actor = Depends(require_permission_on_active_tenant("staff.manage")),
    db: Session = Depends(get_db),
) -> DeviceTokenOut:
    """Register (or upsert) an FCM device token for the authenticated user."""
    user = _resolve_user(db, actor, None)

    existing = db.scalar(
        select(DeviceToken).where(
            DeviceToken.user_id == user.id,
            DeviceToken.token == payload.token,
        )
    )
    now = datetime.now(UTC)
    if existing:
        existing.platform = payload.platform
        existing.updated_at = now
        db.commit()
        db.refresh(existing)
        return existing

    device_token = DeviceToken(
        user_id=user.id,
        restaurant_id=actor.restaurant_id,
        token=payload.token,
        platform=payload.platform,
        updated_at=now,
    )
    db.add(device_token)
    db.commit()
    db.refresh(device_token)
    return device_token


@router.get("/devices", response_model=DeviceTokenListOut)
def list_devices(
    actor: Actor = Depends(require_permission_on_active_tenant("staff.manage")),
    db: Session = Depends(get_db),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
) -> DeviceTokenListOut:
    """List device tokens registered for the actor's restaurant."""
    base = select(DeviceToken).where(DeviceToken.restaurant_id == actor.restaurant_id)
    total = db.scalar(select(func.count()).select_from(base.subquery())) or 0
    rows = db.execute(
        base.options(selectinload(DeviceToken.user))
        .order_by(DeviceToken.updated_at.desc())
        .offset(offset)
        .limit(limit)
    ).scalars().all()
    return DeviceTokenListOut(items=list(rows), total=total)


@router.delete("/devices/{token}", status_code=204)
def unregister_device(
    token: Annotated[str, Path(description="FCM device token to remove")],
    actor: Actor = Depends(require_permission_on_active_tenant("staff.manage")),
    db: Session = Depends(get_db),
) -> None:
    """Remove a device token (e.g. on sign-out or app uninstall)."""
    deleted = db.execute(
        select(DeviceToken).where(
            DeviceToken.restaurant_id == actor.restaurant_id,
            DeviceToken.token == token,
        )
    ).scalars().all()
    if not deleted:
        raise HTTPException(status_code=404, detail="Device token not found.")
    for row in deleted:
        db.delete(row)
    db.commit()


@router.post("/notifications/send", response_model=FCMMessageOut)
def send_notification(
    payload: FCMMessageIn,
    actor: Actor = Depends(require_permission_on_active_tenant("staff.manage")),
    db: Session = Depends(get_db),
) -> FCMMessageOut:
    """Send an FCM notification to devices of the actor's restaurant.

    Requires ``FIREBASE_CREDENTIALS_PATH`` to be set and a valid
    service-account key present; otherwise returns sent=0.
    """
    restaurant_id = str(payload.restaurant_id or actor.restaurant_id)
    sent, failed, message_ids = send_to_restaurant(
        db,
        restaurant_id=restaurant_id,
        title=payload.title,
        body=payload.body,
        data=payload.data,
    )
    return FCMMessageOut(sent=sent, failed=failed, message_ids=message_ids)


@router.post("/notifications/process-outbox", response_model=dict)
def process_outbox_endpoint(
    actor: Actor = Depends(require_permission_on_active_tenant("staff.manage")),
    db: Session = Depends(get_db),
    limit: int = Query(default=100, ge=1, le=500),
) -> dict:
    """Manually trigger delivery of pending outbox_events as FCM notifications.

    Normally this is invoked by a background worker or cron, but the endpoint
    lets you force delivery on demand.
    """
    processed = process_outbox(db, limit=limit)
    return {"processed": processed}
