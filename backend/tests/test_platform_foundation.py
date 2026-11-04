"""PA-0 foundation — platform configuration and realm isolation.

These tests pin the two guardrails introduced before any platform model or
route exists:

- production refuses to start with an unsafe/incomplete platform config;
- a staff token can never be replayed against the platform realm (and vice
  versa), because the JWT carries an explicit ``realm`` claim.

No production domain, admin identity, or secret is invented here.
"""

import uuid

import pytest

from app.core.config import Settings
from app.core.security import create_access_token, decode_access_token
from app.shared.errors import AppError

# Minimum production-valid platform values. Deliberately generic: PA-ADR-011
# leaves the real domain and its owner to the operator.
_VALID_PRODUCTION_PLATFORM = {
    "app_env": "production",
    "platform_secret_key": "platform-secret-not-the-staff-secret-32",
    "platform_mfa_key": "platform-mfa-key-at-least-32-characters",
    "platform_admin_origin": "https://admin.platform.example",
    "platform_api_origin": "https://api.platform.example",
    "platform_cookie_secure": True,
    "platform_cookie_domain": "",
}


def _production_settings(**overrides) -> Settings:
    values = {**_VALID_PRODUCTION_PLATFORM, **overrides}
    return Settings(**values)


def test_platform_config_is_optional_outside_production() -> None:
    dev = Settings(app_env="development")

    # Must not raise even though the platform realm is unconfigured.
    dev.validate_platform_config()


def test_platform_config_rejects_missing_production_values() -> None:
    incomplete = Settings(
        app_env="production",
        platform_secret_key="",
        platform_mfa_key="",
        platform_admin_origin="",
        platform_api_origin="",
    )

    with pytest.raises(RuntimeError) as excinfo:
        incomplete.validate_platform_config()

    message = str(excinfo.value)
    assert "PLATFORM_SECRET_KEY" in message
    assert "PLATFORM_MFA_KEY" in message
    assert "PLATFORM_ADMIN_ORIGIN" in message
    assert "PLATFORM_API_ORIGIN" in message


def test_platform_config_accepts_valid_production_values() -> None:
    _production_settings().validate_platform_config()


def test_platform_secret_must_differ_from_staff_secret() -> None:
    shared = "the-same-key-everywhere"
    settings = _production_settings(secret_key=shared, platform_secret_key=shared)

    with pytest.raises(RuntimeError, match="must differ from SECRET_KEY"):
        settings.validate_platform_config()


def test_platform_config_rejects_shared_cookie_domain() -> None:
    settings = _production_settings(platform_cookie_domain=".platform.example")

    with pytest.raises(RuntimeError, match="host-only cookies"):
        settings.validate_platform_config()


def test_platform_config_requires_secure_cookies_in_production() -> None:
    settings = _production_settings(platform_cookie_secure=False)

    with pytest.raises(RuntimeError, match="PLATFORM_COOKIE_SECURE"):
        settings.validate_platform_config()


def _token(**overrides) -> str:
    claims = {
        "user_id": uuid.uuid4(),
        "membership_id": uuid.uuid4(),
        "restaurant_id": uuid.uuid4(),
        "tenant_id": uuid.uuid4(),
        "realm": "staff",
    }
    claims.update(overrides)
    return create_access_token(**claims)


def test_staff_token_decodes_in_the_staff_realm() -> None:
    user_id = uuid.uuid4()

    payload = decode_access_token(_token(user_id=user_id))

    assert payload["sub"] == str(user_id)
    assert payload["realm"] == "staff"


def test_platform_token_is_rejected_by_the_staff_realm() -> None:
    token = _token(realm="platform")

    with pytest.raises(AppError) as excinfo:
        decode_access_token(token)

    assert excinfo.value.status == 401
    assert excinfo.value.code == "WRONG_REALM"


def test_staff_token_is_rejected_by_the_platform_realm() -> None:
    token = _token(realm="staff")

    with pytest.raises(AppError) as excinfo:
        decode_access_token(token, expected_realm="platform")

    assert excinfo.value.code == "WRONG_REALM"


def test_platform_token_decodes_in_the_platform_realm() -> None:
    token = _token(realm="platform")

    payload = decode_access_token(token, expected_realm="platform")

    assert payload["realm"] == "platform"
