from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient

from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.main import app
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


def auth_headers(client: TestClient, email: str, password: str) -> dict:
    response = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_health(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_login_and_me(client: TestClient) -> None:
    headers = auth_headers(client, "waiter@harbor.example", "HarborWaiter!1")
    me = client.get("/api/v1/me", headers=headers)
    assert me.status_code == 200
    body = me.json()
    assert body["membership"]["role"] == "waiter"
    assert "orders.confirm_qr" in body["membership"]["permissions"]


def test_qr_order_stays_pending_until_staff_accept(client: TestClient) -> None:
    qr = DEMO_QR_TOKENS["T1"]
    menu = client.get(f"/api/v1/public/qr/{qr}/menu")
    assert menu.status_code == 200
    item_id = menu.json()["categories"][0]["items"][0]["id"]
    submit = client.post(
        f"/api/v1/public/qr/{qr}/orders",
        json={"items": [{"menu_item_id": item_id, "quantity": 1}], "customer_note": "no onions"},
        headers={"Idempotency-Key": "qr-order-key-0001"},
    )
    assert submit.status_code == 200, submit.text
    body = submit.json()
    assert body["order"]["status"] == "PENDING_CONFIRMATION"
    assert body["status_token"]
    order_id = body["order"]["id"]

    kitchen_headers = auth_headers(client, "kitchen@harbor.example", "HarborKitchen!1")
    tickets = client.get("/api/v1/kitchen/tickets", headers=kitchen_headers)
    assert tickets.status_code == 200
    assert tickets.json() == []

    waiter = auth_headers(client, "waiter@harbor.example", "HarborWaiter!1")
    accepted = client.post(f"/api/v1/orders/{order_id}/accept", headers=waiter)
    assert accepted.status_code == 200
    assert accepted.json()["status"] == "ACCEPTED"
    assert accepted.json()["dining_session_id"]

    tickets = client.get("/api/v1/kitchen/tickets", headers=kitchen_headers)
    assert len(tickets.json()) == 1


def test_idempotent_qr_submit(client: TestClient) -> None:
    qr = DEMO_QR_TOKENS["T2"]
    menu = client.get(f"/api/v1/public/qr/{qr}/menu")
    item_id = menu.json()["categories"][1]["items"][0]["id"]
    payload = {"items": [{"menu_item_id": item_id, "quantity": 2}], "customer_note": ""}
    first = client.post(
        f"/api/v1/public/qr/{qr}/orders",
        json=payload,
        headers={"Idempotency-Key": "same-key-abc-123"},
    )
    second = client.post(
        f"/api/v1/public/qr/{qr}/orders",
        json=payload,
        headers={"Idempotency-Key": "same-key-abc-123"},
    )
    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["order"]["id"] == second.json()["order"]["id"]


def test_kitchen_cannot_issue_bill(client: TestClient) -> None:
    headers = auth_headers(client, "kitchen@harbor.example", "HarborKitchen!1")
    response = client.post(
        "/api/v1/sessions/00000000-0000-0000-0000-000000000001/bill/issue",
        headers=headers,
    )
    assert response.status_code == 403


def test_invalid_qr_does_not_leak(client: TestClient) -> None:
    response = client.get("/api/v1/public/qr/not-a-real-token/menu")
    assert response.status_code == 404
