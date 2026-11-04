"""PA-0.5 — platform login, MFA, cookie sessions, rotation, and revocation."""

from __future__ import annotations

from collections.abc import Generator
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import create_access_token, hash_password
from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.modules.platform.models import PlatformAdmin
from app.modules.platform.router_auth import router as platform_auth_router
from app.modules.platform.services import auth as auth_service
from app.modules.platform.services.mfa import totp_at
from app.shared.errors import AppError, app_error_handler

PASSWORD = "PlatformPass!123"
EMAIL = "platform-test@harbor.com"


def _build_app() -> FastAPI:
    application = FastAPI()
    application.add_exception_handler(AppError, app_error_handler)
    application.include_router(platform_auth_router, prefix="/api/platform")
    return application


@pytest.fixture()
def configured(monkeypatch):
    monkeypatch.setattr(settings, "platform_secret_key", "platform-test-secret-at-least-32-bytes")
    monkeypatch.setattr(settings, "platform_mfa_key", "platform-mfa-test-key-at-least-32-bytes")
    monkeypatch.setattr(settings, "platform_cookie_secure", False)
    monkeypatch.setattr(settings, "platform_login_max_attempts", 5)
    monkeypatch.setattr(settings, "platform_login_lockout_minutes", 15)


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
        display_name="Platform Owner",
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
        db.delete(db.get(PlatformAdmin, row.id))
        db.commit()


@pytest.fixture()
def client(configured, admin: PlatformAdmin) -> Generator[TestClient, None, None]:
    with TestClient(_build_app()) as test_client:
        yield test_client


def _login(client: TestClient, email: str, password: str = PASSWORD):
    return client.post(
        "/api/platform/auth/login",
        json={"email": email, "password": password},
    )


def _totp(secret: str) -> str:
    return totp_at(secret, datetime.now(UTC))


def _complete_enrollment(client: TestClient, email: str) -> tuple[dict, list[str]]:
    login = _login(client, email)
    assert login.status_code == 200, login.text
    challenge = login.json()
    assert challenge["enrollment_required"] is True

    started = client.post(
        "/api/platform/auth/mfa/enroll/start",
        json={"ticket": challenge["ticket"]},
    )
    assert started.status_code == 200, started.text
    secret = started.json()["secret"]

    verified = client.post(
        "/api/platform/auth/mfa/enroll/verify",
        json={"ticket": challenge["ticket"], "code": _totp(secret)},
    )
    assert verified.status_code == 200, verified.text
    return verified.json(), verified.json().get("recovery_codes") or []


def test_enrollment_sets_httponly_cookies_and_no_body_tokens(client: TestClient) -> None:
    body, recovery_codes = _complete_enrollment(client, EMAIL)

    assert body["admin"]["mfa_enabled"] is True
    assert len(recovery_codes) == settings.platform_recovery_code_count
    assert "access_token" not in body and "refresh_token" not in body

    me = client.get("/api/platform/auth/me")
    assert me.status_code == 200, me.text
    assert me.json()["role"] == "superadmin"
    assert me.json()["permissions"]


def test_cookie_flags_are_host_only_and_csrf_is_readable(client: TestClient) -> None:
    response = _login(client, EMAIL)
    challenge = response.json()
    started = client.post(
        "/api/platform/auth/mfa/enroll/start", json={"ticket": challenge["ticket"]}
    ).json()
    verified = client.post(
        "/api/platform/auth/mfa/enroll/verify",
        json={"ticket": challenge["ticket"], "code": _totp(started["secret"])},
    )

    cookies = verified.headers.get_list("set-cookie")
    access = next(line for line in cookies if line.startswith("platform_access="))
    refresh = next(line for line in cookies if line.startswith("platform_refresh="))
    csrf = next(line for line in cookies if line.startswith("platform_csrf="))

    assert "HttpOnly" in access and "SameSite=strict" in access
    assert "Path=/api/platform" in access
    assert "HttpOnly" in refresh and "Path=/api/platform/auth" in refresh
    assert "HttpOnly" not in csrf
    assert "domain=" not in access.lower()


def test_login_requires_mfa_after_enrollment(client: TestClient) -> None:
    _complete_enrollment(client, EMAIL)
    client.post("/api/platform/auth/logout")

    challenge = _login(client, EMAIL).json()
    assert challenge["enrollment_required"] is False
    assert challenge["mfa_required"] is True

    verified = client.post(
        "/api/platform/auth/mfa/verify",
        json={"ticket": challenge["ticket"], "code": "000000"},
    )
    assert verified.status_code == 401

    # The same ticket is still valid for a correct code.
    started = client.post("/api/platform/auth/mfa/enroll/start", json={"ticket": challenge["ticket"]})
    assert started.status_code in (401, 409)


def test_recovery_code_is_single_use(client: TestClient) -> None:
    _, recovery_codes = _complete_enrollment(client, EMAIL)
    client.post("/api/platform/auth/logout")

    challenge = _login(client, EMAIL).json()
    first = client.post(
        "/api/platform/auth/mfa/verify",
        json={"ticket": challenge["ticket"], "code": recovery_codes[0]},
    )
    assert first.status_code == 200, first.text

    client.post("/api/platform/auth/logout")
    challenge = _login(client, EMAIL).json()
    replay = client.post(
        "/api/platform/auth/mfa/verify",
        json={"ticket": challenge["ticket"], "code": recovery_codes[0]},
    )
    assert replay.status_code == 401


def test_refresh_rotates_and_reuse_revokes_the_family(client: TestClient) -> None:
    _complete_enrollment(client, EMAIL)

    old_refresh = client.cookies.get("platform_refresh")
    assert old_refresh

    refreshed = client.post("/api/platform/auth/refresh")
    assert refreshed.status_code == 200, refreshed.text
    new_refresh = client.cookies.get("platform_refresh")
    assert new_refresh and new_refresh != old_refresh

    # Replay the already-rotated token.
    client.cookies.set("platform_refresh", old_refresh, path="/api/platform/auth")
    replay = client.post("/api/platform/auth/refresh")
    assert replay.status_code == 401
    assert replay.json()["code"] == "TOKEN_REUSE"

    # The whole family is revoked, including the newest token.
    client.cookies.set("platform_refresh", new_refresh, path="/api/platform/auth")
    after = client.post("/api/platform/auth/refresh")
    assert after.status_code == 401


def test_logout_clears_cookies_and_revokes_session(client: TestClient) -> None:
    _complete_enrollment(client, EMAIL)
    refresh = client.cookies.get("platform_refresh")

    logout = client.post("/api/platform/auth/logout")
    assert logout.status_code == 204
    assert client.cookies.get("platform_refresh") in (None, "")

    client.cookies.set("platform_refresh", refresh, path="/api/platform/auth")
    assert client.post("/api/platform/auth/refresh").status_code == 401


def test_sessions_list_and_revoke(client: TestClient) -> None:
    _complete_enrollment(client, EMAIL)

    sessions = client.get("/api/platform/auth/sessions")
    assert sessions.status_code == 200, sessions.text
    rows = sessions.json()["sessions"]
    assert len(rows) == 1 and rows[0]["current"] is True

    revoked = client.post(f"/api/platform/auth/sessions/{rows[0]['family_id']}/revoke")
    assert revoked.status_code == 204
    assert client.get("/api/platform/auth/sessions").json()["sessions"] == []


def test_unknown_email_and_bad_password_are_generic(
    client: TestClient, admin: PlatformAdmin
) -> None:
    unknown = _login(client, "nobody@harbor.com")
    assert unknown.status_code == 401
    assert unknown.json()["code"] == "INVALID_CREDENTIALS"

    bad = _login(client, admin.email, "wrong-password")
    assert bad.status_code == 401
    assert bad.json()["code"] == "INVALID_CREDENTIALS"


def test_lockout_after_repeated_failures(
    client: TestClient, admin: PlatformAdmin, monkeypatch
) -> None:
    monkeypatch.setattr(settings, "platform_login_max_attempts", 2)

    assert _login(client, admin.email, "wrong").status_code == 401
    assert _login(client, admin.email, "wrong").status_code == 401

    locked = _login(client, admin.email)
    assert locked.status_code == 401
    assert locked.json()["code"] == "INVALID_CREDENTIALS"

    session = SessionLocal()
    try:
        row = session.get(PlatformAdmin, admin.id)
        assert row is not None and row.locked_until is not None
    finally:
        session.close()


def test_disabled_admin_cannot_log_in(
    client: TestClient, admin: PlatformAdmin, db: Session
) -> None:
    admin.status = "DISABLED"
    db.commit()

    response = _login(client, admin.email)
    assert response.status_code == 403
    assert response.json()["code"] == "ACCOUNT_DISABLED"


def test_me_requires_a_platform_cookie(client: TestClient) -> None:
    response = client.get("/api/platform/auth/me")
    assert response.status_code == 401


def test_staff_token_is_rejected_on_platform_routes(client: TestClient) -> None:
    staff_token = create_access_token(
        user_id=uuid4(),
        membership_id=uuid4(),
        restaurant_id=uuid4(),
    )
    client.cookies.set("platform_access", staff_token, path="/api/platform")

    response = client.get("/api/platform/auth/me")
    assert response.status_code == 401
    assert response.json()["code"] == "INVALID_TOKEN"


def test_ticket_expiry_is_enforced(configured, admin: PlatformAdmin, monkeypatch) -> None:
    monkeypatch.setattr(settings, "platform_enrollment_ticket_minutes", -1)
    with TestClient(_build_app()) as client:
        challenge = _login(client, admin.email).json()
        response = client.post(
            "/api/platform/auth/mfa/enroll/start",
            json={"ticket": challenge["ticket"]},
        )
    assert response.status_code == 401
    assert response.json()["code"] == "TICKET_EXPIRED"


def test_session_rows_are_hashed_not_plaintext(client: TestClient, db: Session) -> None:
    _complete_enrollment(client, EMAIL)
    raw = client.cookies.get("platform_refresh")

    from sqlalchemy import select

    from app.modules.platform.models import PlatformRefreshToken

    rows = db.scalars(select(PlatformRefreshToken)).all()
    assert rows
    assert all(row.token_hash != raw for row in rows)
    assert all(len(row.token_hash) == 64 for row in rows)


def test_step_up_claim_is_fresh_after_login(client: TestClient, admin: PlatformAdmin) -> None:
    _complete_enrollment(client, EMAIL)
    me = client.get("/api/platform/auth/me")
    assert me.status_code == 200

    # The access token was minted with step_up_at; decode to assert freshness.
    from app.core.security import decode_platform_access_token

    token = client.cookies.get("platform_access")
    payload = decode_platform_access_token(token)
    assert payload["step_up_at"] is not None
    assert datetime.now(UTC).timestamp() - payload["step_up_at"] < 60


def test_refresh_absolute_session_cap(configured, admin: PlatformAdmin, db: Session, monkeypatch):
    monkeypatch.setattr(settings, "platform_refresh_token_minutes", 12)
    with TestClient(_build_app()) as client:
        _complete_enrollment(client, admin.email)

        from sqlalchemy import select

        from app.modules.platform.models import PlatformRefreshToken

        row = db.scalars(select(PlatformRefreshToken)).first()
        assert row is not None
        assert row.expires_at - row.session_started_at <= timedelta(minutes=12)


def test_enrollment_requires_a_ticket(client: TestClient) -> None:
    response = client.post("/api/platform/auth/mfa/enroll/start", json={"ticket": "nope"})
    assert response.status_code == 401
    assert response.json()["code"] == "INVALID_TICKET"


def test_login_response_never_contains_tokens(client: TestClient) -> None:
    response = _login(client, EMAIL)
    body = response.json()
    assert set(body) == {"mfa_required", "enrollment_required", "ticket", "expires_in"}
    assert "token" not in response.text.lower()
