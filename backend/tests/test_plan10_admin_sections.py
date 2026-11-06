"""Integration tests for Plan 10 — Admin Console missing navigation sections.

Tests:
- Support ticket CRUD (GET/POST/PATCH /api/platform/support/tickets)
- Onboarding status list (GET /api/platform/onboarding)
- Onboarding stage update (PATCH /api/platform/onboarding/{id}/stage)
- Analytics summary (GET /api/platform/analytics/summary)
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

CSRF_TOKEN = "test-csrf-token-12345"


def _platform_auth_headers(client: TestClient, admin_id, role: str = "superadmin") -> dict:
    """Mint a platform access JWT (same pattern as plan version tests)."""
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
    return {
        "Origin": "http://localhost:5173",
        "X-CSRF-Token": CSRF_TOKEN,
    }


def _create_platform_admin(db, admin_id, role="superadmin"):
    """Create a platform admin for auth."""
    db.execute(
        _text(
            "INSERT INTO platform_admins (id, email, password_hash, display_name, "
            "role, status, token_version, failed_login_count, created_at, updated_at) "
            "VALUES (:id, :email, :hash, 'Test Admin', :role, 'ACTIVE', 0, 0, :now, :now)"
        ),
        {
            "id": admin_id,
            "email": f"plan10-admin-{uuid4().hex[:8]}@harbor.example",
            "hash": hash_password("AdminPass!1234"),
            "role": role,
            "now": datetime.now(UTC),
        },
    )
    db.commit()


def _create_restaurant(db, slug):
    """Create a restaurant for testing."""
    restaurant_id = uuid4()
    now = datetime.now(UTC)
    db.execute(
        _text(
            "INSERT INTO restaurants (id, name, slug, status, timezone, currency_code, "
            "created_at, updated_at) "
            "VALUES (:id, :name, :slug, 'ACTIVE', 'Asia/Kathmandu', 'NPR', :now, :now)"
        ),
        {"id": restaurant_id, "name": f"Plan10 Test {slug}", "slug": slug, "now": now},
    )
    db.execute(
        _text(
            "INSERT INTO restaurant_settings "
            "(restaurant_id, locale, business_day_start_local, tax_rate_bps, "
            "receipt_header, receipt_footer, qr_ordering_enabled, "
            "online_payments_enabled, settings_version, customer_subdomain, "
            "brand_logo_url, brand_accent_hex, created_at, updated_at, "
            "onboarding_stage, onboarding_completed_at) "
            "VALUES (:rid, 'en-NP', '05:00', 1300, 'Test', 'Thank you', true, "
            "false, 1, :slug, '', '', :now, :now, 'registered', NULL)"
        ),
        {"rid": restaurant_id, "slug": slug, "now": now},
    )
    db.commit()
    return restaurant_id


def _cleanup(db, slug_prefix):
    like = f"{slug_prefix}%"
    db.execute(
        _text("DELETE FROM platform_support_tickets WHERE restaurant_id IN "
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
    db.execute(
        _text("DELETE FROM platform_admins WHERE email LIKE :email"),
        {"email": "plan10-admin-%@harbor.example"},
    )
    db.commit()


@pytest.fixture(scope="function")
def env():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        admin_id = uuid4()
        _create_platform_admin(db, admin_id)
        client = TestClient(app)
        headers = _platform_auth_headers(client, admin_id)

        # Create a test restaurant
        slug = f"plan10-rest-{uuid4().hex[:6]}"
        restaurant_id = _create_restaurant(db, slug)

        yield {
            "client": client,
            "headers": headers,
            "restaurant_id": str(restaurant_id),
            "slug": slug,
        }
    finally:
        _cleanup(db, "plan10-rest-")
        db.close()


class TestSupportTickets:
    def test_create_and_list_ticket(self, env):
        client, headers = env["client"], env["headers"]
        rid = env["restaurant_id"]

        # Create ticket
        response = client.post(
            "/api/platform/support/tickets",
            json={
                "restaurant_id": rid,
                "subject": "Cannot log in",
                "description": "Owner cannot access dashboard",
                "priority": "high",
            },
            headers=headers,
        )
        assert response.status_code == 201, response.text
        data = response.json()
        assert data["subject"] == "Cannot log in"
        assert data["status"] == "open"
        assert data["priority"] == "high"
        ticket_id = data["id"]

        # List tickets
        response = client.get("/api/platform/support/tickets", headers=headers)
        assert response.status_code == 200, response.text
        data = response.json()
        assert data["total"] >= 1
        assert any(t["id"] == ticket_id for t in data["items"])

    def test_update_ticket(self, env):
        client, headers = env["client"], env["headers"]
        rid = env["restaurant_id"]

        # Create ticket
        response = client.post(
            "/api/platform/support/tickets",
            json={
                "restaurant_id": rid,
                "subject": "Billing question",
                "priority": "low",
            },
            headers=headers,
        )
        assert response.status_code == 201, response.text
        ticket_id = response.json()["id"]

        # Update ticket
        response = client.patch(
            f"/api/platform/support/tickets/{ticket_id}",
            json={"status": "resolved", "priority": "medium"},
            headers=headers,
        )
        assert response.status_code == 200, response.text
        data = response.json()
        assert data["status"] == "resolved"
        assert data["priority"] == "medium"
        assert data["resolved_at"] is not None

    def test_filter_tickets_by_status(self, env):
        client, headers = env["client"], env["headers"]
        rid = env["restaurant_id"]

        # Create an open ticket
        client.post(
            "/api/platform/support/tickets",
            json={"restaurant_id": rid, "subject": "Open ticket", "priority": "low"},
            headers=headers,
        )

        # Filter by open
        response = client.get(
            "/api/platform/support/tickets?status=open", headers=headers
        )
        assert response.status_code == 200, response.text
        data = response.json()
        assert all(t["status"] == "open" for t in data["items"])


class TestOnboardingStatus:
    def test_list_onboarding_status(self, env):
        client, headers = env["client"], env["headers"]

        response = client.get("/api/platform/onboarding", headers=headers)
        assert response.status_code == 200, response.text
        data = response.json()
        assert data["total"] >= 1
        # Find our test restaurant
        found = any(t["slug"] == env["slug"] for t in data["items"])
        assert found, f"Test restaurant {env['slug']} not found in onboarding list"
        item = next(t for t in data["items"] if t["slug"] == env["slug"])
        assert item["onboarding_stage"] == "registered"
        assert item["tenant_id"] == env["restaurant_id"]

    def test_update_onboarding_stage(self, env):
        client, headers = env["client"], env["headers"]
        rid = env["restaurant_id"]

        response = client.patch(
            f"/api/platform/onboarding/{rid}/stage",
            json={"stage": "owner_activated", "reason": "Owner completed setup"},
            headers=headers,
        )
        assert response.status_code == 200, response.text
        data = response.json()
        assert data["onboarding_stage"] == "owner_activated"

    def test_update_invalid_stage(self, env):
        client, headers = env["client"], env["headers"]
        rid = env["restaurant_id"]

        response = client.patch(
            f"/api/platform/onboarding/{rid}/stage",
            json={"stage": "invalid_stage"},
            headers=headers,
        )
        assert response.status_code == 422, response.text
        assert response.json()["code"] == "INVALID_STAGE"


class TestAnalyticsSummary:
    def test_analytics_summary(self, env):
        client, headers = env["client"], env["headers"]

        response = client.get("/api/platform/analytics/summary", headers=headers)
        assert response.status_code == 200, response.text
        data = response.json()
        assert "total_restaurants" in data
        assert "new_restaurants_30d" in data
        assert "total_branches" in data
        assert "total_staff" in data
        assert "restaurants_by_status" in data
        assert "subscriptions_by_status" in data
        assert "tickets_by_status" in data
        assert data["total_restaurants"] >= 1
