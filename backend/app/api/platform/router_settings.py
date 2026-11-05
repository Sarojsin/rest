"""Allowlisted platform settings API (plan 05 §10)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.modules.platform.deps import (
    PlatformActor,
    require_platform_permission,
    require_platform_step_up,
)
from app.modules.platform.models import PlatformSetting
from app.modules.platform.schemas_admin import SettingsUpdateRequest
from app.modules.platform.services.audit import write_platform_audit
from app.modules.platform.services.common import require_reason
from app.modules.platform.services.settings import (
    SETTING_DEFINITIONS,
    current_settings,
    update_settings,
)

router = APIRouter(tags=["platform-settings"])

_TYPE_NAMES = {str: "string", int: "integer", bool: "boolean", list: "list"}


@router.get("/settings")
def get_settings(
    actor: PlatformActor = Depends(require_platform_permission("settings.view")),
    db: Session = Depends(get_db),
) -> dict:
    values = current_settings(db)
    stored = {row.key: row for row in db.query(PlatformSetting).all()}
    return {
        "second_approval_policy": "DEFERRED",
        "items": [
            {
                "key": key,
                "value": values[key],
                "type": _TYPE_NAMES.get(definition[0], "string"),
                "description": definition[2],
                "updated_at": stored[key].updated_at if key in stored else None,
                "updated_by_admin_id": (
                    stored[key].updated_by_admin_id if key in stored else None
                ),
            }
            for key, definition in SETTING_DEFINITIONS.items()
        ],
    }


@router.patch("/settings")
def patch_settings(
    payload: SettingsUpdateRequest,
    request: Request,
    actor: PlatformActor = Depends(require_platform_permission("settings.manage")),
    _: PlatformActor = Depends(require_platform_step_up),
    db: Session = Depends(get_db),
) -> dict:
    reason = require_reason(payload.reason)
    before, after = update_settings(db, payload.changes, admin_id=actor.admin_id)
    changed = {key: after.get(key) for key in payload.changes}
    write_platform_audit(
        db,
        action="PLATFORM_SETTING_UPDATED",
        entity_type="platform_setting",
        entity_id=",".join(sorted(payload.changes))[:64],
        actor_admin_id=actor.admin_id,
        actor_email=actor.email,
        reason=reason,
        request=request,
        before={key: before.get(key) for key in payload.changes},
        after=changed,
    )
    db.commit()
    return {"updated": list(payload.changes), "settings": after}
