"""Regression tests for local development platform configuration.

The admin console is served by the shared Vite server over plain HTTP in dev
(PA-ADR-003). A fresh checkout with no platform secrets must still be able to
sign in: the origin allowlist accepts the configured dev origins, and the
platform realm signs/encrypts with a stable development-only key.
"""

from __future__ import annotations

from collections.abc import Generator

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.api.platform.router import platform_router
from app.core.config import Settings, settings
from app.core.security import hash_password
from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.modules.platform.models import PlatformAdmin
from app.shared.errors import AppError, app_error_handler

DEV_ORIGIN = "http://192.168.1.5:5173"
EMAIL = "dev-origin-admin@harbor.com"
PASSWORD = "PlatformPass!123"


def test_dev_origins_are_allowed_only_outside_production() -> None:
    dev = Settings(
        app_env="development",
        platform_admin_origin=DEV_ORIGIN,
        platform_dev_admin_origins="http://localhost:5173,http://127.0.0.1:5173",
    )
    assert dev.platform_admin_origin_list == [
        DEV_ORIGIN,
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]

    prod = Settings(
        app_env="production",
        platform_admin_origin="https://admin.example.com",
        platform_dev_admin_origins="http://localhost:5173",
    )
    assert prod.platform_admin_origin_list == ["https://admin.example.com"]


def test_dev_signing_and_mfa_keys_are_derived_but_production_requires_real_keys() -> None:
    dev = Settings(app_env="development", secret_key="staff-dev-secret")
    assert dev.platform_signing_key
    assert dev.platform_signing_key != dev.secret_key
    assert dev.platform_mfa_material

    # Explicit empty keys keep this assertion about configuration, not about
    # whatever a developer happens to have in their local .env file.
    prod = Settings(
        app_env="production",
        secret_key="staff-dev-secret",
        platform_secret_key="",
        platform_mfa_key="",
    )
    with pytest.raises(RuntimeError, match="PLATFORM_SECRET_KEY"):
        _ = prod.platform_signing_key
    with pytest.raises(RuntimeError, match="PLATFORM_MFA_KEY"):
        _ = prod.platform_mfa_material


def test_dev_cookies_are_not_secure_by_default() -> None:
    assert Settings(app_env="development").platform_cookie_secure is False


def _build_app() -> FastAPI:
    application = FastAPI()
    application.add_exception_handler(AppError, app_error_handler)
    application.include_router(platform_router, prefix="/api/platform")
    return application


@pytest.fixture()
def configured(monkeypatch) -> None:
    monkeypatch.setattr(settings, "platform_secret_key", "platform-test-secret-at-least-32-bytes")
    monkeypatch.setattr(settings, "platform_mfa_key", "platform-mfa-test-key-at-least-32-bytes")
    monkeypatch.setattr(settings, "platform_cookie_secure", False)
    monkeypatch.setattr(settings, "app_env", "development")
    monkeypatch.setattr(settings, "platform_admin_origin", DEV_ORIGIN)
    monkeypatch.setattr(
        settings,
        "platform_dev_admin_origins",
        "http://localhost:5173,http://127.0.0.1:5173",
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
def admin(db: Session) -> Generator[PlatformAdmin, None, None]:
    row = PlatformAdmin(
        email=EMAIL,
        password_hash=hash_password(PASSWORD),
        display_name="Dev Origin Admin",
        role="superadmin",
        status="ACTIVE",
        token_version=0,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    try:
        yield row
    finally:
        db.expire_all()
        existing = db.get(PlatformAdmin, row.id)
        if existing is not None:
            db.delete(existing)
            db.commit()


@pytest.fixture()
def client(configured, admin: PlatformAdmin) -> Generator[TestClient, None, None]:
    with TestClient(_build_app()) as test_client:
        yield test_client


@pytest.mark.parametrize(
    "origin",
    [DEV_ORIGIN, "http://localhost:5173", "http://127.0.0.1:5173"],
)
def test_login_accepts_each_configured_dev_origin(client: TestClient, origin: str) -> None:
    response = client.post(
        "/api/platform/auth/login",
        json={"email": EMAIL, "password": PASSWORD},
        headers={"Origin": origin},
    )
    assert response.status_code == 200, response.text
    assert response.json()["enrollment_required"] is True


def test_login_rejects_an_unlisted_origin(client: TestClient) -> None:
    response = client.post(
        "/api/platform/auth/login",
        json={"email": EMAIL, "password": PASSWORD},
        headers={"Origin": "http://evil.example"},
    )
    assert response.status_code == 403
    assert response.json()["code"] == "ORIGIN_INVALID"


def test_login_without_origin_is_still_rejected(client: TestClient) -> None:
    response = client.post(
        "/api/platform/auth/login",
        json={"email": EMAIL, "password": PASSWORD},
    )
    assert response.status_code == 403
    assert response.json()["code"] == "ORIGIN_INVALID"
