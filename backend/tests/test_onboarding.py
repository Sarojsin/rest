"""Integration tests for Plan 08 — Admin Onboarding Wizard.

Tests the single-endpoint transactional onboarding flow:
POST /api/platform/onboarding/restaurants

Creates tenant + subscription + branches + owner invitation atomically.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import jwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text as _text

from app.core.config import settings
from app.core.security import hash_password
from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.main import app
from app.modules.platform.models import PlatformPlan, PlatformPlanVersion

CSRF_TOKEN = "test-csrf-token-12345"


def _platform_auth_headers(client: TestClient, admin_id) -> dict:
    """Mint a platform access JWT (same pattern as plan version tests)."""
    now = datetime.now(UTC)
    token = jwt.encode(
        {
            "sub": str(admin_id),
            "realm": "platform",
            "role": "superadmin",
            "ver": 0,
            "jti": str(uuid4()),
            "auth_time": int(now.timestamp()),
            "step_up_at": int(now.timestamp()),
            "exp": int(
                (now + timedelta(minutes=settings.platform_access_token_minutes)).timestamp()
            ),
        },
        settings.platform_signing_key,
        algorithm="HS256",
    )
    client.cookies.set("platform_access", token)
    client.cookies.set("platform_csrf", CSRF_TOKEN)
    return {
        "Origin": "http://localhost:5173",
        "X-CSRF-Token": CSRF_TOKEN,
    }


def _cleanup(db, slug_prefix: str) -> None:
    like = f"{slug_prefix}%"
    db.execute(
        _text(
            "DELETE FROM platform_one_time_tokens WHERE restaurant_id IN "
            "(SELECT id FROM restaurants WHERE slug LIKE :like)"
        ),
        {"like": like},
    )
    db.execute(
        _text(
            "DELETE FROM platform_tenant_usage WHERE restaurant_id IN "
            "(SELECT id FROM restaurants WHERE slug LIKE :like)"
        ),
        {"like": like},
    )
    db.execute(
        _text(
            "DELETE FROM platform_usage_events WHERE restaurant_id IN "
            "(SELECT id FROM restaurants WHERE slug LIKE :like)"
        ),
        {"like": like},
    )
    db.execute(
        _text(
            "DELETE FROM platform_subscriptions WHERE restaurant_id IN "
            "(SELECT id FROM restaurants WHERE slug LIKE :like)"
        ),
        {"like": like},
    )
    db.execute(
        _text("DELETE FROM platform_plan_features WHERE plan_version_id IN "
              "(SELECT id FROM platform_plan_versions WHERE plan_id IN "
              "(SELECT id FROM platform_plans WHERE code LIKE :code))"),
        {"code": "onboard-plan-%"},
    )
    db.execute(
        _text("DELETE FROM platform_plan_limits WHERE plan_version_id IN "
              "(SELECT id FROM platform_plan_versions WHERE plan_id IN "
              "(SELECT id FROM platform_plans WHERE code LIKE :code))"),
        {"code": "onboard-plan-%"},
    )
    db.execute(
        _text("DELETE FROM platform_plan_versions WHERE plan_id IN "
              "(SELECT id FROM platform_plans WHERE code LIKE :code)"),
        {"code": "onboard-plan-%"},
    )
    db.execute(
        _text("DELETE FROM platform_plans WHERE code LIKE :code"),
        {"code": "onboard-plan-%"},
    )
    db.execute(
        _text("DELETE FROM restaurant_memberships WHERE restaurant_id IN "
              "(SELECT id FROM restaurants WHERE slug LIKE :like)"),
        {"like": like},
    )
    db.execute(
        _text("DELETE FROM users WHERE email LIKE :email"),
        {"email": "onboard-owner-%@example.com"},
    )
    db.execute(
        _text("DELETE FROM branches WHERE restaurant_id IN "
              "(SELECT id FROM restaurants WHERE slug LIKE :like)"),
        {"like": like},
    )
    db.execute(
        _text("DELETE FROM restaurant_settings WHERE restaurant_id IN "
              "(SELECT id FROM restaurants WHERE slug LIKE :like)"),
        {"like": like},
    )
    db.execute(
        _text("DELETE FROM restaurants WHERE slug LIKE :like"),
        {"like": like},
    )
    db.commit()


@pytest.fixture(scope="function")
def env():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        # Create a platform admin for auth
        admin_id = uuid4()
        db.execute(
            _text(
                "INSERT INTO platform_admins (id, email, password_hash, display_name, "
                "role, status, token_version, failed_login_count, created_at, updated_at) "
                "VALUES (:id, :email, :hash, 'Onboarding Admin', 'superadmin', "
                "'ACTIVE', 0, 0, :now, :now)"
            ),
            {
                "id": admin_id,
                "email": f"onboard-admin-{uuid4().hex[:8]}@harbor.example",
                "hash": hash_password("AdminPass!1234"),
                "now": datetime.now(UTC),
            },
        )
        db.commit()

        # Create a plan with branches limit = 3
        plan_id = uuid4()
        plan_code = f"onboard-plan-{uuid4().hex[:6]}"
        version_id = uuid4()
        now = datetime.now(UTC)
        db.execute(
            _text(
                "INSERT INTO platform_plans (id, code, name, description, "
                "price_monthly_minor, price_annual_minor, currency_code, "
                "trial_days, status, is_public, sort_order, created_at, updated_at) "
                "VALUES (:id, :code, 'Onboarding Plan', 'Test', 299900, 2999000, "
                "'NPR', 14, 'ACTIVE', true, 1, :now, :now)"
            ),
            {"id": plan_id, "code": plan_code, "now": now},
        )
        db.execute(
            _text(
                "INSERT INTO platform_plan_versions (id, plan_id, version, "
                "effective_from, price_monthly_minor, price_annual_minor, "
                "currency_code, trial_days, is_active, created_at, updated_at) "
                "VALUES (:id, :pid, 1, :now, 299900, 2999000, 'NPR', 14, true, "
                ":now, :now)"
            ),
            {"id": version_id, "pid": plan_id, "now": now},
        )
        db.execute(
            _text(
                "INSERT INTO platform_plan_limits "
                "(id, plan_version_id, limit_key, limit_value, created_at) "
                "VALUES (:id, :vid, 'branches', 3, :now)"
            ),
            {"id": uuid4(), "vid": version_id, "now": now},
        )
        db.execute(
            _text(
                "INSERT INTO platform_plan_limits "
                "(id, plan_version_id, limit_key, limit_value, created_at) "
                "VALUES (:id, :vid, 'waiters', 15, :now)"
            ),
            {"id": uuid4(), "vid": version_id, "now": now},
        )
        db.execute(
            _text(
                "INSERT INTO platform_plan_features "
                "(id, plan_version_id, feature_key, enabled, created_at) "
                "VALUES (:id, :vid, 'qr_ordering', true, :now)"
            ),
            {"id": uuid4(), "vid": version_id, "now": now},
        )
        db.commit()

        client = TestClient(app)
        headers = _platform_auth_headers(client, admin_id)

        yield {
            "client": client,
            "headers": headers,
            "plan_code": plan_code,
        }
    finally:
        _cleanup(db, "maison-")
        db.close()


class TestOnboardingSuccess:
    def test_onboard_complete_restaurant(self, env):
        client, headers = env["client"], env["headers"]
        slug = f"maison-{uuid4().hex[:6]}"
        owner_email = f"onboard-owner-{uuid4().hex[:8]}@example.com"
        response = client.post(
            "/api/platform/onboarding/restaurants",
            json={
                "restaurant": {
                    "name": "MAISON Restaurant",
                    "legal_name": "MAISON Pvt. Ltd.",
                    "slug": slug,
                    "contact_email": "contact@maison.example",
                    "contact_phone": "+977-1-1234567",
                    "country": "NP",
                    "province": "Bagmati",
                    "district": "Kathmandu",
                    "address": "Thamel, Kathmandu",
                    "timezone": "Asia/Kathmandu",
                    "currency_code": "NPR",
                },
                "owner": {
                    "full_name": "Restaurant Owner",
                    "email": owner_email,
                    "phone": "+977-98-1234567",
                },
                "subscription": {
                    "plan_code": env["plan_code"],
                    "trial_days": 14,
                    "billing_interval": "MONTHLY",
                },
                "branches": [
                    {
                        "name": "MAISON Kathmandu",
                        "code": "KTM-01",
                        "address": "Thamel, Kathmandu",
                        "phone": "+977-1-4444444",
                        "opening_hours": "09:00-22:00",
                        "timezone": "Asia/Kathmandu",
                    },
                    {
                        "name": "MAISON Pokhara",
                        "code": "PKR-01",
                        "address": "Lakeside, Pokhara",
                        "phone": "+977-61-555555",
                        "opening_hours": "10:00-21:00",
                        "timezone": "Asia/Kathmandu",
                    },
                ],
                "reason": "New customer onboarding",
                "confirm": slug,
            },
            headers=headers,
        )
        assert response.status_code == 201, response.text
        data = response.json()
        assert data["tenant_id"]
        assert data["restaurant"]["name"] == "MAISON Restaurant"
        assert data["restaurant"]["slug"] == slug
        assert data["restaurant"]["status"] == "ACTIVE"
        assert data["subscription"]["plan_code"] == env["plan_code"]
        assert data["subscription"]["status"] == "TRIALING"
        assert len(data["branches"]) == 2
        assert data["owner_invitation"]["sent"] is True
        assert data["owner_invitation"]["email"] == owner_email
        assert data["owner_invitation"]["expires_at"]

    def test_branch_limit_enforced(self, env):
        client, headers = env["client"], env["headers"]
        slug = f"maison-limit-{uuid4().hex[:6]}"
        owner_email = f"onboard-owner-{uuid4().hex[:8]}@example.com"

        # Plan allows 3 branches; request 4
        branches = [
            {
                "name": f"MAISON Branch {i}",
                "code": f"BR{i:02d}-{uuid4().hex[:4].upper()}",
                "address": f"Address {i}",
                "timezone": "Asia/Kathmandu",
            }
            for i in range(4)
        ]
        response = client.post(
            "/api/platform/onboarding/restaurants",
            json={
                "restaurant": {
                    "name": "Limit Test Restaurant",
                    "slug": slug,
                    "contact_email": "contact@limit.example",
                    "contact_phone": "+977-1-0000000",
                    "country": "NP",
                    "district": "Kathmandu",
                    "address": "Test Address",
                    "timezone": "Asia/Kathmandu",
                    "currency_code": "NPR",
                },
                "owner": {
                    "full_name": "Owner",
                    "email": owner_email,
                },
                "subscription": {
                    "plan_code": env["plan_code"],
                    "trial_days": 14,
                    "billing_interval": "MONTHLY",
                },
                "branches": branches,
                "reason": "Branch limit test",
                "confirm": slug,
            },
            headers=headers,
        )
        assert response.status_code == 409, response.text
        assert response.json()["code"] == "SEAT_LIMIT_REACHED"

    def test_confirmation_must_match_slug(self, env):
        client, headers = env["client"], env["headers"]
        slug = f"maison-confirm-{uuid4().hex[:6]}"
        response = client.post(
            "/api/platform/onboarding/restaurants",
            json={
                "restaurant": {
                    "name": "Confirm Test",
                    "slug": slug,
                    "contact_email": "contact@confirm.example",
                    "contact_phone": "+977-1-0000000",
                    "country": "NP",
                    "district": "Kathmandu",
                    "address": "Test Address",
                    "timezone": "Asia/Kathmandu",
                    "currency_code": "NPR",
                },
                "owner": {
                    "full_name": "Owner",
                    "email": f"onboard-owner-{uuid4().hex[:8]}@example.com",
                },
                "subscription": {
                    "plan_code": env["plan_code"],
                    "trial_days": 14,
                    "billing_interval": "MONTHLY",
                },
                "branches": [
                    {
                        "name": "Branch 1",
                        "code": f"B1-{uuid4().hex[:4].upper()}",
                        "timezone": "Asia/Kathmandu",
                    }
                ],
                "reason": "Confirmation test",
                "confirm": "wrong-slug",
            },
            headers=headers,
        )
        assert response.status_code == 422, response.text
        assert response.json()["code"] == "CONFIRMATION_MISMATCH"

    def test_duplicate_slug_rejected(self, env):
        client, headers = env["client"], env["headers"]
        slug = f"maison-dup-{uuid4().hex[:6]}"
        owner_email = f"onboard-owner-{uuid4().hex[:8]}@example.com"

        # First creation
        response = client.post(
            "/api/platform/onboarding/restaurants",
            json={
                "restaurant": {
                    "name": "Dup Test",
                    "slug": slug,
                    "contact_email": "contact@dup.example",
                    "contact_phone": "+977-1-0000000",
                    "country": "NP",
                    "district": "Kathmandu",
                    "address": "Test Address",
                    "timezone": "Asia/Kathmandu",
                    "currency_code": "NPR",
                },
                "owner": {
                    "full_name": "Owner",
                    "email": owner_email,
                },
                "subscription": {
                    "plan_code": env["plan_code"],
                    "trial_days": 14,
                    "billing_interval": "MONTHLY",
                },
                "branches": [
                    {
                        "name": "Branch 1",
                        "code": f"B1-{uuid4().hex[:4].upper()}",
                        "timezone": "Asia/Kathmandu",
                    }
                ],
                "reason": "Dup test 1",
                "confirm": slug,
            },
            headers=headers,
        )
        assert response.status_code == 201, response.text

        # Second creation with same slug
        response = client.post(
            "/api/platform/onboarding/restaurants",
            json={
                "restaurant": {
                    "name": "Dup Test 2",
                    "slug": slug,
                    "contact_email": "contact@dup2.example",
                    "contact_phone": "+977-1-0000000",
                    "country": "NP",
                    "district": "Kathmandu",
                    "address": "Test Address 2",
                    "timezone": "Asia/Kathmandu",
                    "currency_code": "NPR",
                },
                "owner": {
                    "full_name": "Owner 2",
                    "email": f"onboard-owner-{uuid4().hex[:8]}@example.com",
                },
                "subscription": {
                    "plan_code": env["plan_code"],
                    "trial_days": 14,
                    "billing_interval": "MONTHLY",
                },
                "branches": [
                    {
                        "name": "Branch 1",
                        "code": f"B1-{uuid4().hex[:4].upper()}",
                        "timezone": "Asia/Kathmandu",
                    }
                ],
                "reason": "Dup test 2",
                "confirm": slug,
            },
            headers=headers,
        )
        assert response.status_code == 409, response.text
        assert response.json()["code"] == "SLUG_TAKEN"
