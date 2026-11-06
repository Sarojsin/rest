"""Integration tests for plan version API endpoints (Plan 01).

Tests the full HTTP stack for plan version management:
- POST /api/platform/plans/{plan_id}/versions
- GET /api/platform/plans/{plan_id}/versions
- POST /api/platform/plans/versions/{version_id}/publish
- POST /api/platform/plans/versions/{version_id}/features
- POST /api/platform/plans/versions/{version_id}/limits
- GET /api/platform/plans/{plan_id}/entitlements

Platform API uses HttpOnly cookies for auth (platform_access) + CSRF protection
(platform_csrf cookie + X-CSRF-Token header). In tests, we create a valid JWT
and set it as the platform_access cookie, plus set the CSRF cookie and header.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import jwt
import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.core.security import hash_password
from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.main import app
from app.modules.platform.models import PlatformAdmin, PlatformPlan

CSRF_TOKEN = "test-csrf-token-12345"


@pytest.fixture(scope="function")
def client() -> TestClient:
    """Create a test client with the database migrated."""
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        # Create a platform admin for auth
        admin = PlatformAdmin(
            email=f"plan-test-{uuid4().hex[:8]}@harbor.example",
            password_hash=hash_password("TestPass!123"),
            display_name="Plan Test Admin",
            role="superadmin",
            status="ACTIVE",
            token_version=0,
        )
        db.add(admin)
        db.commit()
        db.refresh(admin)

        # Create a test plan with unique code
        plan = PlatformPlan(
            code=f"test_plan_{uuid4().hex[:8]}",
            name="Test Plan",
            description="Integration test plan",
            price_monthly_minor=299900,
            price_annual_minor=2999000,
            currency_code="NPR",
            trial_days=14,
            status="ACTIVE",
            is_public=True,
            sort_order=1,
        )
        db.add(plan)
        db.commit()
        db.refresh(plan)

        yield TestClient(app), admin, plan
    finally:
        # Targeted cleanup instead of drop_all: the shared dev DB is migrated
        # via Alembic and other tests/objects depend on these tables. Remove
        # this fixture's rows in FK-safe order.
        from sqlalchemy import text as _text

        db.execute(
            _text(
                "DELETE FROM platform_plan_features WHERE plan_version_id IN "
                "(SELECT id FROM platform_plan_versions WHERE plan_id = :pid)"
            ),
            {"pid": plan.id},
        )
        db.execute(
            _text(
                "DELETE FROM platform_plan_limits WHERE plan_version_id IN "
                "(SELECT id FROM platform_plan_versions WHERE plan_id = :pid)"
            ),
            {"pid": plan.id},
        )
        db.execute(
            _text("DELETE FROM platform_plan_versions WHERE plan_id = :pid"),
            {"pid": plan.id},
        )
        db.execute(_text("DELETE FROM platform_plans WHERE id = :pid"), {"pid": plan.id})
        db.execute(
            _text("DELETE FROM platform_admins WHERE id = :aid"), {"aid": admin.id}
        )
        db.commit()
        db.close()


def _auth_headers(
    client: TestClient, admin_id: str, role: str = "superadmin"
) -> dict:
    """Set platform_access cookie (JWT) and CSRF cookie/header for auth."""
    now = datetime.now(UTC)
    token = jwt.encode(
        {
            "sub": str(admin_id),
            "realm": "platform",
            "role": role,
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
    return {"Origin": "http://localhost:5173", "X-CSRF-Token": CSRF_TOKEN}


class TestPlanVersionAPI:
    """Integration tests for plan version API."""

    def test_create_plan_version(self, client: TestClient):
        """POST /api/platform/plans/{plan_id}/versions should create a draft version."""
        test_client, admin, plan = client
        headers = _auth_headers(test_client, str(admin.id))

        response = test_client.post(
            f"/api/platform/plans/{plan.id}/versions",
            json={
                "price_monthly_minor": 350000,
                "price_annual_minor": 3500000,
                "currency_code": "NPR",
                "trial_days": 30,
                "reason": "Test version creation",
            },
            headers=headers,
        )
        assert response.status_code == 201, f"Create version failed: {response.text}"
        data = response.json()
        assert data["version"] == 1
        assert data["is_active"] is False  # Draft by default
        assert data["price_monthly_minor"] == 350000
        assert data["trial_days"] == 30
        assert "id" in data

    def test_list_plan_versions(self, client: TestClient):
        """GET /api/platform/plans/{plan_id}/versions should list all versions."""
        test_client, admin, plan = client
        headers = _auth_headers(test_client, str(admin.id))

        # Create two versions
        test_client.post(
            f"/api/platform/plans/{plan.id}/versions",
            json={
                "price_monthly_minor": 300000,
                "price_annual_minor": 3000000,
                "currency_code": "NPR",
                "trial_days": 30,
                "reason": "V1",
            },
            headers=headers,
        )
        test_client.post(
            f"/api/platform/plans/{plan.id}/versions",
            json={
                "price_monthly_minor": 350000,
                "price_annual_minor": 3500000,
                "currency_code": "NPR",
                "trial_days": 30,
                "reason": "V2",
            },
            headers=headers,
        )

        response = test_client.get(
            f"/api/platform/plans/{plan.id}/versions", headers=headers
        )
        assert response.status_code == 200, f"List versions failed: {response.text}"
        data = response.json()
        assert len(data["items"]) == 2
        assert data["items"][0]["version"] == 1
        assert data["items"][1]["version"] == 2

    def test_publish_plan_version(self, client: TestClient):
        """POST /api/platform/plans/versions/{version_id}/publish should activate version."""
        test_client, admin, plan = client
        headers = _auth_headers(test_client, str(admin.id))

        # Create a version
        create_resp = test_client.post(
            f"/api/platform/plans/{plan.id}/versions",
            json={
                "price_monthly_minor": 300000,
                "price_annual_minor": 3000000,
                "currency_code": "NPR",
                "trial_days": 30,
                "reason": "V1",
            },
            headers=headers,
        )
        version_id = create_resp.json()["id"]

        # Publish it
        publish_resp = test_client.post(
            f"/api/platform/plans/versions/{version_id}/publish",
            json={"reason": "Publish V1"},
            headers=headers,
        )
        assert publish_resp.status_code == 200, f"Publish failed: {publish_resp.text}"
        data = publish_resp.json()
        assert data["is_active"] is True

    def test_add_feature_to_version(self, client: TestClient):
        """POST /api/platform/plans/versions/{version_id}/features should add a feature."""
        test_client, admin, plan = client
        headers = _auth_headers(test_client, str(admin.id))

        # Create a draft version
        create_resp = test_client.post(
            f"/api/platform/plans/{plan.id}/versions",
            json={
                "price_monthly_minor": 300000,
                "price_annual_minor": 3000000,
                "currency_code": "NPR",
                "trial_days": 30,
                "reason": "V1",
            },
            headers=headers,
        )
        version_id = create_resp.json()["id"]

        # Add a feature
        feature_resp = test_client.post(
            f"/api/platform/plans/versions/{version_id}/features",
            json={
                "feature_key": "qr_ordering",
                "enabled": True,
                "reason": "Add QR ordering",
            },
            headers=headers,
        )
        assert feature_resp.status_code == 201, f"Add feature failed: {feature_resp.text}"
        data = feature_resp.json()
        assert data["feature_key"] == "qr_ordering"
        assert data["enabled"] is True

    def test_add_limit_to_version(self, client: TestClient):
        """POST /api/platform/plans/versions/{version_id}/limits should add a limit."""
        test_client, admin, plan = client
        headers = _auth_headers(test_client, str(admin.id))

        # Create a draft version
        create_resp = test_client.post(
            f"/api/platform/plans/{plan.id}/versions",
            json={
                "price_monthly_minor": 300000,
                "price_annual_minor": 3000000,
                "currency_code": "NPR",
                "trial_days": 30,
                "reason": "V1",
            },
            headers=headers,
        )
        version_id = create_resp.json()["id"]

        # Add a limit
        limit_resp = test_client.post(
            f"/api/platform/plans/versions/{version_id}/limits",
            json={
                "limit_key": "branches",
                "limit_value": 3,
                "reason": "Add branch limit",
            },
            headers=headers,
        )
        assert limit_resp.status_code == 201, f"Add limit failed: {limit_resp.text}"
        data = limit_resp.json()
        assert data["limit_key"] == "branches"
        assert data["limit_value"] == 3

    def test_get_plan_entitlements(self, client: TestClient):
        """GET /api/platform/plans/{plan_id}/entitlements should return active version entitlements."""
        test_client, admin, plan = client
        headers = _auth_headers(test_client, str(admin.id))

        # No active version yet
        resp = test_client.get(f"/api/platform/plans/{plan.id}/entitlements", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["active_version"] is None
        assert data["features"] == {}
        assert data["limits"] == {}

        # Create and publish a version with features/limits
        create_resp = test_client.post(
            f"/api/platform/plans/{plan.id}/versions",
            json={
                "price_monthly_minor": 300000,
                "price_annual_minor": 3000000,
                "currency_code": "NPR",
                "trial_days": 30,
                "reason": "V1",
            },
            headers=headers,
        )
        version_id = create_resp.json()["id"]

        test_client.post(
            f"/api/platform/plans/versions/{version_id}/features",
            json={"feature_key": "qr_ordering", "enabled": True, "reason": "Add feature"},
            headers=headers,
        )
        test_client.post(
            f"/api/platform/plans/versions/{version_id}/limits",
            json={"limit_key": "branches", "limit_value": 3, "reason": "Add limit"},
            headers=headers,
        )
        test_client.post(
            f"/api/platform/plans/versions/{version_id}/publish",
            json={"reason": "Publish"},
            headers=headers,
        )

        # Get entitlements
        resp = test_client.get(f"/api/platform/plans/{plan.id}/entitlements", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["active_version"] is not None
        assert data["active_version"]["version"] == 1
        assert data["features"] == {"qr_ordering": True}
        assert data["limits"] == {"branches": 3}
