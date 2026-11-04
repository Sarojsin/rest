"""PA-0.7 — step-up re-authentication for sensitive platform actions."""

from __future__ import annotations

from collections.abc import Generator
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.api.platform.router import platform_router
from app.core.config import settings
from app.core.security import decode_platform_access_token, hash_password
from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.modules.platform.constants import PLATFORM_CSRF_COOKIE
from app.modules.platform.deps import PlatformActor, require_platform_step_up
from app.modules.platform.models import PlatformAdmin
from app.modules.platform.permissions import permissions_for
from app.modules.platform.services.mfa import totp_at
from app.shared.errors import AppError, app_error_handler

ORIGIN = "https://admin.harbor.com"
EMAIL = "stepup-admin@harbor.com"
PASSWORD = "PlatformPass!123"


def _app() -> FastAPI:
    application = FastAPI()
    application.add_exception_handler(AppError, app_error_handler)
    application.include_router(platform_router, prefix="/api/platform")
    return application


def _headers(csrf: str | None = None) -> dict:
    headers = {"Origin": ORIGIN}
    if csrf:
        headers["X-CSRF-Token"] = csrf
    return headers


@pytest.fixture()
def configured(monkeypatch):
    monkeypatch.setattr(settings, "platform_secret_key", "platform-test-secret-at-least-32-bytes")
    monkeypatch.setattr(settings, "platform_mfa_key", "platform-mfa-test-key-at-least-32-bytes")
    monkeypatch.setattr(settings, "platform_cookie_secure", False)
    monkeypatch.setattr(settings, "platform_admin_origin", ORIGIN)
    monkeypatch.setattr(settings, "platform_step_up_minutes", 5)


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
        display_name="Step Up Admin",
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
    with TestClient(_app()) as test_client:
        yield test_client


def _enroll(client: TestClient) -> tuple[str, list[str]]:
    challenge = client.post(
        "/api/platform/auth/login",
        json={"email": EMAIL, "password": PASSWORD},
        headers=_headers(),
    ).json()
    started = client.post(
        "/api/platform/auth/mfa/enroll/start",
        json={"ticket": challenge["ticket"]},
        headers=_headers(),
    ).json()
    verified = client.post(
        "/api/platform/auth/mfa/enroll/verify",
        json={
            "ticket": challenge["ticket"],
            "code": totp_at(started["secret"], datetime.now(UTC)),
        },
        headers=_headers(),
    )
    assert verified.status_code == 200, verified.text
    return started["secret"], verified.json().get("recovery_codes") or []


def test_fresh_step_up_passes(configured) -> None:
    actor = PlatformActor(
        admin_id=uuid4(),
        email=EMAIL,
        display_name="Admin",
        role="superadmin",
        permissions=permissions_for("superadmin"),
        token_version=0,
        auth_time=datetime.now(UTC),
        step_up_at=datetime.now(UTC),
        mfa_enabled=True,
    )
    assert require_platform_step_up(actor=actor) is actor


def test_stale_step_up_is_rejected(configured) -> None:
    stale = datetime.now(UTC) - timedelta(minutes=settings.platform_step_up_minutes + 1)
    actor = PlatformActor(
        admin_id=uuid4(),
        email=EMAIL,
        display_name="Admin",
        role="superadmin",
        permissions=permissions_for("superadmin"),
        token_version=0,
        auth_time=stale,
        step_up_at=stale,
        mfa_enabled=True,
    )

    with pytest.raises(AppError) as excinfo:
        require_platform_step_up(actor=actor)

    assert excinfo.value.code == "STEP_UP_REQUIRED"
    assert excinfo.value.extra["max_age_seconds"] == settings.platform_step_up_minutes * 60


def test_step_up_reissues_the_access_cookie_only(client: TestClient) -> None:
    secret, _ = _enroll(client)

    old_access = client.cookies.get("platform_access")
    old_refresh = client.cookies.get("platform_refresh")
    csrf = client.cookies.get(PLATFORM_CSRF_COOKIE)

    response = client.post(
        "/api/platform/auth/step-up",
        json={"password": PASSWORD, "code": totp_at(secret, datetime.now(UTC))},
        headers=_headers(csrf),
    )
    assert response.status_code == 200, response.text
    assert response.json()["step_up_expires_in"] == settings.platform_step_up_minutes * 60

    new_access = client.cookies.get("platform_access")
    assert new_access and new_access != old_access
    assert client.cookies.get("platform_refresh") == old_refresh

    payload = decode_platform_access_token(new_access)
    assert datetime.now(UTC).timestamp() - payload["step_up_at"] < 30


def test_step_up_rejects_a_wrong_code(client: TestClient) -> None:
    _enroll(client)
    csrf = client.cookies.get(PLATFORM_CSRF_COOKIE)

    response = client.post(
        "/api/platform/auth/step-up",
        json={"password": PASSWORD, "code": "000000"},
        headers=_headers(csrf),
    )
    assert response.status_code == 401
    assert response.json()["code"] == "MFA_INVALID"


def test_step_up_requires_csrf(client: TestClient) -> None:
    _enroll(client)

    response = client.post(
        "/api/platform/auth/step-up",
        json={"password": PASSWORD, "code": "000000"},
        headers=_headers(),
    )
    assert response.status_code == 403
    assert response.json()["code"] == "CSRF_INVALID"


def test_step_up_accepts_a_recovery_code(client: TestClient) -> None:
    _, recovery_codes = _enroll(client)
    csrf = client.cookies.get(PLATFORM_CSRF_COOKIE)

    response = client.post(
        "/api/platform/auth/step-up",
        json={"password": PASSWORD, "code": recovery_codes[0]},
        headers=_headers(csrf),
    )
    assert response.status_code == 200, response.text
