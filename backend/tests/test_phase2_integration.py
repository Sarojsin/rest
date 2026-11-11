"""Phase 2 integration tests for new mobile app endpoints.

Covers inventory reports, stock counts, payment methods, advanced reports,
and audit events that were added for mobile feature parity.
"""

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


def _auth(client: TestClient, email: str, password: str) -> dict:
    response = client.post(
        "/api/v1/auth/login", json={"email": email, "password": password}
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.fixture(scope="module")
def owner(client: TestClient) -> dict:
    return _auth(client, "owner@harbor.example", "HarborOwner!1")


@pytest.fixture(scope="module")
def manager(client: TestClient) -> dict:
    return _auth(client, "manager@harbor.example", "HarborManager!1")


@pytest.fixture(scope="module")
def waiter(client: TestClient) -> dict:
    return _auth(client, "waiter@harbor.example", "HarborWaiter!1")


@pytest.fixture(scope="module")
def cashier(client: TestClient) -> dict:
    return _auth(client, "cashier@harbor.example", "HarborCashier!1")


@pytest.fixture(scope="module")
def branch(client: TestClient, owner: dict) -> dict:
    response = client.post(
        "/api/v1/branches",
        json={"name": "Downtown", "code": "DT", "address": "1 Main St"},
        headers=owner,
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_inventory_reports_low_stock(
    client: TestClient, owner: dict, branch: dict
) -> None:
    # Create supplier and ingredient with low stock
    supplier = client.post(
        "/api/v1/inventory/suppliers",
        json={"name": "Test Supplier", "email": "test@supplier.com"},
        headers=owner,
    )
    assert supplier.status_code == 201
    supplier_id = supplier.json()["id"]

    ingredient = client.post(
        "/api/v1/inventory/ingredients",
        json={
            "name": "Low Stock Item",
            "unit": "kg",
            "current_stock": 2,
            "minimum_stock": 10,
            "supplier_id": supplier_id,
        },
        headers=owner,
    )
    assert ingredient.status_code == 201

    # Test low stock report
    report = client.get("/api/v1/inventory/reports/low-stock", headers=owner)
    assert report.status_code == 200
    body = report.json()
    assert body["low_stock_count"] >= 1
    assert any(i["name"] == "Low Stock Item" for i in body["ingredients"])
    assert any(i["current_stock"] < i["minimum_stock"] for i in body["ingredients"])


def test_inventory_reports_consumption(
    client: TestClient, owner: dict, branch: dict
) -> None:
    # Create ingredient and record some stock movements
    supplier = client.post(
        "/api/v1/inventory/suppliers",
        json={"name": "Consumption Supplier", "email": "consumption@supplier.com"},
        headers=owner,
    )
    supplier_id = supplier.json()["id"]

    ingredient = client.post(
        "/api/v1/inventory/ingredients",
        json={
            "name": "Consumed Item",
            "unit": "kg",
            "current_stock": 50,
            "minimum_stock": 5,
            "supplier_id": supplier_id,
        },
        headers=owner,
    )
    ingredient_id = ingredient.json()["id"]

    # Record some DEDUCT movements
    for _ in range(3):
        client.post(
            "/api/v1/inventory/stock-movements",
            json={
                "ingredient_id": ingredient_id,
                "movement_type": "DEDUCT",
                "quantity": 5,
                "reason": "Sold to customers",
            },
            headers=owner,
        )

    # Test consumption report
    report = client.get("/api/v1/inventory/reports/consumption", headers=owner)
    assert report.status_code == 200
    body = report.json()
    assert "consumption" in body
    assert any(i["ingredient_name"] == "Consumed Item" for i in body["consumption"])
    consumed = next(
        i for i in body["consumption"] if i["ingredient_name"] == "Consumed Item"
    )
    assert consumed["total_deducted"] >= 15


def test_inventory_reports_waste(
    client: TestClient, owner: dict, branch: dict
) -> None:
    # Create ingredient and record waste movements
    supplier = client.post(
        "/api/v1/inventory/suppliers",
        json={"name": "Waste Supplier", "email": "waste@supplier.com"},
        headers=owner,
    )
    supplier_id = supplier.json()["id"]

    ingredient = client.post(
        "/api/v1/inventory/ingredients",
        json={
            "name": "Wasted Item",
            "unit": "kg",
            "current_stock": 20,
            "minimum_stock": 2,
            "supplier_id": supplier_id,
        },
        headers=owner,
    )
    ingredient_id = ingredient.json()["id"]

    # Record waste movements
    client.post(
        "/api/v1/inventory/stock-movements",
        json={
            "ingredient_id": ingredient_id,
            "movement_type": "WASTE",
            "quantity": 3,
            "reason": "Spoiled",
        },
        headers=owner,
    )

    # Test waste report
    report = client.get("/api/v1/inventory/reports/waste?days=7", headers=owner)
    assert report.status_code == 200
    body = report.json()
    assert body["window_days"] == 7
    assert "waste" in body
    assert any(i["ingredient_name"] == "Wasted Item" for i in body["waste"])
    wasted = next(
        i for i in body["waste"] if i["ingredient_name"] == "Wasted Item"
    )
    assert wasted["total_wasted"] >= 3


def test_inventory_reports_expiring_batches(
    client: TestClient, owner: dict, branch: dict
) -> None:
    # Create ingredient and batch expiring soon
    supplier = client.post(
        "/api/v1/inventory/suppliers",
        json={"name": "Batch Supplier", "email": "batch@supplier.com"},
        headers=owner,
    )
    supplier_id = supplier.json()["id"]

    ingredient = client.post(
        "/api/v1/inventory/ingredients",
        json={
            "name": "Expiring Item",
            "unit": "kg",
            "current_stock": 10,
            "minimum_stock": 1,
            "supplier_id": supplier_id,
        },
        headers=owner,
    )
    ingredient_id = ingredient.json()["id"]

    # Create batch expiring within 7 days
    from datetime import UTC, datetime, timedelta
    expiry = (datetime.now(UTC) + timedelta(days=3)).isoformat()
    batch = client.post(
        "/api/v1/inventory/batches",
        json={
            "ingredient_id": ingredient_id,
            "batch_no": "BATCH-EXP-001",
            "expiry_date": expiry,
            "quantity": 5,
            "cost_per_unit_minor": 100,
        },
        headers=owner,
    )
    assert batch.status_code == 201

    # Test expiring batches report
    report = client.get("/api/v1/inventory/reports/expiring-batches?days=7", headers=owner)
    assert report.status_code == 200
    body = report.json()
    assert body["window_days"] == 7
    assert "batches" in body
    assert any(b["batch_no"] == "BATCH-EXP-001" for b in body["batches"])
    expiring = next(
        b for b in body["batches"] if b["batch_no"] == "BATCH-EXP-001"
    )
    assert expiring["expired"] is False


def test_inventory_stock_counts_create_and_complete(
    client: TestClient, owner: dict, branch: dict
) -> None:
    # Create ingredient
    supplier = client.post(
        "/api/v1/inventory/suppliers",
        json={"name": "Count Supplier", "email": "count@supplier.com"},
        headers=owner,
    )
    supplier_id = supplier.json()["id"]

    ingredient = client.post(
        "/api/v1/inventory/ingredients",
        json={
            "name": "Counted Item",
            "unit": "kg",
            "current_stock": 25,
            "minimum_stock": 5,
            "supplier_id": supplier_id,
        },
        headers=owner,
    )
    ingredient_id = ingredient.json()["id"]

    # Create stock count
    count = client.post(
        "/api/v1/inventory/stock-counts",
        json={
            "branch_id": branch["id"],
            "items": [
                {
                    "ingredient_id": ingredient_id,
                    "expected_qty": 25,
                    "counted_qty": 22,
                }
            ],
            "notes": "Monthly inventory count",
        },
        headers=owner,
    )
    assert count.status_code == 201, count.text
    count_id = count.json()["id"]
    assert count.json()["status"] == "DRAFT"
    assert count.json()["items"][0]["variance_qty"] == -3

    # Complete stock count
    completed = client.post(
        f"/api/v1/inventory/stock-counts/{count_id}/complete", headers=owner
    )
    assert completed.status_code == 200
    assert completed.json()["status"] == "COMPLETED"

    # Verify ingredient stock was adjusted
    fetched = client.get(
        f"/api/v1/inventory/ingredients/{ingredient_id}", headers=owner
    )
    assert fetched.json()["current_stock"] == 22


def test_payment_methods_crud(client: TestClient, owner: dict) -> None:
    # Create payment method - uses label, kind (CASH/QR)
    # Note: endpoint returns 200 not 201
    created = client.post(
        "/api/v1/payment-methods",
        json={
            "label": "Test Card",
            "kind": "CASH",
            "is_active": True,
            "display_order": 1,
        },
        headers=owner,
    )
    assert created.status_code == 200, created.text
    method_id = created.json()["id"]
    assert created.json()["label"] == "Test Card"
    assert created.json()["kind"] == "CASH"
    assert created.json()["is_active"] is True

    # List payment methods
    listed = client.get("/api/v1/payment-methods", headers=owner)
    assert listed.status_code == 200
    assert any(m["id"] == method_id for m in listed.json())

    # Update payment method
    updated = client.patch(
        f"/api/v1/payment-methods/{method_id}",
        json={"label": "Updated Card", "is_active": False},
        headers=owner,
    )
    assert updated.status_code == 200
    assert updated.json()["label"] == "Updated Card"
    assert updated.json()["is_active"] is False

    # Delete payment method
    deleted = client.delete(f"/api/v1/payment-methods/{method_id}", headers=owner)
    assert deleted.status_code == 204

    # Verify deletion
    listed = client.get("/api/v1/payment-methods", headers=owner)
    assert not any(m["id"] == method_id for m in listed.json())


def test_payment_methods_qr_image(client: TestClient, owner: dict) -> None:
    # Create payment method with QR - endpoint returns 200
    created = client.post(
        "/api/v1/payment-methods",
        json={
            "label": "QR Payment",
            "kind": "QR",
            "is_active": True,
        },
        headers=owner,
    )
    assert created.status_code == 200
    method_id = created.json()["id"]

    # Upload QR image (create a minimal PNG)
    import base64
    png_data = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
    )
    upload = client.post(
        f"/api/v1/payment-methods/{method_id}/qr-image",
        files={"image": ("test.png", png_data, "image/png")},
        headers=owner,
    )
    assert upload.status_code == 200
    assert upload.json()["qr_image_url"] is not None

    # Download QR image
    download = client.get(
        f"/api/v1/payment-methods/{method_id}/qr-image", headers=owner
    )
    assert download.status_code == 200


def test_reports_advanced(client: TestClient, owner: dict, branch: dict) -> None:
    # Place an order first to have data
    qr = DEMO_QR_TOKENS["T1"]
    menu = client.get(f"/api/v1/public/qr/{qr}/menu")
    item_id = menu.json()["categories"][0]["items"][0]["id"]
    client.post(
        f"/api/v1/public/qr/{qr}/orders",
        json={"items": [{"menu_item_id": item_id, "quantity": 1}]},
        headers={"Idempotency-Key": "adv-report-order-1"},
    )

    report = client.get("/api/v1/reports/advanced?days=7", headers=owner)
    assert report.status_code == 200
    body = report.json()
    assert body["window_days"] == 7
    assert "sales" in body
    assert "average_order_minor" in body
    assert "daily" in body
    assert isinstance(body["daily"], list)


def test_reports_payments(client: TestClient, owner: dict, branch: dict) -> None:
    # Create payment method with unique label (Cash already exists from seed)
    method = client.post(
        "/api/v1/payment-methods",
        json={"label": "Test Cash", "kind": "CASH", "is_active": True},
        headers=owner,
    )
    assert method.status_code == 200, method.text
    method_id = method.json()["id"]

    # Place an order and pay
    qr = DEMO_QR_TOKENS["T1"]
    menu = client.get(f"/api/v1/public/qr/{qr}/menu")
    item_id = menu.json()["categories"][0]["items"][0]["id"]
    order = client.post(
        f"/api/v1/public/qr/{qr}/orders",
        json={"items": [{"menu_item_id": item_id, "quantity": 1}]},
        headers={"Idempotency-Key": "pay-report-order-1"},
    )
    order_id = order.json()["order"]["id"]

    # Accept order (creates dining session)
    accepted = client.post(f"/api/v1/orders/{order_id}/accept", headers=owner)
    session_id = accepted.json()["dining_session_id"]

    # Issue bill
    bill = client.post(
        f"/api/v1/sessions/{session_id}/bill/issue", headers=owner
    )
    bill_id = bill.json()["id"]

    # Record payment
    client.post(
        f"/api/v1/bills/{bill_id}/payments",
        json={"method_id": method_id, "amount_minor": 1500},
        headers=owner,
    )

    # Test payments report
    report = client.get("/api/v1/reports/payments?days=7", headers=owner)
    assert report.status_code == 200
    body = report.json()
    assert body["window_days"] == 7
    assert "methods" in body
    assert isinstance(body["methods"], list)
    assert "total_collected_minor" in body


def test_reports_kitchen_speed(client: TestClient, owner: dict, branch: dict) -> None:
    # Place and accept an order to generate kitchen tickets
    qr = DEMO_QR_TOKENS["T1"]
    menu = client.get(f"/api/v1/public/qr/{qr}/menu")
    item_id = menu.json()["categories"][0]["items"][0]["id"]
    order = client.post(
        f"/api/v1/public/qr/{qr}/orders",
        json={"items": [{"menu_item_id": item_id, "quantity": 1}]},
        headers={"Idempotency-Key": "kitchen-report-order-1"},
    )
    order_id = order.json()["order"]["id"]

    # Accept order
    client.post(f"/api/v1/orders/{order_id}/accept", headers=owner)

    # Claim and complete (kitchen)
    client.post(f"/api/v1/orders/{order_id}/claim", headers=owner)

    report = client.get("/api/v1/reports/kitchen-speed?days=7", headers=owner)
    assert report.status_code == 200
    body = report.json()
    assert body["window_days"] == 7
    assert "completed_ticket_count" in body
    assert "avg_prep_seconds" in body
    assert "slowest_tickets" in body
    assert isinstance(body["slowest_tickets"], list)


def test_audit_events(client: TestClient, owner: dict) -> None:
    # Perform some audited actions first - create payment method (audited)
    # Note: endpoint returns 200 not 201
    created = client.post(
        "/api/v1/payment-methods",
        json={"label": "Audit Test", "kind": "CASH", "is_active": True},
        headers=owner,
    )
    assert created.status_code == 200

    # Claim an order (also audited)
    qr = DEMO_QR_TOKENS["T1"]
    menu = client.get(f"/api/v1/public/qr/{qr}/menu")
    item_id = menu.json()["categories"][0]["items"][0]["id"]
    order = client.post(
        f"/api/v1/public/qr/{qr}/orders",
        json={"items": [{"menu_item_id": item_id, "quantity": 1}]},
        headers={"Idempotency-Key": "audit-test-order"},
    )
    order_id = order.json()["order"]["id"]
    client.post(f"/api/v1/orders/{order_id}/accept", headers=owner)
    client.post(f"/api/v1/orders/{order_id}/claim", headers=owner)

    report = client.get("/api/v1/audit-events", headers=owner)
    assert report.status_code == 200
    body = report.json()
    assert isinstance(body, list)
    assert len(body) >= 1
    # Should have audit events for payment method creation and order claim
    entity_types = {e["entity_type"] for e in body}
    assert "payment_method" in entity_types or "order" in entity_types


def test_orders_claim_escalate_integration(
    client: TestClient, owner: dict, waiter: dict, branch: dict
) -> None:
    # Place order via QR
    qr = DEMO_QR_TOKENS["T1"]
    menu = client.get(f"/api/v1/public/qr/{qr}/menu")
    item_id = menu.json()["categories"][0]["items"][0]["id"]
    order = client.post(
        f"/api/v1/public/qr/{qr}/orders",
        json={"items": [{"menu_item_id": item_id, "quantity": 1}]},
        headers={"Idempotency-Key": "claim-escalate-order-1"},
    )
    assert order.status_code == 200
    order_id = order.json()["order"]["id"]

    # Waiter claims order
    claim = client.post(f"/api/v1/orders/{order_id}/claim", headers=waiter)
    assert claim.status_code == 200
    assert claim.json()["claim_state"] == "CLAIMED"
    assert claim.json()["claimed_by_membership_id"] is not None
    assert claim.json()["claim_timeout_at"] is not None

    # Waiter escalates order
    escalate = client.post(
        f"/api/v1/orders/{order_id}/escalate",
        json={"note": "Customer has allergy questions"},
        headers=waiter,
    )
    assert escalate.status_code == 200
    assert escalate.json()["claim_state"] == "ESCALATED"
    assert escalate.json()["escalated_by_membership_id"] is not None
    assert escalate.json()["escalated_at"] is not None


def test_stock_count_permissions(
    client: TestClient, owner: dict, waiter: dict, branch: dict
) -> None:
    # Waiter does NOT have inventory.read permission
    # Owner can list
    listed = client.get("/api/v1/inventory/stock-counts", headers=owner)
    assert listed.status_code == 200

    # Waiter cannot list (no inventory.read)
    forbidden = client.get("/api/v1/inventory/stock-counts", headers=waiter)
    assert forbidden.status_code == 403

    # Waiter cannot create (no inventory.manage)
    supplier = client.post(
        "/api/v1/inventory/suppliers",
        json={"name": "Perm Supplier", "email": "perm@supplier.com"},
        headers=owner,
    )
    supplier_id = supplier.json()["id"]

    ingredient = client.post(
        "/api/v1/inventory/ingredients",
        json={
            "name": "Perm Item",
            "unit": "kg",
            "current_stock": 10,
            "minimum_stock": 2,
            "supplier_id": supplier_id,
        },
        headers=owner,
    )
    ingredient_id = ingredient.json()["id"]

    forbidden = client.post(
        "/api/v1/inventory/stock-counts",
        json={
            "branch_id": branch["id"],
            "items": [{"ingredient_id": ingredient_id, "expected_qty": 10, "counted_qty": 8}],
        },
        headers=waiter,
    )
    assert forbidden.status_code == 403


def test_payment_methods_permissions(
    client: TestClient, owner: dict, waiter: dict
) -> None:
    # Owner can create (settings.manage) - returns 200
    created = client.post(
        "/api/v1/payment-methods",
        json={"label": "Owner Method", "kind": "CASH", "is_active": True},
        headers=owner,
    )
    assert created.status_code == 200
    method_id = created.json()["id"]

    # Waiter can list (no permission required for list - uses get_actor)
    listed = client.get("/api/v1/payment-methods", headers=waiter)
    assert listed.status_code == 200

    # Waiter cannot create (no settings.manage)
    forbidden = client.post(
        "/api/v1/payment-methods",
        json={"label": "Waiter Method", "kind": "CASH", "is_active": True},
        headers=waiter,
    )
    assert forbidden.status_code == 403

    # Waiter cannot update
    forbidden = client.patch(
        f"/api/v1/payment-methods/{method_id}",
        json={"label": "Hacked"},
        headers=waiter,
    )
    assert forbidden.status_code == 403

    # Waiter cannot delete
    forbidden = client.delete(
        f"/api/v1/payment-methods/{method_id}", headers=waiter
    )
    assert forbidden.status_code == 403


def test_reports_permissions(
    client: TestClient, owner: dict, manager: dict, waiter: dict
) -> None:
    # Owner can access all reports (has all permissions)
    for endpoint in [
        "/api/v1/reports/sales",
        "/api/v1/reports/advanced?days=7",
        "/api/v1/reports/payments?days=7",
        "/api/v1/reports/kitchen-speed?days=7",
        "/api/v1/audit-events",
    ]:
        response = client.get(endpoint, headers=owner)
        assert response.status_code == 200, f"{endpoint}: {response.text}"

    # Manager has reports.read - can access all except audit (needs audit.read)
    for endpoint in [
        "/api/v1/reports/sales",
        "/api/v1/reports/advanced?days=7",
        "/api/v1/reports/payments?days=7",
        "/api/v1/reports/kitchen-speed?days=7",
    ]:
        response = client.get(endpoint, headers=manager)
        assert response.status_code == 200, f"{endpoint}: {response.text}"

    # Manager cannot access audit-events (no audit.read)
    assert client.get("/api/v1/audit-events", headers=manager).status_code == 403

    # Waiter does NOT have reports.read - only orders/kitchen/tables
    for endpoint in [
        "/api/v1/reports/sales",
        "/api/v1/reports/advanced?days=7",
        "/api/v1/reports/payments?days=7",
        "/api/v1/reports/kitchen-speed?days=7",
        "/api/v1/audit-events",
    ]:
        response = client.get(endpoint, headers=waiter)
        assert response.status_code == 403, f"{endpoint}: {response.text}"


def test_cashier_reports_permissions(
    client: TestClient, cashier: dict
) -> None:
    # Cashier has reports.read - can access sales, payments, kitchen-speed
    # In demo mode, tenant features are not enforced (entitlements is None), 
    # so advanced_reports is also accessible
    assert client.get("/api/v1/reports/sales", headers=cashier).status_code == 200
    assert client.get("/api/v1/reports/payments?days=7", headers=cashier).status_code == 200
    assert client.get("/api/v1/reports/kitchen-speed?days=7", headers=cashier).status_code == 200
    assert client.get("/api/v1/reports/advanced?days=7", headers=cashier).status_code == 200
    
    # But cashier cannot access audit (no audit.read)
    assert client.get("/api/v1/audit-events", headers=cashier).status_code == 403