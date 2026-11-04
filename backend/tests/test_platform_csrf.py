"""PA-0.6 — Origin and CSRF guards on platform routes."""

from __future__ import annotations

from collections.abc import Generator
from datetime import UTC, datetime

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.api.platform.router import platform_router
from app.core.config import settings
from app.core.security import hash_password
from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.modules.platform.constants import PLATFORM_CSRF_COOKIE
from app.modules.platform.models import PlatformAdmin
from app.modules.platform.services.mfa import totp_at
from app.shared.errors import AppError, app_error_handler

ADMIN_ORIGIN = "https://admin.harbor.com"
EMAIL = "csrf-admin@harbor.com"
PASSWORD = "PlatformPass!123"


def _build_app() -> FastAPI:
    application = FastAPI()
    application.add_exception_handler(AppError, app_error_handler)
    application.include_router(platform_router, prefix="/api/platform")
    return application


def _headers(origin: str | None = ADMIN_ORIGIN, csrf: str | None = None) -> dict:
    headers = {}
    if origin is not None:
        headers["Origin"] = origin
    if csrf is not None:
        headers["X-CSRF-Token"] = csrf
    return headers


@pytest.fixture()
def configured(monkeypatch):
    monkeypatch.setattr(settings, "platform_secret_key", "platform-test-secret-at-least-32-bytes")
    monkeypatch.setattr(settings, "platform_mfa_key", "platform-mfa-test-key-at-least-32-bytes")
    monkeypatch.setattr(settings, "platform_cookie_secure", False)
    monkeypatch.setattr(settings, "platform_admin_origin", ADMIN_ORIGIN)


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
        display_name="CSRF Admin",
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


def _login(client: TestClient, *, origin: str | None = ADMIN_ORIGIN):
    return client.post(
        "/api/platform/auth/login",
        json={"email": EMAIL, "password": PASSWORD},
        headers=_headers(origin),
    )


def _enroll(client: TestClient) -> list[str]:
    challenge = _login(client).json()
    started = client.post(
        "/api/platform/auth/mfa/enroll/start",
        json={"ticket": challenge["ticket"]},
        headers=_headers(),
    )
    assert started.status_code == 200, started.text
    secret = started.json()["secret"]
    verified = client.post(
        "/api/platform/auth/mfa/enroll/verify",
        json={
            "ticket": challenge["ticket"],
            "code": totp_at(secret, datetime.now(UTC)),
        },
        headers=_headers(),
    )
    assert verified.status_code == 200, verified.text
    return verified.json().get("recovery_codes") or []


def test_login_without_origin_is_rejected(client: TestClient) -> None:
    response = _login(client, origin=None)
    assert response.status_code == 403
    assert response.json()["code"] == "ORIGIN_INVALID"


def test_login_from_an_unlisted_origin_is_rejected(client: TestClient) -> None:
    response = _login(client, origin="https://evil.example")
    assert response.status_code == 403
    assert response.json()["code"] == "ORIGIN_INVALID"


def test_login_from_the_admin_origin_succeeds(client: TestClient) -> None:
    response = _login(client)
    assert response.status_code == 200


def test_referer_is_accepted_as_an_origin_fallback(client: TestClient) -> None:
    response = client.post(
        "/api/platform/auth/login",
        json={"email": EMAIL, "password": PASSWORD},
        headers={"Referer": f"{ADMIN_ORIGIN}/login"},
    )
    assert response.status_code == 200


def test_logout_requires_a_matching_csrf_token(client: TestClient) -> None:
    _enroll(client)
    csrf = client.cookies.get(PLATFORM_CSRF_COOKIE)
    assert csrf

    missing = client.post("/api/platform/auth/logout", headers=_headers())
    assert missing.status_code == 403
    assert missing.json()["code"] == "CSRF_INVALID"

    wrong = client.post(
        "/api/platform/auth/logout",
        headers=_headers(csrf="not-the-token"),
    )
    assert wrong.status_code == 403

    accepted = client.post(
        "/api/platform/auth/logout",
        headers=_headers(csrf=csrf),
    )
    assert accepted.status_code == 204


def test_refresh_is_csrf_exempt_but_origin_checked(client: TestClient) -> None:
    _enroll(client)

    no_origin = client.post("/api/platform/auth/refresh", headers=_headers(origin=None))
    assert no_origin.status_code == 403

    refreshed = client.post("/api/platform/auth/refresh", headers=_headers())
    assert refreshed.status_code == 200


def test_safe_get_does_not_require_origin_or_csrf(client: TestClient) -> None:
    _enroll(client)
    response = client.get("/api/platform/auth/me")
    assert response.status_code == 200


def test_session_revocation_requires_csrf(client: TestClient) -> None:
    _enroll(client)
    sessions = client.get("/api/platform/auth/sessions").json()["sessions"]
    family_id = sessions[0]["family_id"]

    denied = client.post(
        f"/api/platform/auth/sessions/{family_id}/revoke",
        headers=_headers(),
    )
    assert denied.status_code == 403

    csrf = client.cookies.get(PLATFORM_CSRF_COOKIE)
    allowed = client.post(
        f"/api/platform/auth/sessions/{family_id}/revoke",
        headers=_headers(csrf=csrf),
    )
    assert allowed.status_code == 204


def test_allowed_origins_include_the_platform_origin(configured, monkeypatch) -> None:
    monkeypatch.setattr(settings, "platform_admin_origin", ADMIN_ORIGIN)
    monkeypatch.setattr(settings, "platform_tenant_origin", "https://www.harbor.com")
    origins = settings.allowed_origin_list
    assert ADMIN_ORIGIN in origins
    assert "https://www.harbor.com" in origins
    assert len(origins) == len(set(origins))
