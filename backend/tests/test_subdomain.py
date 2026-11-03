"""Plan 07 M7 — customer subdomain, hostname cross-check, per-tenant branding.

Covers the exit criteria from backend/webplan/07-customer-subdomain.md:
- staff can configure the customer surface (settings.manage)
- D5: subdomain is chosen once, then locked
- uniqueness + reserved-label guards
- QR endpoints cross-check the request Host and fail closed (403, no redirect)
- per-tenant branding reaches the public QR menu payload
"""

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient

from app.core.security import hash_password
from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.main import app
from app.modules.identity.models import User
from app.modules.tenancy.models import Restaurant, RestaurantMembership, RestaurantSettings
from app.seed import DEMO_QR_TOKENS, seed_if_empty


@pytest.fixture(scope="module")
def client() -> Generator[TestClient, None, None]:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_if_empty(db)
    finally:
        db.close()
    with TestClient(app) as test_client:
        yield test_client


def _sign_in(client: TestClient, email: str, password: str) -> dict[str, str]:
    response = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.fixture(scope="module")
def manager(client: TestClient) -> dict[str, str]:
    return _sign_in(client, "manager@harbor.example", "HarborManager!1")


@pytest.fixture(scope="module")
def second_owner(client: TestClient) -> dict[str, str]:
    """An independent tenant (own subdomain slot, own owner) for conflict tests."""
    db = SessionLocal()
    try:
        restaurant = Restaurant(
            name="Riverside Grill",
            slug="riverside",
            timezone="UTC",
            currency_code="USD",
            status="ACTIVE",
        )
        db.add(restaurant)
        db.flush()
        db.add(RestaurantSettings(restaurant_id=restaurant.id))
        user = User(
            email="owner@riverside.example",
            password_hash=hash_password("RiversideOwner!1"),
            display_name="Riverside Owner",
            status="ACTIVE",
        )
        db.add(user)
        db.flush()
        db.add(
            RestaurantMembership(
                restaurant_id=restaurant.id,
                user_id=user.id,
                role="owner",
                status="ACTIVE",
            )
        )
        db.commit()
    finally:
        db.close()
    return _sign_in(client, "owner@riverside.example", "RiversideOwner!1")


# --- Staff configuration ------------------------------------------------------


def test_customer_host_defaults_derive_from_slug(client: TestClient, manager: dict) -> None:
    response = client.get("/api/v1/restaurant/customer-host", headers=manager)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["customer_subdomain"] == "harbor-table"
    assert body["customer_hostname"] == "harbor-table.platform.com"
    assert body["custom_domain"] is None


def test_branding_round_trip(client: TestClient, manager: dict) -> None:
    response = client.put(
        "/api/v1/restaurant/customer-host",
        json={"brand_accent_hex": "#3B82F6", "brand_logo_url": "https://cdn.example/logo.png"},
        headers=manager,
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["brand_accent_hex"] == "#3B82F6"
    assert body["brand_logo_url"] == "https://cdn.example/logo.png"
    # None of the identity fields changed.
    assert body["customer_hostname"] == "harbor-table.platform.com"


def test_subdomain_is_locked_once_set(client: TestClient, manager: dict) -> None:
    response = client.put(
        "/api/v1/restaurant/customer-host",
        json={"customer_subdomain": "something-else"},
        headers=manager,
    )
    assert response.status_code == 409, response.text
    assert response.json()["code"] == "SUBDOMAIN_LOCKED"


def test_custom_domain_replaces_primary_hostname(client: TestClient, manager: dict) -> None:
    response = client.put(
        "/api/v1/restaurant/customer-host",
        json={"custom_domain": "menu.riverside-harbor.example"},
        headers=manager,
    )
    assert response.status_code == 200, response.text
    assert response.json()["customer_hostname"] == "menu.riverside-harbor.example"

    clear = client.put(
        "/api/v1/restaurant/customer-host", json={"custom_domain": None}, headers=manager
    )
    assert clear.status_code == 200, clear.text
    assert clear.json()["custom_domain"] is None
    assert clear.json()["customer_hostname"] == "harbor-table.platform.com"


def test_restaurant_endpoint_returns_customer_hostname(client: TestClient, manager: dict) -> None:
    response = client.get("/api/v1/restaurant", headers=manager)
    assert response.status_code == 200, response.text
    assert response.json()["customer_hostname"] == "harbor-table.platform.com"


def test_customer_host_requires_settings_permission(client: TestClient) -> None:
    waiter = _sign_in(client, "waiter@harbor.example", "HarborWaiter!1")
    response = client.get("/api/v1/restaurant/customer-host", headers=waiter)
    assert response.status_code == 403, response.text
    assert response.json()["code"] == "FORBIDDEN"


# --- Subdomain claim rules (D5: launch-time selection) -------------------------


def test_invalid_labels_are_rejected(client: TestClient, second_owner: dict) -> None:
    for label in ("ab", "has_underscore", "-leading", "trailing-", "x" * 64):
        response = client.put(
            "/api/v1/restaurant/customer-host",
            json={"customer_subdomain": label},
            headers=second_owner,
        )
        assert response.status_code == 422, f"{label}: {response.text}"
        assert response.json()["code"] == "INVALID_SUBDOMAIN"


def test_reserved_labels_are_rejected(client: TestClient, second_owner: dict) -> None:
    response = client.put(
        "/api/v1/restaurant/customer-host",
        json={"customer_subdomain": "admin"},
        headers=second_owner,
    )
    assert response.status_code == 409, response.text
    assert response.json()["code"] == "RESERVED_SUBDOMAIN"


def test_subdomain_claim_is_unique_and_locks(
    client: TestClient, second_owner: dict
) -> None:
    response = client.put(
        "/api/v1/restaurant/customer-host",
        json={"customer_subdomain": "harbor-table"},
        headers=second_owner,
    )
    assert response.status_code == 409, response.text
    assert response.json()["code"] == "SUBDOMAIN_TAKEN"

    ok = client.put(
        "/api/v1/restaurant/customer-host",
        json={"customer_subdomain": "riverside-grill"},
        headers=second_owner,
    )
    assert ok.status_code == 200, ok.text
    assert ok.json()["customer_hostname"] == "riverside-grill.platform.com"

    locked = client.put(
        "/api/v1/restaurant/customer-host",
        json={"customer_subdomain": "yet-another"},
        headers=second_owner,
    )
    assert locked.status_code == 409, locked.text
    assert locked.json()["code"] == "SUBDOMAIN_LOCKED"


# --- Public QR hostname cross-check (no cross-tenant redirect) ----------------


def test_qr_menu_fails_closed_on_unknown_host(client: TestClient) -> None:
    qr = DEMO_QR_TOKENS["T1"]
    response = client.get(
        f"/api/v1/public/qr/{qr}/menu", headers={"Host": "not-our-tenant.platform.com"}
    )
    assert response.status_code == 403, response.text
    body = response.json()
    assert body["code"] == "QR_HOST_MISMATCH"


def test_qr_tokens_never_resolve_through_other_tenants_host(
    client: TestClient, second_owner: dict
) -> None:
    qr = DEMO_QR_TOKENS["T1"]
    response = client.get(
        f"/api/v1/public/qr/{qr}/menu", headers={"Host": "riverside-grill.platform.com"}
    )
    assert response.status_code == 403, response.text


def test_qr_menu_allows_correct_subdomain_host(client: TestClient) -> None:
    qr = DEMO_QR_TOKENS["T1"]
    response = client.get(
        f"/api/v1/public/qr/{qr}/menu", headers={"Host": "harbor-table.platform.com"}
    )
    assert response.status_code == 200, response.text
    assert response.json()["restaurant_name"] == "Harbor Table"


def test_qr_menu_allows_custom_domain_host(client: TestClient, manager: dict) -> None:
    set_domain = client.put(
        "/api/v1/restaurant/customer-host",
        json={"custom_domain": "order.harbortable.example"},
        headers=manager,
    )
    assert set_domain.status_code == 200, set_domain.text

    qr = DEMO_QR_TOKENS["T1"]
    via_custom = client.get(
        f"/api/v1/public/qr/{qr}/menu", headers={"Host": "order.harbortable.example"}
    )
    assert via_custom.status_code == 200, via_custom.text

    # The managed subdomain remains valid alongside the custom domain.
    via_subdomain = client.get(
        f"/api/v1/public/qr/{qr}/menu", headers={"Host": "harbor-table.platform.com"}
    )
    assert via_subdomain.status_code == 200, via_subdomain.text

    client.put(
        "/api/v1/restaurant/customer-host", json={"custom_domain": None}, headers=manager
    )


def test_local_dev_hosts_still_work(client: TestClient) -> None:
    qr = DEMO_QR_TOKENS["T1"]
    for host in ("localhost", "127.0.0.1"):
        response = client.get(f"/api/v1/public/qr/{qr}/menu", headers={"Host": f"{host}:5173"})
        assert response.status_code == 200, f"{host}: {response.text}"


def test_branding_reaches_public_menu_payload(client: TestClient, manager: dict) -> None:
    response = client.put(
        "/api/v1/restaurant/customer-host",
        json={"brand_accent_hex": "#8B5CF6"},
        headers=manager,
    )
    assert response.status_code == 200, response.text

    qr = DEMO_QR_TOKENS["T1"]
    menu = client.get(
        f"/api/v1/public/qr/{qr}/menu", headers={"Host": "harbor-table.platform.com"}
    )
    assert menu.status_code == 200, menu.text
    assert menu.json()["brand_accent_hex"] == "#8B5CF6"
    assert menu.json()["customer_hostname"] == "harbor-table.platform.com"


def test_qr_order_rejected_on_wrong_host(client: TestClient) -> None:
    qr = DEMO_QR_TOKENS["T2"]
    # A valid order payload is required so the request reaches the handler;
    # the guard must fire before anything is created.
    menu = client.get(f"/api/v1/public/qr/{qr}/menu")
    item_id = menu.json()["categories"][0]["items"][0]["id"]
    response = client.post(
        f"/api/v1/public/qr/{qr}/orders",
        json={"items": [{"menu_item_id": item_id, "quantity": 1}], "customer_note": ""},
        headers={"Host": "not-our-tenant.platform.com", "Idempotency-Key": "subdomain-host-guard"},
    )
    assert response.status_code == 403, response.text
    assert response.json()["code"] == "QR_HOST_MISMATCH"
