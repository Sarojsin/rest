"""PA-0.8 — platform audit writer: transaction, reason, redaction."""

from __future__ import annotations

from collections.abc import Generator
from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.modules.platform.models import PlatformAuditLog
from app.modules.platform.services.audit import REDACTED, write_platform_audit


@pytest.fixture()
def db() -> Generator[Session, None, None]:
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    before = set(session.scalars(select(PlatformAuditLog.id)).all())
    try:
        yield session
        session.rollback()
    finally:
        new_rows = session.scalars(
            select(PlatformAuditLog).where(PlatformAuditLog.id.not_in(before))
        ).all()
        for row in new_rows:
            session.delete(row)
        session.commit()
        session.close()


@pytest.fixture()
def fake_request():
    return SimpleNamespace(
        state=SimpleNamespace(request_id="req-123"),
        client=SimpleNamespace(host="203.0.113.9"),
        headers={"user-agent": "pytest-agent"},
    )


def test_audit_row_captures_actor_entity_and_request(db: Session, fake_request) -> None:
    admin_id = uuid4()
    entry = write_platform_audit(
        db,
        action="TENANT_SUSPENDED",
        entity_type="restaurant",
        entity_id=str(uuid4()),
        actor_admin_id=admin_id,
        actor_email="admin@harbor.com",
        reason="payment overdue for two cycles",
        request=fake_request,
        require_reason=True,
    )
    db.commit()

    stored = db.get(PlatformAuditLog, entry.id)
    assert stored is not None
    assert stored.actor_admin_id == admin_id
    assert stored.actor_email_snapshot == "admin@harbor.com"
    assert stored.reason == "payment overdue for two cycles"
    assert stored.request_id == "req-123"
    assert stored.ip == "203.0.113.9"
    assert stored.user_agent == "pytest-agent"


def test_mutations_require_a_meaningful_reason(db: Session) -> None:
    with pytest.raises(ValueError, match="at least 10"):
        write_platform_audit(
            db,
            action="PLAN_UPDATED",
            entity_type="platform_plan",
            entity_id=str(uuid4()),
            reason="short",
            require_reason=True,
        )
    db.rollback()


def test_reason_is_trimmed_and_bounded(db: Session) -> None:
    entry = write_platform_audit(
        db,
        action="PLAN_UPDATED",
        entity_type="platform_plan",
        entity_id=str(uuid4()),
        reason="   a valid reason with spaces   ",
        require_reason=True,
    )
    assert entry.reason == "a valid reason with spaces"

    long_entry = write_platform_audit(
        db,
        action="PLAN_UPDATED",
        entity_type="platform_plan",
        entity_id=str(uuid4()),
        reason="x" * 5000,
        require_reason=True,
    )
    assert len(long_entry.reason) == 1000
    db.rollback()


def test_snapshots_redact_secrets_and_session_material(db: Session) -> None:
    entry = write_platform_audit(
        db,
        action="PLATFORM_SETTING_UPDATED",
        entity_type="platform_setting",
        entity_id="platform.company_name",
        reason="legal name correction approved",
        before={"company_name": "Old", "password": "hunter2"},
        after={
            "company_name": "New",
            "nested": {
                "api_key": "abc",
                "csrf_token": "xyz",
                "safe": "kept",
            },
            "items": [{"secret_value": "nope"}, {"safe": "yes"}],
        },
        require_reason=True,
    )

    assert entry.before_json["password"] == REDACTED
    assert entry.after_json["nested"]["api_key"] == REDACTED
    assert entry.after_json["nested"]["csrf_token"] == REDACTED
    assert entry.after_json["nested"]["safe"] == "kept"
    assert entry.after_json["items"][0]["secret_value"] == REDACTED
    assert entry.after_json["items"][1]["safe"] == "yes"
    db.rollback()


def test_security_events_do_not_require_a_long_reason(db: Session) -> None:
    entry = write_platform_audit(
        db,
        action="PLATFORM_LOGOUT",
        entity_type="platform_admin",
        entity_id=str(uuid4()),
        reason="logout",
    )
    assert entry.reason == "logout"
    db.rollback()


def test_deep_payloads_are_bounded(db: Session) -> None:
    nested: dict = {"value": "leaf"}
    for _ in range(10):
        nested = {"child": nested}

    entry = write_platform_audit(
        db,
        action="PLAN_UPDATED",
        entity_type="platform_plan",
        entity_id=str(uuid4()),
        reason="deep payload guard test",
        after=nested,
        require_reason=True,
    )

    # Just assert it serializes and does not recurse forever.
    assert entry.after_json is not None
    db.rollback()
