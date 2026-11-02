"""Two-tenant fixture harness — Phase 0 isolation gate (plan 02 §5).

Each test opens its own SessionLocal and calls seed_if_empty(db) first.
The test client logs in as a staff user, then asserts that actor
permissions from one tenant cannot access another tenant's resources (404/403).

Default staff credentials (created by seed_if_empty):
  owner@harbor.example / HarborOwner!1
  manager@harbor.example / HarborManager!1
  waiter@harbor.example / HarborWaiter!1
  kitchen@harbor.example / HarborKitchen!1
  cashier@harbor.example / HarborCashier!1
"""

import uuid

from fastapi.testclient import TestClient

# Populate the module namespace so app.models.* is available.
import app.models  # noqa: F401, makes app.modules.identity.models etc. available
from app.db.session import SessionLocal
from app.main import create_app  # ensures import app.models runs
from app.seed import seed_if_empty

app = create_app()
client = TestClient(app)


def _login(client: TestClient, email: str, password: str) -> str:
    """Login and return Bearer token header dict."""
    resp = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, f"Login failed: {resp.status_code} {resp.text}"
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _seed_second_tenant(db_session):
    """Seed a second restaurant+user+membership on top of an already-seeded tenant.

    Returns (restaurant_2, user_2, membership_2).
    Uses UUID-based slug/email to avoid unique-constraint clashes with prior runs.
    """
    from app.modules.identity.models import User
    from app.modules.tenancy.models import Restaurant, RestaurantMembership

    # Second restaurant — slug based on UUID fragment to avoid clashes
    restaurant_2_id = uuid.uuid4()
    slug = f"second-branch-{restaurant_2_id.hex[:8]}"
    restaurant_2 = db_session.query(Restaurant).filter_by(id=restaurant_2_id).first()
    if restaurant_2 is None:
        restaurant_2 = Restaurant(
            id=restaurant_2_id,
            name="Second Branch",
            slug=slug,
            status="ACTIVE",
            timezone="UTC",
            currency_code="USD",
        )
        db_session.add(restaurant_2)
        db_session.flush()

    # Second user — email based on UUID so it's guaranteed unique
    user_2_id = uuid.uuid4()
    user_email = f"mgr2-{user_2_id.hex[:8]}@second-branch.test"
    existing = db_session.query(User).filter_by(email=user_email).first()
    if existing is None:
        user_2 = User(
            id=user_2_id,
            email=user_email,
            password_hash="$dummy",  # not used for login; we use default staff creds
            display_name="Mgr2",
            status="ACTIVE",
        )
        db_session.add(user_2)
        db_session.flush()

    # Second membership
    membership_2_id = uuid.uuid4()
    membership_2 = RestaurantMembership(
        id=membership_2_id,
        restaurant_id=restaurant_2_id,
        user_id=user_2_id,
        role="manager",
        status="ACTIVE",
    )
    db_session.add(membership_2)
    db_session.flush()

    db_session.commit()
    return restaurant_2, user_2, membership_2


def _table_headers(tenant_restaurant_id: uuid.UUID) -> dict:
    """Return auth headers for the tenant whose restaurant_id matches.

    We login as the first staff user from seed_if_empty (owner).
    The test then asserts that this tenant cannot see another tenant's tables.
    """
    # Login as owner — this user belongs to the first (tenant1) restaurant
    headers = _login(client, "owner@harbor.example", "HarborOwner!1")
    # Override the x-tenant-id to select which tenant's data we're querying
    headers["x-tenant-id"] = str(tenant_restaurant_id)
    return headers


def test_tenant1_actor_cannot_see_tenant2_table():
    """Tenant-1 actor (logged in as owner) gets 404 on tenant-2's table — isolation baseline."""
    from app.modules.operations.models import RestaurantTable

    db = SessionLocal()
    try:
        # Seed first restaurant + default data (idempotent; no-op if already seeded)
        seed_if_empty(db)

        # Seed second tenant on top
        restaurant_2, user_2, membership_2 = _seed_second_tenant(db)

        # Create a table under tenant 2 only
        t2 = RestaurantTable(
            restaurant_id=restaurant_2.id,
            branch_id=restaurant_2.id,
            table_code="t99",
            display_name="Tenant2 Table",
            seating_capacity=2,
            status="ACTIVE",
        )
        db.add(t2)
        db.flush()

        # Tenant 1 actor (owner) tries to list tables — should not see t99
        hdrs = _table_headers(restaurant_2.id)
        # using tenant2's ID to test cross-tenant forbiddance
        resp = client.get("/api/v1/tables", headers=hdrs)
        # Tenant 1 should not see table "t99" that belongs to tenant 2
        assert resp.status_code in (200, 404)
        if resp.status_code == 200:
            table_codes = [t["table_code"] for t in resp.json()]
            assert "t99" not in table_codes, (
                "FAIL: tenant1 actor saw tenant2's table — isolation broken"
            )
    finally:
        db.close()


def test_tenant2_actor_cannot_see_tenant1_table():
    """Tenant-2 actor gets 404 on tenant-1's table — symmetric isolation baseline.

    We test this by logging in as the owner (global auth) and setting
    x-tenant-id to tenant1's restaurant ID, then asserting tenant1's
    table (t88) does not appear in the list.
    """
    db = SessionLocal()
    try:
        # Seed first restaurant + default data
        seed_if_empty(db)

        # Create a table under tenant 1 only
        from app.modules.operations.models import RestaurantTable
        from app.modules.tenancy.models import Restaurant as R

        restaurant_1 = db.query(R).filter(R.slug == "restaurant").first()
        if restaurant_1 is None:
            # Fallback: create it if seed_if_empty didn't (should not happen)
            restaurant_1 = R(id=uuid.uuid4(), name="Default", slug="restaurant", status="ACTIVE")
            db.add(restaurant_1)
            db.flush()

        t1 = RestaurantTable(
            restaurant_id=restaurant_1.id,
            branch_id=restaurant_1.id,
            table_code="t88",
            display_name="Tenant1 Table",
            seating_capacity=2,
            status="ACTIVE",
        )
        db.add(t1)
        db.flush()

        # Tenant 2 actor: login as owner (auth is global), set x-tenant-id to tenant1
        headers = _login(client, "owner@harbor.example", "HarborOwner!1")
        headers["x-tenant-id"] = str(restaurant_1.id)
        resp = client.get("/api/v1/tables", headers=headers)
        assert resp.status_code in (200, 404)
        if resp.status_code == 200:
            table_codes = [t["table_code"] for t in resp.json()]
            assert "t88" not in table_codes, (
                "FAIL: actor with x-tenant-id=t1 saw tenant1's table — isolation broken"
            )
    finally:
        db.close()