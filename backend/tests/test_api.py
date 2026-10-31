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


def menu_item_ids(client: TestClient, headers: dict) -> list[str]:
    menu = client.get("/api/v1/menu", headers=headers)
    assert menu.status_code == 200, menu.text
    return [item["id"] for category in menu.json() for item in category["items"]]


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


def test_service_call_dedupe_and_acknowledge(client: TestClient) -> None:
    qr = DEMO_QR_TOKENS["T3"]

    first = client.post(f"/api/v1/public/qr/{qr}/service-calls")
    assert first.status_code == 200, first.text
    call_one = first.json()
    assert call_one["status"] == "REQUESTED"
    assert call_one["deduplicated"] is False

    second = client.post(f"/api/v1/public/qr/{qr}/service-calls")
    assert second.status_code == 200
    call_two = second.json()
    assert call_two["id"] == call_one["id"]
    assert call_two["deduplicated"] is True

    waiter = auth_headers(client, "waiter@harbor.example", "HarborWaiter!1")
    listing = client.get("/api/v1/service-calls?status=REQUESTED", headers=waiter)
    assert listing.status_code == 200, listing.text
    listed = [call for call in listing.json() if call["id"] == call_one["id"]]
    assert listed and listed[0]["table_display_name"].startswith("Table")

    acknowledged = client.post(
        f"/api/v1/service-calls/{call_one['id']}/acknowledge", headers=waiter
    )
    assert acknowledged.status_code == 200
    assert acknowledged.json()["status"] == "ACKNOWLEDGED"
    assert acknowledged.json()["acknowledged_at"]

    again = client.post(f"/api/v1/service-calls/{call_one['id']}/acknowledge", headers=waiter)
    assert again.status_code == 200
    assert again.json()["status"] == "ACKNOWLEDGED"

    latest = client.get(f"/api/v1/public/qr/{qr}/service-calls/latest")
    assert latest.status_code == 200
    assert latest.json()["call"]["status"] == "ACKNOWLEDGED"

    rearm = client.post(f"/api/v1/public/qr/{qr}/service-calls")
    assert rearm.status_code == 200
    assert rearm.json()["id"] != call_one["id"]


def test_kitchen_call_waiter_signals_service(client: TestClient) -> None:
    # Waiter sends an order straight to the kitchen (ACCEPTED => ticket exists).
    waiter = auth_headers(client, "waiter@harbor.example", "HarborWaiter!1")
    tables = client.get("/api/v1/tables", headers=waiter)
    assert tables.status_code == 200, tables.text
    table_id = tables.json()[0]["id"]
    menu_items = menu_item_ids(client, waiter)
    created = client.post(
        "/api/v1/orders",
        json={
            "table_id": table_id,
            "items": [{"menu_item_id": menu_items[0], "quantity": 2}],
        },
        headers={**waiter, "Idempotency-Key": "kitchen-call-test-0001"},
    )
    assert created.status_code == 200, created.text
    order = created.json()
    assert order["status"] == "ACCEPTED"

    kitchen = auth_headers(client, "kitchen@harbor.example", "HarborKitchen!1")
    tickets = client.get("/api/v1/kitchen/tickets", headers=kitchen)
    ticket = next(t for t in tickets.json() if t["order_id"] == order["id"])
    assert ticket["status"] == "NEW"
    assert ticket["table_display_name"]  # still resolved server-side for waiter-facing UI

    # Kitchen presses "Call waiter": items go READY, a KITCHEN service call is born.
    signaled = client.post(
        f"/api/v1/kitchen/tickets/{ticket['id']}/call-waiter", headers=kitchen
    )
    assert signaled.status_code == 200, signaled.text
    body = signaled.json()
    assert body["status"] == "READY"
    assert body["ready_at"]
    assert all(item["status"] in {"READY", "SERVED"} for item in body["items"])

    # Staff queue shows a KITCHEN call with ticket number + item summary.
    listing = client.get("/api/v1/service-calls?status=REQUESTED", headers=waiter)
    assert listing.status_code == 200, listing.text
    pickup = [
        c
        for c in listing.json()
        if c["kind"] == "KITCHEN" and c["ticket_number"] == body["ticket_number"]
    ]
    assert pickup, listing.json()
    pickup_call = pickup[0]
    assert pickup_call["table_display_name"]
    assert "2x" in pickup_call["items_summary"]
    assert pickup_call["status"] == "REQUESTED"

    # Repeat press is idempotent (same ticket, one open call → no new row).
    again = client.post(f"/api/v1/kitchen/tickets/{ticket['id']}/call-waiter", headers=kitchen)
    assert again.status_code == 200
    listing_two = client.get("/api/v1/service-calls?status=REQUESTED", headers=waiter)
    open_kitchen_calls = [
        c
        for c in listing_two.json()
        if c["kind"] == "KITCHEN" and c["ticket_number"] == body["ticket_number"]
    ]
    assert len(open_kitchen_calls) == 1

    # Waiter acknowledges the pickup like any other call.
    acknowledged = client.post(
        f"/api/v1/service-calls/{pickup_call['id']}/acknowledge", headers=waiter
    )
    assert acknowledged.status_code == 200, acknowledged.text
    ack = acknowledged.json()
    assert ack["status"] == "ACKNOWLEDGED"
    assert ack["kind"] == "KITCHEN" and ack["ticket_number"] == body["ticket_number"]

    # After the pickup was acknowledged, the kitchen can re-signal the same ticket.
    rearm = client.post(f"/api/v1/kitchen/tickets/{ticket['id']}/call-waiter", headers=kitchen)
    assert rearm.status_code == 200
    listing_three = client.get("/api/v1/service-calls?status=REQUESTED", headers=waiter)
    assert any(
        c["kind"] == "KITCHEN" and c["ticket_number"] == body["ticket_number"]
        for c in listing_three.json()
    )


def test_kitchen_call_waiter_is_tenant_scoped_and_forbidden_without_permission(
    client: TestClient,
) -> None:
    waiter = auth_headers(client, "waiter@harbor.example", "HarborWaiter!1")
    table_id = client.get("/api/v1/tables", headers=waiter).json()[1]["id"]
    menu_items = menu_item_ids(client, waiter)
    created = client.post(
        "/api/v1/orders",
        json={
            "table_id": table_id,
            "items": [{"menu_item_id": menu_items[1], "quantity": 1}],
        },
        headers={**waiter, "Idempotency-Key": "kitchen-call-test-0002"},
    )
    assert created.status_code == 200, created.text
    kitchen = auth_headers(client, "kitchen@harbor.example", "HarborKitchen!1")
    ticket_id = next(
        t["id"]
        for t in client.get("/api/v1/kitchen/tickets", headers=kitchen).json()
        if t["order_id"] == created.json()["id"]
    )

    # Waiter lacks kitchen.update → 403, and no signal is created.
    denied = client.post(f"/api/v1/kitchen/tickets/{ticket_id}/call-waiter", headers=waiter)
    assert denied.status_code == 403

    # Unknown id inside the tenant reads as not found.
    missing = client.post(
        "/api/v1/kitchen/tickets/00000000-0000-0000-0000-00000000abcd/call-waiter",
        headers=kitchen,
    )
    assert missing.status_code == 404


def test_kitchen_call_waiter_rejects_closed_tickets(client: TestClient) -> None:
    waiter = auth_headers(client, "waiter@harbor.example", "HarborWaiter!1")
    table_id = client.get("/api/v1/tables", headers=waiter).json()[2]["id"]
    menu_items = menu_item_ids(client, waiter)
    created = client.post(
        "/api/v1/orders",
        json={
            "table_id": table_id,
            "items": [{"menu_item_id": menu_items[0], "quantity": 1}],
        },
        headers={**waiter, "Idempotency-Key": "kitchen-call-test-0003"},
    )
    assert created.status_code == 200, created.text
    kitchen = auth_headers(client, "kitchen@harbor.example", "HarborKitchen!1")
    tickets = client.get("/api/v1/kitchen/tickets", headers=kitchen)
    ticket = next(t for t in tickets.json() if t["order_id"] == created.json()["id"])

    # Close the workflow: kitchen signals ready; the waiter serves → the parent
    # order completes. Serving is floor work, not a kitchen action.
    ready = client.post(f"/api/v1/kitchen/tickets/{ticket['id']}/call-waiter", headers=kitchen)
    assert ready.status_code == 200, ready.text
    served = client.post(
        f"/api/v1/kitchen/ticket-items/{ticket['items'][0]['id']}/status",
        json={"status": "SERVED"},
        headers=waiter,
    )
    assert served.status_code == 200, served.text

    # With the order COMPLETED the ticket is closed: further calls are 409s.
    call = client.post(f"/api/v1/kitchen/tickets/{ticket['id']}/call-waiter", headers=kitchen)
    assert call.status_code == 409, call.text
    assert call.json()["code"] == "KITCHEN_STATE_CONFLICT"


def test_cancelling_last_item_returns_ticket_not_404(client: TestClient) -> None:
    waiter = auth_headers(client, "waiter@harbor.example", "HarborWaiter!1")
    table_id = client.get("/api/v1/tables", headers=waiter).json()[3]["id"]
    menu_items = menu_item_ids(client, waiter)
    created = client.post(
        "/api/v1/orders",
        json={
            "table_id": table_id,
            "items": [{"menu_item_id": menu_items[0], "quantity": 1}],
        },
        headers={**waiter, "Idempotency-Key": "kitchen-cancel-test-0001"},
    )
    assert created.status_code == 200, created.text
    kitchen = auth_headers(client, "kitchen@harbor.example", "HarborKitchen!1")
    ticket = next(
        t
        for t in client.get("/api/v1/kitchen/tickets", headers=kitchen).json()
        if t["order_id"] == created.json()["id"]
    )

    # Cancelling the only open item closes the ticket; the transition response
    # must still come back (200) instead of a misleading 404.
    cancelled = client.post(
        f"/api/v1/kitchen/ticket-items/{ticket['items'][0]['id']}/status",
        json={"status": "CANCELLED"},
        headers=kitchen,
    )
    assert cancelled.status_code == 200, cancelled.text
    body = cancelled.json()
    assert body["status"] == "CANCELLED"
    assert body["items"][0]["status"] == "CANCELLED"
    # And it no longer appears in the active kitchen queue.
    remaining = [t["id"] for t in client.get("/api/v1/kitchen/tickets", headers=kitchen).json()]
    assert ticket["id"] not in remaining


def test_kitchen_cannot_acknowledge_service_calls(client: TestClient) -> None:

    qr = DEMO_QR_TOKENS["T5"]
    created = client.post(f"/api/v1/public/qr/{qr}/service-calls")
    assert created.status_code == 200

    kitchen = auth_headers(client, "kitchen@harbor.example", "HarborKitchen!1")
    listing = client.get("/api/v1/service-calls?status=REQUESTED", headers=kitchen)
    assert listing.status_code == 200
    assert any(call["id"] == created.json()["id"] for call in listing.json())

    denied = client.post(
        f"/api/v1/service-calls/{created.json()['id']}/acknowledge", headers=kitchen
    )
    assert denied.status_code == 403


def test_ingredients_visible_in_public_menu(client: TestClient) -> None:
    menu = client.get(f"/api/v1/public/qr/{DEMO_QR_TOKENS['T1']}/menu")
    assert menu.status_code == 200
    steam_momo = menu.json()["categories"][0]["items"][0]
    assert "gluten" in steam_momo["ingredients_text"]
    assert "sesame" in steam_momo["ingredients_text"]

    manager = auth_headers(client, "manager@harbor.example", "HarborManager!1")
    item_id = steam_momo["id"]
    updated = client.patch(
        f"/api/v1/menu/items/{item_id}",
        json={"ingredients_text": "Test only: contains nuts"},
        headers=manager,
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["ingredients_text"] == "Test only: contains nuts"

    refreshed = client.get(f"/api/v1/public/qr/{DEMO_QR_TOKENS['T1']}/menu")
    assert (
        refreshed.json()["categories"][0]["items"][0]["ingredients_text"]
        == "Test only: contains nuts"
    )

    too_long = client.patch(
        f"/api/v1/menu/items/{item_id}",
        json={"ingredients_text": "x" * 501},
        headers=manager,
    )
    assert too_long.status_code == 422
