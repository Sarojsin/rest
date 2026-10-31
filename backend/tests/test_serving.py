"""Serving workflow: the kitchen stops at READY; delivering food to the guest
(`SERVED`) is a waiter/manager/owner action gated behind `orders.serve`.

After the last item is served the order completes automatically, which is what
drives the guest's bill view.
"""

from collections.abc import Generator
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.seed import seed_if_empty

_engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
_TestSession = sessionmaker(bind=_engine, autoflush=False, autocommit=False, expire_on_commit=False)

DEMO_TABLE_TOKEN = "table-harbor-1-alpha"


@pytest.fixture(scope="module")
def client() -> Generator[TestClient, None, None]:
    """Isolated in-memory DB: the dev database is never touched."""
    Base.metadata.create_all(bind=_engine)
    db = _TestSession()
    try:
        seed_if_empty(db)
    finally:
        db.close()

    def override_get_db() -> Generator:
        session = _TestSession()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.pop(get_db, None)
        Base.metadata.drop_all(bind=_engine)


def auth_headers(client: TestClient, email: str, password: str) -> dict:
    response = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def waiter(client: TestClient) -> dict:
    return auth_headers(client, "waiter@harbor.example", "HarborWaiter!1")


def kitchen(client: TestClient) -> dict:
    return auth_headers(client, "kitchen@harbor.example", "HarborKitchen!1")


def _submit_qr_order(client: TestClient) -> str:
    """Guest submits an order from the table QR; returns the order id."""
    menu = client.get(f"/api/v1/public/qr/{DEMO_TABLE_TOKEN}/menu")
    assert menu.status_code == 200, menu.text
    item_id = menu.json()["categories"][0]["items"][0]["id"]
    response = client.post(
        f"/api/v1/public/qr/{DEMO_TABLE_TOKEN}/orders",
        json={"items": [{"menu_item_id": item_id, "quantity": 1}], "customer_note": ""},
        headers={"Idempotency-Key": f"test-serve-{uuid4()}"},
    )
    assert response.status_code == 200, response.text
    return response.json()["order"]["id"]


def _accept(client: TestClient, headers: dict, order_id: str) -> None:
    response = client.post(f"/api/v1/orders/{order_id}/accept", headers=headers)
    assert response.status_code == 200, response.text


def _first_ticket_item(client: TestClient, headers: dict, order_id: str) -> dict:
    """The ticket for this order — never `tickets[0]` overall, which may belong
    to an earlier order in the module-scoped database."""
    tickets = client.get("/api/v1/kitchen/tickets", headers=headers).json()
    matches = [t for t in tickets if t["order_id"] == order_id]
    assert matches, "No kitchen ticket was created for this order"
    return matches[0]["items"][0]


def _set_status(client: TestClient, headers: dict, item_id: str, status: str):
    return client.post(
        f"/api/v1/kitchen/ticket-items/{item_id}/status",
        json={"status": status},
        headers=headers,
    )


# ── FULL HAPPY PATH ───────────────────────────────────────────────────────────


def test_waiter_serves_and_order_completes(client: TestClient) -> None:
    waiter_headers = waiter(client)
    order_id = _submit_qr_order(client)
    _accept(client, waiter_headers, order_id)

    # Kitchen moves the item NEW -> PREPARING -> READY
    kitchen_headers = kitchen(client)
    item = _first_ticket_item(client, kitchen_headers, order_id)
    assert _set_status(client, kitchen_headers, item["id"], "PREPARING").status_code == 200
    assert _set_status(client, kitchen_headers, item["id"], "READY").status_code == 200

    # The waiter — not the kitchen — delivers it to the guest
    served = _set_status(client, waiter_headers, item["id"], "SERVED")
    assert served.status_code == 200, served.text

    # Serving the last item completes the order for the guest's bill view
    order = client.get(f"/api/v1/orders/{order_id}", headers=waiter_headers).json()
    assert order["status"] == "COMPLETED"


def test_public_status_shows_completed_after_serve(client: TestClient) -> None:
    waiter_headers = waiter(client)
    menu = client.get(f"/api/v1/public/qr/{DEMO_TABLE_TOKEN}/menu")
    item_id = menu.json()["categories"][0]["items"][0]["id"]
    submit = client.post(
        f"/api/v1/public/qr/{DEMO_TABLE_TOKEN}/orders",
        json={"items": [{"menu_item_id": item_id, "quantity": 1}], "customer_note": ""},
        headers={"Idempotency-Key": f"test-serve-public-{uuid4()}"},
    )
    order_id, status_token = submit.json()["order"]["id"], submit.json()["status_token"]
    _accept(client, waiter_headers, order_id)

    kitchen_headers = kitchen(client)
    item = _first_ticket_item(client, kitchen_headers, order_id)
    _set_status(client, kitchen_headers, item["id"], "PREPARING")
    _set_status(client, kitchen_headers, item["id"], "READY")

    assert _set_status(client, waiter_headers, item["id"], "SERVED").status_code == 200

    status = client.get(f"/api/v1/public/orders/{status_token}")
    assert status.status_code == 200
    assert status.json()["status"] == "COMPLETED"


# ── PERMISSION BOUNDARIES ────────────────────────────────────────────────────


def test_kitchen_cannot_mark_served(client: TestClient) -> None:
    waiter_headers = waiter(client)
    order_id = _submit_qr_order(client)
    _accept(client, waiter_headers, order_id)

    kitchen_headers = kitchen(client)
    item = _first_ticket_item(client, kitchen_headers, order_id)
    _set_status(client, kitchen_headers, item["id"], "PREPARING")
    _set_status(client, kitchen_headers, item["id"], "READY")

    denied = _set_status(client, kitchen_headers, item["id"], "SERVED")
    assert denied.status_code == 403, denied.text
    assert denied.json()["code"] == "FORBIDDEN"
    # Untouched — the order is still open
    order = client.get(f"/api/v1/orders/{order_id}", headers=waiter_headers).json()
    assert order["status"] == "ACCEPTED"


def test_waiter_cannot_drive_kitchen_progress(client: TestClient) -> None:
    waiter_headers = waiter(client)
    order_id = _submit_qr_order(client)
    _accept(client, waiter_headers, order_id)

    item = _first_ticket_item(client, waiter_headers, order_id)
    assert item["status"] == "NEW"

    denied = _set_status(client, waiter_headers, item["id"], "PREPARING")
    assert denied.status_code == 403, denied.text
    assert denied.json()["code"] == "FORBIDDEN"

    # Kitchen staff can still do everything up to READY
    kitchen_headers = kitchen(client)
    assert _set_status(client, kitchen_headers, item["id"], "PREPARING").status_code == 200
    assert _set_status(client, kitchen_headers, item["id"], "READY").status_code == 200


def test_cashier_cannot_serve_and_cannot_prepare(client: TestClient) -> None:
    cashier = auth_headers(client, "cashier@harbor.example", "HarborCashier!1")
    waiter_headers = waiter(client)
    order_id = _submit_qr_order(client)
    _accept(client, waiter_headers, order_id)

    item = _first_ticket_item(client, cashier, order_id)
    assert _set_status(client, cashier, item["id"], "SERVED").status_code == 403
    assert _set_status(client, cashier, item["id"], "PREPARING").status_code == 403


def test_manager_can_serve(client: TestClient) -> None:
    manager = auth_headers(client, "manager@harbor.example", "HarborManager!1")
    waiter_headers = waiter(client)
    order_id = _submit_qr_order(client)
    _accept(client, waiter_headers, order_id)

    kitchen_headers = kitchen(client)
    item = _first_ticket_item(client, kitchen_headers, order_id)
    _set_status(client, kitchen_headers, item["id"], "PREPARING")
    _set_status(client, kitchen_headers, item["id"], "READY")

    assert _set_status(client, manager, item["id"], "SERVED").status_code == 200
