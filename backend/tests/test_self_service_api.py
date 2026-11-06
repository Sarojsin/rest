"""Integration tests for PA-04 Self-Service Registration.

Tests the public API endpoints for restaurant owner self-registration:
- GET /api/platform/public/plans - List available plans (no auth)
- POST /api/platform/public/register - Register a restaurant (no auth)
- GET /api/platform/self-service/registrations - List registrations (auth required)
- POST /api/platform/self-service/registrations/{id}/approve - Approve registration (auth required)
- POST /api/platform/self-service/registrations/{id}/reject - Reject registration (auth required)
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import jwt
import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.main import app
from app.modules.platform.models import PlatformAdmin, PlatformPlan
from app.core.security import hash_password

CSRF_TOKEN = "test-csrf-token-12345"


@pytest.fixture(scope="module")
def client() -> TestClient:
    """Create a test client with the database migrated."""
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        from sqlalchemy import text as _text

        # Idempotent setup: clear any leftovers from a prior interrupted run.
        # Order matters because several tables reference restaurants/plans.
        db.execute(
            _text("DELETE FROM self_service_registrations WHERE owner_email LIKE '%@example.com'")
        )
        db.execute(
            _text(
                "DELETE FROM platform_subscriptions WHERE plan_id IN "
                "(SELECT id FROM platform_plans WHERE code IN "
                "('starter','professional','enterprise'))"
            )
        )
        db.execute(
            _text(
                "DELETE FROM platform_one_time_tokens WHERE restaurant_id IN "
                "(SELECT id FROM restaurants WHERE slug IN "
                "('my-test-restaurant','dup-test','list-test','approve-test',"
                "'reject-test','get-test','invalid-plan','dup-email-1','dup-email-2'))"
            )
        )
        db.execute(
            _text(
                "DELETE FROM restaurant_settings WHERE restaurant_id IN "
                "(SELECT id FROM restaurants WHERE slug IN "
                "('my-test-restaurant','dup-test','list-test','approve-test',"
                "'reject-test','get-test','invalid-plan','dup-email-1','dup-email-2'))"
            )
        )
        db.execute(
            _text(
                "DELETE FROM restaurant_memberships WHERE restaurant_id IN "
                "(SELECT id FROM restaurants WHERE slug IN "
                "('my-test-restaurant','dup-test','list-test','approve-test',"
                "'reject-test','get-test','invalid-plan','dup-email-1','dup-email-2'))"
            )
        )
        db.execute(
            _text(
                "DELETE FROM users WHERE email IN "
                "('owner@example.com','owner1@example.com','owner2@example.com',"
                "'dup@example.com','list@example.com','approve@example.com',"
                "'reject@example.com','get@example.com')"
            )
        )
        db.execute(
            _text(
                "DELETE FROM restaurants WHERE slug IN "
                "('my-test-restaurant','dup-test','list-test','approve-test',"
                "'reject-test','get-test','invalid-plan','dup-email-1','dup-email-2')"
            )
        )
        db.execute(
            _text("DELETE FROM platform_plans WHERE code IN ('starter','professional','enterprise')")
        )
        db.execute(
            _text("DELETE FROM platform_admins WHERE email = 'ss-test@harbor.example'")
        )
        db.commit()

        # Enable self-service registration for the test run.
        db.execute(
            _text(
                "INSERT INTO platform_settings (key, value_json, description, updated_at) "
                "VALUES ('platform.self_service_enabled', 'true', 'test', :now) "
                "ON CONFLICT (key) DO UPDATE SET value_json = 'true', updated_at = :now"
            ),
            {"now": datetime.now(UTC)},
        )
        db.execute(
            _text(
                "INSERT INTO platform_settings (key, value_json, description, updated_at) "
                "VALUES ('platform.self_service_tenant_creation', 'true', 'test', :now) "
                "ON CONFLICT (key) DO UPDATE SET value_json = 'true', updated_at = :now"
            ),
            {"now": datetime.now(UTC)},
        )
        db.commit()

        # Create a platform admin for auth
        admin = PlatformAdmin(
            email="ss-test@harbor.example",
            password_hash=hash_password("TestPass!123"),
            display_name="Self Service Test Admin",
            role="superadmin",
            status="ACTIVE",
            token_version=0,
        )
        db.add(admin)
        db.commit()
        db.refresh(admin)

        # Create some public plans (with active versions, as self-service
        # registration requires a published plan version).
        from app.modules.platform.models import PlatformPlanVersion

        for code, name, monthly, annual, trial_days in [
            ("starter", "Starter", 299900, 2999000, 14),
            ("professional", "Professional", 999900, 9999000, 30),
            ("enterprise", "Enterprise", 1999900, 19999000, 0),
        ]:
            plan = PlatformPlan(
                code=code,
                name=name,
                description=f"{name} plan",
                price_monthly_minor=monthly,
                price_annual_minor=annual,
                currency_code="NPR",
                trial_days=trial_days,
                status="ACTIVE",
                is_public=True,
                sort_order=1,
            )
            db.add(plan)
            db.flush()
            db.add(
                PlatformPlanVersion(
                    plan_id=plan.id,
                    version=1,
                    price_monthly_minor=monthly,
                    price_annual_minor=annual,
                    currency_code="NPR",
                    trial_days=trial_days,
                    is_active=True,
                )
            )
        db.commit()

        yield TestClient(app, headers={"Origin": "http://localhost:5173"}), admin
    finally:
        # Remove rows this fixture created, in FK-safe order.
        from sqlalchemy import text as _text

        _slugs = (
            "'my-test-restaurant','dup-test','list-test','approve-test',"
            "'reject-test','get-test','invalid-plan','dup-email-1','dup-email-2'"
        )
        db.execute(
            _text(
                "DELETE FROM self_service_registrations WHERE owner_email IN "
                "('owner@example.com','owner1@example.com','owner2@example.com',"
                "'dup@example.com','list@example.com','approve@example.com',"
                "'reject@example.com','get@example.com')"
            )
        )
        db.execute(
            _text(
                "DELETE FROM platform_subscriptions WHERE restaurant_id IN "
                f"(SELECT id FROM restaurants WHERE slug IN ({_slugs})) "
                "OR plan_id IN (SELECT id FROM platform_plans WHERE code IN "
                "('starter','professional','enterprise'))"
            )
        )
        db.execute(
            _text(
                "DELETE FROM platform_one_time_tokens WHERE restaurant_id IN "
                f"(SELECT id FROM restaurants WHERE slug IN ({_slugs}))"
            )
        )
        db.execute(
            _text(
                "DELETE FROM restaurant_settings WHERE restaurant_id IN "
                f"(SELECT id FROM restaurants WHERE slug IN ({_slugs}))"
            )
        )
        db.execute(
            _text(
                "DELETE FROM restaurant_memberships WHERE restaurant_id IN "
                f"(SELECT id FROM restaurants WHERE slug IN ({_slugs}))"
            )
        )
        db.execute(
            _text(
                "DELETE FROM users WHERE email IN "
                "('owner@example.com','owner1@example.com','owner2@example.com',"
                "'dup@example.com','list@example.com','approve@example.com',"
                "'reject@example.com','get@example.com')"
            )
        )
        db.execute(
            _text(f"DELETE FROM restaurants WHERE slug IN ({_slugs})")
        )
        db.execute(
            _text("DELETE FROM platform_plans WHERE code IN ('starter','professional','enterprise')")
        )
        db.execute(
            _text("DELETE FROM platform_admins WHERE email = 'ss-test@harbor.example'")
        )
        db.commit()
        db.close()


def _auth_headers(
    client: TestClient, admin_id: str, role: str = "superadmin"
) -> dict:
    """Set a signed platform access cookie and CSRF cookie/header.

    Platform login is MFA-gated and splits into a challenge flow, so tests
    mint a short-lived access JWT directly (same pattern as the plan-version
    integration tests) instead of driving the full TOTP enrollment.
    """
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


class TestPublicPlans:
    """Tests for public plans listing (no auth required)."""

    def test_list_plans(self, client: TestClient):
        """GET /api/platform/public/plans should return active public plans."""
        test_client, _ = client
        response = test_client.get("/api/platform/public/plans")
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert "items" in data
        assert len(data["items"]) >= 3
        # Check plan structure
        for plan in data["items"]:
            assert "code" in plan
            assert "name" in plan
            assert "price_monthly_minor" in plan
            assert "currency_code" in plan


class TestSelfServiceRegistration:
    """Tests for self-registration endpoint."""

    def test_register_tenant(self, client: TestClient):
        """POST /api/platform/public/register should create a tenant registration."""
        test_client, _ = client
        response = test_client.post(
            "/api/platform/public/register",
            json={
                "restaurant_name": "My Test Restaurant",
                "restaurant_slug": "my-test-restaurant",
                "owner_email": "owner@example.com",
                "owner_name": "John Owner",
                "owner_phone": "+1 555-000-0000",
                "plan_code": "starter",
                "trial_days": 14,
                "contact_email": "contact@example.com",
                "contact_phone": "+1 555-000-0001",
                "legal_name": "My Test Restaurant LLC",
                "timezone": "Asia/Kathmandu",
                "currency_code": "NPR",
                "source": "self_service",
                "reason": "Self-service registration",
            },
        )
        assert response.status_code == 201, f"Registration failed: {response.text}"
        data = response.json()
        assert data["status"] in ("PENDING", "APPROVED")
        assert data["owner_email"] == "owner@example.com"
        assert "id" in data

    def test_register_duplicate_slug(self, client: TestClient):
        """Registering with same slug should fail."""
        test_client, _ = client
        # First registration
        test_client.post(
            "/api/platform/public/register",
            json={
                "restaurant_name": "Test Restaurant",
                "restaurant_slug": "dup-test",
                "owner_email": "owner1@example.com",
                "owner_name": "Owner One",
                "plan_code": "starter",
                "trial_days": 14,
                "reason": "Self-service registration",
            },
        )
        # Second registration with same slug
        response = test_client.post(
            "/api/platform/public/register",
            json={
                "restaurant_name": "Test Restaurant 2",
                "restaurant_slug": "dup-test",
                "owner_email": "owner2@example.com",
                "owner_name": "Owner Two",
                "plan_code": "starter",
                "trial_days": 14,
                "reason": "Self-service registration",
            },
        )
        assert response.status_code == 409, f"Expected 409: {response.text}"
        data = response.json()
        assert data["code"] == "APPLICATION_EXISTS"

    def test_register_duplicate_email(self, client: TestClient):
        """Registering with same owner email should fail."""
        test_client, _ = client
        # First registration
        test_client.post(
            "/api/platform/public/register",
            json={
                "restaurant_name": "Test Restaurant",
                "restaurant_slug": "dup-email-1",
                "owner_email": "dup@example.com",
                "owner_name": "Owner One",
                "plan_code": "starter",
                "trial_days": 14,
                "reason": "Self-service registration",
            },
        )
        # Second registration with same email
        response = test_client.post(
            "/api/platform/public/register",
            json={
                "restaurant_name": "Test Restaurant 2",
                "restaurant_slug": "dup-email-2",
                "owner_email": "dup@example.com",
                "owner_name": "Owner Two",
                "plan_code": "starter",
                "trial_days": 14,
                "reason": "Self-service registration",
            },
        )
        assert response.status_code == 409, f"Expected 409: {response.text}"
        data = response.json()
        assert data["code"] == "OWNER_EMAIL_EXISTS"

    def test_register_invalid_plan(self, client: TestClient):
        """Registering with invalid plan code should fail."""
        test_client, _ = client
        response = test_client.post(
            "/api/platform/public/register",
            json={
                "restaurant_name": "Test Restaurant",
                "restaurant_slug": "invalid-plan",
                "owner_email": "owner@example.com",
                "owner_name": "Owner",
                "plan_code": "nonexistent_plan",
                "trial_days": 14,
                "reason": "Self-service registration",
            },
        )
        assert response.status_code == 404, f"Expected 404: {response.text}"
        data = response.json()
        assert data["code"] == "PLAN_NOT_FOUND"


class TestSelfServiceAdmin:
    """Tests for admin management of self-service registrations."""

    def test_list_registrations(self, client: TestClient):
        """GET /api/platform/self-service/registrations should list registrations."""
        test_client, admin = client
        headers = _auth_headers(test_client, str(admin.id))

        # Create a registration first
        test_client.post(
            "/api/platform/public/register",
            json={
                "restaurant_name": "List Test Restaurant",
                "restaurant_slug": "list-test",
                "owner_email": "list@example.com",
                "owner_name": "List Owner",
                "plan_code": "starter",
                "trial_days": 14,
                "reason": "Self-service registration",
            },
        )

        response = test_client.get(
            "/api/platform/self-service/registrations", headers=headers
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert "items" in data
        assert len(data["items"]) >= 1
        assert data["items"][0]["restaurant_slug"] == "list-test"

    def test_approve_registration(self, client: TestClient):
        """POST /api/platform/self-service/registrations/{id}/approve should approve."""
        test_client, admin = client
        headers = _auth_headers(test_client, str(admin.id))

        # Create a registration first
        reg_resp = test_client.post(
            "/api/platform/public/register",
            json={
                "restaurant_name": "Approve Test",
                "restaurant_slug": "approve-test",
                "owner_email": "approve@example.com",
                "owner_name": "Approve Owner",
                "plan_code": "starter",
                "trial_days": 14,
                "reason": "Self-service registration",
            },
        )
        reg_id = reg_resp.json()["id"]

        # Approve
        response = test_client.post(
            f"/api/platform/self-service/registrations/{reg_id}/approve",
            json={"reason": "Approved for testing", "confirm": "approve-test"},
            headers=headers,
        )
        assert response.status_code == 200, f"Approve failed: {response.text}"
        data = response.json()
        assert data["status"] == "APPROVED"
        assert data["restaurant_id"] is not None
        assert data["invitation_token"] is not None

    def test_reject_registration(self, client: TestClient):
        """POST /api/platform/self-service/registrations/{id}/reject should reject."""
        test_client, admin = client
        headers = _auth_headers(test_client, str(admin.id))

        # Create a registration first
        reg_resp = test_client.post(
            "/api/platform/public/register",
            json={
                "restaurant_name": "Reject Test",
                "restaurant_slug": "reject-test",
                "owner_email": "reject@example.com",
                "owner_name": "Reject Owner",
                "plan_code": "starter",
                "trial_days": 14,
                "reason": "Self-service registration",
            },
        )
        reg_id = reg_resp.json()["id"]

        # Reject
        response = test_client.post(
            f"/api/platform/self-service/registrations/{reg_id}/reject",
            json={"reason": "Incomplete information", "confirm": "reject-test"},
            headers=headers,
        )
        assert response.status_code == 200, f"Reject failed: {response.text}"
        data = response.json()
        assert data["status"] == "REJECTED"

    def test_get_registration(self, client: TestClient):
        """GET /api/platform/self-service/registrations/{id} should return registration."""
        test_client, admin = client
        headers = _auth_headers(test_client, str(admin.id))

        # Create a registration first
        reg_resp = test_client.post(
            "/api/platform/public/register",
            json={
                "restaurant_name": "Get Test",
                "restaurant_slug": "get-test",
                "owner_email": "get@example.com",
                "owner_name": "Get Owner",
                "plan_code": "starter",
                "trial_days": 14,
                "reason": "Self-service registration",
            },
        )
        reg_id = reg_resp.json()["id"]

        # Get registration
        response = test_client.get(
            f"/api/platform/self-service/registrations/{reg_id}", headers=headers
        )
        assert response.status_code == 200, f"Get failed: {response.text}"
        data = response.json()
        assert data["id"] == reg_id
        assert data["restaurant_slug"] == "get-test"
        assert data["owner_email"] == "get@example.com"

    def test_get_nonexistent_registration(self, client: TestClient):
        """GET /api/platform/self-service/registrations/{id} with nonexistent ID should return 404."""
        test_client, admin = client
        headers = _auth_headers(test_client, str(admin.id))

        response = test_client.get(
            f"/api/platform/self-service/registrations/{uuid4()}", headers=headers
        )
        assert response.status_code == 404, f"Expected 404: {response.text}"
        data = response.json()
        assert data["code"] == "REGISTRATION_NOT_FOUND"

    def test_approve_nonexistent_registration(self, client: TestClient):
        """POST /api/platform/self-service/registrations/{id}/approve with nonexistent ID should return 404."""
        test_client, admin = client
        headers = _auth_headers(test_client, str(admin.id))

        response = test_client.post(
            f"/api/platform/self-service/registrations/{uuid4()}/approve",
            json={"reason": "Approve", "confirm": "nonexistent"},
            headers=headers,
        )
        assert response.status_code == 404, f"Expected 404: {response.text}"
        data = response.json()
        assert data["code"] == "REGISTRATION_NOT_FOUND"

    def test_reject_nonexistent_registration(self, client: TestClient):
        """POST /api/platform/self-service/registrations/{id}/reject with nonexistent ID should return 404."""
        test_client, admin = client
        headers = _auth_headers(test_client, str(admin.id))

        response = test_client.post(
            f"/api/platform/self-service/registrations/{uuid4()}/reject",
            json={"reason": "Reject", "confirm": "nonexistent"},
            headers=headers,
        )
        assert response.status_code == 404, f"Expected 404: {response.text}"
        data = response.json()
        assert data["code"] == "REGISTRATION_NOT_FOUND"
