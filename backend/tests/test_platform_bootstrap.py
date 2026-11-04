"""PA-0.9 — production bootstrap and development-only platform seed."""

from __future__ import annotations

from collections.abc import Generator

import pytest
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.security import hash_password
from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.modules.platform.models import PlatformAdmin, PlatformAuditLog
from app.modules.platform.services.bootstrap import (
    BOOTSTRAP_ACTION,
    BOOTSTRAP_REENABLED_ACTION,
    DEV_PLATFORM_ADMINS,
    bootstrap_platform,
    seed_platform_dev,
)

BOOTSTRAP_EMAIL = "primary@harbor.com"
BOOTSTRAP_PASSWORD = "PrimaryPlatform!123"


def _production_settings(**overrides) -> Settings:
    values = {
        "app_env": "production",
        "platform_bootstrap_email": BOOTSTRAP_EMAIL,
        "platform_bootstrap_password": BOOTSTRAP_PASSWORD,
    }
    values.update(overrides)
    return Settings(**values)


@pytest.fixture()
def db() -> Generator[Session, None, None]:
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    session.execute(delete(PlatformAuditLog))
    session.execute(delete(PlatformAdmin))
    session.commit()
    try:
        yield session
    finally:
        session.rollback()
        session.execute(delete(PlatformAuditLog))
        session.execute(delete(PlatformAdmin))
        session.commit()
        session.close()


def _superadmins(db: Session) -> list[PlatformAdmin]:
    return list(
        db.scalars(
            select(PlatformAdmin).where(PlatformAdmin.role == "superadmin")
        ).all()
    )


def test_bootstrap_creates_exactly_one_primary_superadmin(db: Session) -> None:
    bootstrap_platform(db, _production_settings())

    admins = _superadmins(db)
    assert len(admins) == 1
    assert admins[0].email == BOOTSTRAP_EMAIL
    assert admins[0].status == "ACTIVE"
    assert admins[0].mfa_enabled_at is None  # enrollment required on first login

    actions = db.scalars(
        select(PlatformAuditLog.action).where(PlatformAuditLog.action == BOOTSTRAP_ACTION)
    ).all()
    assert actions == [BOOTSTRAP_ACTION]


def test_bootstrap_is_idempotent(db: Session) -> None:
    settings = _production_settings()
    bootstrap_platform(db, settings)
    bootstrap_platform(db, settings)

    assert len(_superadmins(db)) == 1


def test_bootstrap_does_not_add_a_second_admin_when_one_is_active(db: Session) -> None:
    db.add(
        PlatformAdmin(
            email="existing@harbor.com",
            password_hash=hash_password("ExistingPlatform!123"),
            display_name="Existing",
            role="superadmin",
            status="ACTIVE",
            token_version=0,
        )
    )
    db.commit()

    # No bootstrap env needed: an active superadmin already exists.
    bootstrap_platform(db, Settings(app_env="production"))

    admins = _superadmins(db)
    assert len(admins) == 1
    assert admins[0].email == "existing@harbor.com"


def test_bootstrap_fails_without_credentials_when_empty(db: Session) -> None:
    with pytest.raises(RuntimeError, match="PLATFORM_BOOTSTRAP_EMAIL"):
        bootstrap_platform(
            db,
            Settings(
                app_env="production",
                platform_bootstrap_email="",
                platform_bootstrap_password="",
            ),
        )

    assert _superadmins(db) == []


def test_bootstrap_rejects_a_short_password(db: Session) -> None:
    with pytest.raises(RuntimeError, match="at least 12"):
        bootstrap_platform(
            db,
            _production_settings(platform_bootstrap_password="short"),
        )


def test_bootstrap_reenables_the_configured_account_without_changing_secrets(
    db: Session,
) -> None:
    original_hash = hash_password("ExistingPlatform!123")
    admin = PlatformAdmin(
        email=BOOTSTRAP_EMAIL,
        password_hash=original_hash,
        display_name="Primary",
        role="superadmin",
        status="DISABLED",
        disabled_reason="incident",
        token_version=0,
    )
    db.add(admin)
    db.commit()

    bootstrap_platform(db, _production_settings())

    refreshed = db.scalar(select(PlatformAdmin).where(PlatformAdmin.email == BOOTSTRAP_EMAIL))
    assert refreshed is not None
    assert refreshed.status == "ACTIVE"
    assert refreshed.disabled_reason is None
    assert refreshed.password_hash == original_hash

    actions = db.scalars(
        select(PlatformAuditLog.action).where(
            PlatformAuditLog.action == BOOTSTRAP_REENABLED_ACTION
        )
    ).all()
    assert actions == [BOOTSTRAP_REENABLED_ACTION]


def test_dev_seed_creates_the_documented_role_fixtures(db: Session) -> None:
    seed_platform_dev(
        db,
        Settings(app_env="development", platform_mfa_key="platform-mfa-test-key-at-least-32-bytes"),
    )

    emails = set(
        db.scalars(select(PlatformAdmin.email)).all()
    )
    expected = {email for email, *_ in DEV_PLATFORM_ADMINS}
    assert emails == expected
    assert len(_superadmins(db)) == 2

    seeded = db.scalar(
        select(PlatformAdmin).where(PlatformAdmin.email == "platform@harbor.example")
    )
    assert seeded is not None
    assert seeded.mfa_enabled_at is not None
    assert seeded.mfa_secret_encrypted


def test_dev_seed_can_leave_mfa_enrollment_for_first_login(db: Session) -> None:
    seed_platform_dev(db, Settings(app_env="development", platform_mfa_key=""))

    seeded = db.scalar(
        select(PlatformAdmin).where(PlatformAdmin.email == "platform@harbor.example")
    )
    assert seeded is not None
    assert seeded.mfa_enabled_at is None
    assert seeded.mfa_secret_encrypted is None


def test_dev_seed_never_runs_in_production(db: Session) -> None:
    seed_platform_dev(db, Settings(app_env="production"))

    assert db.scalar(select(PlatformAdmin.id)) is None


def test_dev_seed_is_idempotent(db: Session) -> None:
    settings = Settings(app_env="development", platform_mfa_key="")
    seed_platform_dev(db, settings)
    seed_platform_dev(db, settings)

    assert len(list(db.scalars(select(PlatformAdmin)).all())) == len(DEV_PLATFORM_ADMINS)
