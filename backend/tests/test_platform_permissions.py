"""PA-0.4 — platform permissions, dependencies, and maker–checker helpers."""

from collections.abc import Generator
from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import create_platform_access_token
from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.modules.platform.constants import PLATFORM_ACCESS_COOKIE
from app.modules.platform.deps import (
    PlatformActor,
    get_platform_admin,
    require_platform_permission,
)
from app.modules.platform.models import PlatformAdmin
from app.modules.platform.permissions import (
    BILLING,
    MAKER_CHECKER_DISTINCT,
    MAKER_CHECKER_ONLY_ONE,
    MAKER_CHECKER_SELF,
    OPS,
    PLATFORM_PERMISSIONS,
    PLATFORM_ROLE_PERMISSIONS,
    SUPERADMIN,
    SUPPORT,
    has_permission,
    is_platform_role,
    maker_checker_status,
    permissions_for,
)
from app.shared.errors import AppError

EXPECTED = {
    SUPPORT: {
        "platform.dashboard.view",
        "tenant.view",
        "tenant.search",
        "plan.view",
        "subscription.view",
        "invoice.view",
        "audit.view",
        "settings.view",
        "diagnostics.view",
        "analytics.view",
    },
    BILLING: {
        "platform.dashboard.view",
        "tenant.view",
        "tenant.search",
        "plan.view",
        "subscription.view",
        "subscription.manage",
        "invoice.view",
        "invoice.manage",
        "payment.confirm",
        "payment.refund.request",
        "payment.refund.approve",
        "payment.refund.complete",
        "audit.view",
        "settings.view",
        "diagnostics.view",
        "analytics.view",
    },
    OPS: {
        "platform.dashboard.view",
        "tenant.view",
        "tenant.search",
        "tenant.create",
        "tenant.suspend",
        "tenant.reactivate",
        "tenant.force_logout",
        "tenant.export",
        "plan.view",
        "subscription.view",
        "invoice.view",
        "audit.view",
        "settings.view",
        "diagnostics.view",
        "analytics.view",
    },
    SUPERADMIN: {
        "platform.dashboard.view",
        "tenant.view",
        "tenant.search",
        "tenant.create",
        "tenant.suspend",
        "tenant.reactivate",
        "tenant.force_logout",
        "tenant.export",
        "tenant.delete",
        "plan.view",
        "plan.manage",
        "subscription.view",
        "subscription.manage",
        "subscription.override",
        "invoice.view",
        "invoice.manage",
        "payment.confirm",
        "payment.void",
        "payment.refund.request",
        "payment.refund.approve",
        "payment.refund.complete",
        "platform_user.view",
        "platform_user.manage",
        "audit.view",
        "settings.view",
        "settings.manage",
        "diagnostics.view",
        "analytics.view",
    },
}


@pytest.mark.parametrize("role", [SUPPORT, BILLING, OPS, SUPERADMIN])
def test_each_role_has_the_expected_permission_set(role: str) -> None:
    assert PLATFORM_ROLE_PERMISSIONS[role] == frozenset(EXPECTED[role])


def test_permission_map_is_default_deny() -> None:
    assert permissions_for("owner") == frozenset()
    assert permissions_for("") == frozenset()
    assert not is_platform_role("owner")
    assert not has_permission("owner", "tenant.view")


def test_superadmin_owns_every_defined_permission() -> None:
    assert PLATFORM_PERMISSIONS == PLATFORM_ROLE_PERMISSIONS[SUPERADMIN]


def test_billing_cannot_void_payments_or_manage_platform_users() -> None:
    assert not has_permission(BILLING, "payment.void")
    assert not has_permission(BILLING, "platform_user.manage")
    assert not has_permission(SUPPORT, "payment.confirm")
    assert not has_permission(OPS, "payment.confirm")


def test_require_platform_permission_rejects_unknown_permission() -> None:
    with pytest.raises(ValueError, match="Unknown platform permission"):
        require_platform_permission("tenant.explode")


def _actor(role: str) -> PlatformActor:
    return PlatformActor(
        admin_id=uuid4(),
        email="admin@example.test",
        display_name="Admin",
        role=role,
        permissions=permissions_for(role),
        token_version=0,
        auth_time=datetime.now(UTC),
        step_up_at=None,
        mfa_enabled=True,
    )


def test_permission_dependency_allows_granted_role() -> None:
    dependency = require_platform_permission("tenant.view")

    actor = _actor(SUPPORT)

    assert dependency(actor=actor) is actor


def test_permission_dependency_denies_missing_permission() -> None:
    dependency = require_platform_permission("tenant.suspend")

    with pytest.raises(AppError) as excinfo:
        dependency(actor=_actor(BILLING))

    assert excinfo.value.status == 403
    assert excinfo.value.code == "FORBIDDEN"


@pytest.mark.parametrize(
    ("maker", "checker", "count", "expected"),
    [
        ("a", "a", 1, MAKER_CHECKER_ONLY_ONE),
        ("a", "a", 2, MAKER_CHECKER_SELF),
        ("a", "b", 2, MAKER_CHECKER_DISTINCT),
        ("a", "b", 5, MAKER_CHECKER_DISTINCT),
    ],
)
def test_maker_checker_status(maker, checker, count, expected) -> None:
    assert (
        maker_checker_status(
            maker_admin_id=maker,
            checker_admin_id=checker,
            active_admin_count=count,
        )
        == expected
    )


@pytest.fixture()
def db() -> Generator[Session, None, None]:
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def platform_admin(db: Session) -> Generator[PlatformAdmin, None, None]:
    admin = PlatformAdmin(
        email=f"{uuid4().hex}@example.test",
        password_hash="not-a-real-hash",
        display_name="Test Admin",
        role=BILLING,
        status="ACTIVE",
        token_version=0,
    )
    db.add(admin)
    db.commit()
    db.refresh(admin)
    try:
        yield admin
    finally:
        db.delete(admin)
        db.commit()


@pytest.fixture()
def platform_secret(monkeypatch) -> str:
    secret = "test-platform-secret-at-least-32-bytes"
    monkeypatch.setattr(settings, "platform_secret_key", secret)
    return secret


def _request_with_cookie(token: str):
    return SimpleNamespace(cookies={PLATFORM_ACCESS_COOKIE: token})


def test_get_platform_admin_reads_the_httponly_cookie(
    platform_admin: PlatformAdmin, db: Session, platform_secret: str
) -> None:
    token = create_platform_access_token(
        admin_id=platform_admin.id,
        role=platform_admin.role,
        token_version=platform_admin.token_version,
    )

    actor = get_platform_admin(request=_request_with_cookie(token), db=db)

    assert actor.admin_id == platform_admin.id
    assert actor.role == BILLING
    assert "payment.confirm" in actor.permissions


def test_get_platform_admin_requires_a_cookie(db: Session, platform_secret: str) -> None:
    with pytest.raises(AppError) as excinfo:
        get_platform_admin(request=SimpleNamespace(cookies={}), db=db)

    assert excinfo.value.status == 401
    assert excinfo.value.code == "AUTH_REQUIRED"


def test_get_platform_admin_rejects_a_stale_token_version(
    platform_admin: PlatformAdmin, db: Session, platform_secret: str
) -> None:
    token = create_platform_access_token(
        admin_id=platform_admin.id,
        role=platform_admin.role,
        token_version=0,
    )
    platform_admin.token_version = 1
    db.commit()

    with pytest.raises(AppError) as excinfo:
        get_platform_admin(request=_request_with_cookie(token), db=db)

    assert excinfo.value.code == "TOKEN_REVOKED"


def test_get_platform_admin_rejects_a_role_change(
    platform_admin: PlatformAdmin, db: Session, platform_secret: str
) -> None:
    token = create_platform_access_token(
        admin_id=platform_admin.id,
        role=BILLING,
        token_version=platform_admin.token_version,
    )
    platform_admin.role = SUPERADMIN
    db.commit()

    with pytest.raises(AppError) as excinfo:
        get_platform_admin(request=_request_with_cookie(token), db=db)

    assert excinfo.value.code == "TOKEN_REVOKED"


def test_get_platform_admin_rejects_a_disabled_admin(
    platform_admin: PlatformAdmin, db: Session, platform_secret: str
) -> None:
    token = create_platform_access_token(
        admin_id=platform_admin.id,
        role=platform_admin.role,
        token_version=platform_admin.token_version,
    )
    platform_admin.status = "DISABLED"
    db.commit()

    with pytest.raises(AppError) as excinfo:
        get_platform_admin(request=_request_with_cookie(token), db=db)

    assert excinfo.value.code == "INVALID_TOKEN"
