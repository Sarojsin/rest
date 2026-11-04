"""End-to-end API coverage for phases 11-16 (branches, inventory, staff,
loyalty, reviews, subscriptions).

These tests boot the real app against the configured database and exercise the
new endpoints the way the web client does: authenticate, mutate, read back.
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
def waiter(client: TestClient) -> dict:
    return _auth(client, "waiter@harbor.example", "HarborWaiter!1")


@pytest.fixture(scope="module")
def branch(client: TestClient, owner: dict) -> dict:
    response = client.post(
        "/api/v1/branches",
        json={"name": "Downtown", "code": "DT", "address": "1 Main St"},
        headers=owner,
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_branch_crud_and_tables(client: TestClient, owner: dict, branch: dict) -> None:
    listed = client.get("/api/v1/branches", headers=owner)
    assert listed.status_code == 200
    assert any(b["id"] == branch["id"] for b in listed.json())

    fetched = client.get(f"/api/v1/branches/{branch['id']}", headers=owner)
    assert fetched.status_code == 200
    assert fetched.json()["restaurant_name"]

    patched = client.patch(
        f"/api/v1/branches/{branch['id']}",
        json={"phone": "+1-555-0100"},
        headers=owner,
    )
    assert patched.status_code == 200
    assert patched.json()["phone"] == "+1-555-0100"

    table = client.post(
        f"/api/v1/branches/{branch['id']}/tables",
        json={"table_code": "T1", "display_name": "Window", "seating_capacity": 4},
        headers=owner,
    )
    assert table.status_code == 201, table.text

    tables = client.get(f"/api/v1/branches/{branch['id']}/tables", headers=owner)
    assert tables.status_code == 200
    assert [t["table_code"] for t in tables.json()] == ["T1"]


def test_branch_reports_and_dashboards(
    client: TestClient, owner: dict, branch: dict
) -> None:
    report = client.post(
        f"/api/v1/branches/{branch['id']}/reports/sales",
        json={
            "total_sales_minor": 12345,
            "total_orders": 3,
            "total_orders_completed": 2,
            "total_orders_pending": 1,
        },
        headers=owner,
    )
    assert report.status_code == 201, report.text
    body = report.json()
    assert body["total_sales_minor"] == 12345
    assert body["total_sales_display"] == "123.45"

    generated = client.post(
        f"/api/v1/branches/{branch['id']}/reports/sales/generate", headers=owner
    )
    assert generated.status_code == 200, generated.text

    history = client.get(
        f"/api/v1/branches/{branch['id']}/reports/sales", headers=owner
    )
    assert history.status_code == 200
    assert len(history.json()) >= 2

    dashboard = client.get(
        f"/api/v1/branches/{branch['id']}/dashboard", headers=owner
    )
    assert dashboard.status_code == 200
    assert dashboard.json()["active_tables"] == 1

    rolled_up = client.get("/api/v1/branches/dashboard/owner", headers=owner)
    assert rolled_up.status_code == 200
    assert rolled_up.json()["branch_count"] >= 1


def test_branch_manager_assignment(
    client: TestClient, owner: dict, branch: dict
) -> None:
    me = client.get("/api/v1/me", headers=owner).json()
    membership_id = me["membership"]["id"]
    assigned = client.post(
        f"/api/v1/branches/{branch['id']}/managers",
        json={"membership_id": membership_id},
        headers=owner,
    )
    assert assigned.status_code == 201, assigned.text

    listed = client.get(
        f"/api/v1/branches/{branch['id']}/managers", headers=owner
    )
    assert listed.status_code == 200
    assert len(listed.json()) == 1


def test_inventory_supplier_ingredient_stock(
    client: TestClient, owner: dict, waiter: dict
) -> None:
    supplier = client.post(
        "/api/v1/inventory/suppliers",
        json={"name": "Fresh Farms", "email": "orders@fresh.example"},
        headers=owner,
    )
    assert supplier.status_code == 201, supplier.text
    supplier_id = supplier.json()["id"]

    ingredient = client.post(
        "/api/v1/inventory/ingredients",
        json={
            "name": "Tomato",
            "unit": "kg",
            "current_stock": 10,
            "minimum_stock": 5,
            "supplier_id": supplier_id,
        },
        headers=owner,
    )
    assert ingredient.status_code == 201, ingredient.text
    ingredient_id = ingredient.json()["id"]
    assert ingredient.json()["supplier_name"] == "Fresh Farms"
    assert ingredient.json()["status"] == "IN_STOCK"

    # Receiving stock keeps status in sync
    receive = client.post(
        "/api/v1/inventory/stock-movements",
        json={
            "ingredient_id": ingredient_id,
            "movement_type": "RECEIVE",
            "quantity": 5,
            "reason": "Delivery",
        },
        headers=owner,
    )
    assert receive.status_code == 201, receive.text
    assert receive.json()["new_balance"] == 15

    # Deducting below the threshold flips to LOW_STOCK
    deduct = client.post(
        "/api/v1/inventory/stock-movements",
        json={
            "ingredient_id": ingredient_id,
            "movement_type": "DEDUCT",
            "quantity": 12,
        },
        headers=owner,
    )
    assert deduct.status_code == 201, deduct.text
    assert deduct.json()["new_balance"] == 3

    fetched = client.get(
        f"/api/v1/inventory/ingredients/{ingredient_id}", headers=owner
    )
    assert fetched.status_code == 200
    assert fetched.json()["status"] == "LOW_STOCK"

    movements = client.get("/api/v1/inventory/stock-movements", headers=owner)
    assert movements.status_code == 200
    assert len(movements.json()) >= 2

    # Waiters can read but not manage inventory
    assert client.get("/api/v1/inventory/ingredients", headers=waiter).status_code == 200
    forbidden = client.post(
        "/api/v1/inventory/ingredients",
        json={"name": "Basil"},
        headers=waiter,
    )
    assert forbidden.status_code == 403


def test_inventory_purchase_order_and_recipe(
    client: TestClient, owner: dict
) -> None:
    supplier_id = client.get("/api/v1/inventory/suppliers", headers=owner).json()[0]["id"]
    ingredient_id = client.get(
        "/api/v1/inventory/ingredients", headers=owner
    ).json()[0]["id"]

    po = client.post(
        "/api/v1/inventory/purchase-orders",
        json={
            "code": "PO-1001",
            "supplier_id": supplier_id,
            "items": [
                {
                    "ingredient_id": ingredient_id,
                    "quantity": 4,
                    "unit_price_minor": 250,
                }
            ],
        },
        headers=owner,
    )
    assert po.status_code == 201, po.text
    po_id = po.json()["id"]
    assert po.json()["total_minor"] == 1000

    received = client.post(
        f"/api/v1/inventory/purchase-orders/{po_id}/receive", headers=owner
    )
    assert received.status_code == 200, received.text
    assert received.json()["status"] == "RECEIVED"

    menu = client.get("/api/v1/menu", headers=owner).json()
    menu_item_id = menu[0]["items"][0]["id"]

    recipe = client.put(
        f"/api/v1/inventory/recipes/{menu_item_id}",
        json={
            "items": [
                {"ingredient_id": ingredient_id, "quantity_per_serving": 2}
            ]
        },
        headers=owner,
    )
    assert recipe.status_code == 200, recipe.text
    assert recipe.json()[0]["ingredient_name"] == "Tomato"

    listed = client.get(
        f"/api/v1/inventory/recipes?menu_item_id={menu_item_id}", headers=owner
    )
    assert listed.status_code == 200
    assert len(listed.json()) == 1

    cost = client.get(f"/api/v1/inventory/recipes/{menu_item_id}/cost", headers=owner)
    assert cost.status_code == 200
    assert "total_cost_minor" in cost.json()


def test_employees_and_shifts(client: TestClient, owner: dict, branch: dict) -> None:
    created = client.post(
        "/api/v1/employees",
        json={
            "name": "Sam Rivera",
            "email": "sam@harbor.example",
            "phone": "+1-555-0111",
            "role": "waiter",
            "hire_date": "2026-01-15T00:00:00Z",
            "branch_id": branch["id"],
        },
        headers=owner,
    )
    assert created.status_code == 201, created.text
    employee_id = created.json()["id"]
    assert created.json()["branch_id"] == branch["id"]

    listed = client.get("/api/v1/employees", headers=owner)
    assert listed.status_code == 200
    assert any(e["id"] == employee_id for e in listed.json())

    patched = client.patch(
        f"/api/v1/employees/{employee_id}",
        json={"role": "senior waiter"},
        headers=owner,
    )
    assert patched.status_code == 200
    assert patched.json()["role"] == "senior waiter"

    shift = client.post(
        "/api/v1/employees/shifts",
        json={
            "employee_id": employee_id,
            "branch_id": branch["id"],
            "date": "2026-11-05",
            "start_time": "09:00",
            "end_time": "17:00",
        },
        headers=owner,
    )
    assert shift.status_code == 201, shift.text

    shifts = client.get("/api/v1/employees/shifts", headers=owner)
    assert shifts.status_code == 200
    assert len(shifts.json()) == 1

    # Duplicate shift on the same date is rejected
    duplicate = client.post(
        "/api/v1/employees/shifts",
        json={
            "employee_id": employee_id,
            "branch_id": branch["id"],
            "date": "2026-11-05",
            "start_time": "10:00",
            "end_time": "18:00",
        },
        headers=owner,
    )
    assert duplicate.status_code == 409


def _place_order(client: TestClient) -> tuple[str, str]:
    qr = DEMO_QR_TOKENS["T1"]
    menu = client.get(f"/api/v1/public/qr/{qr}/menu")
    item_id = menu.json()["categories"][0]["items"][0]["id"]
    submit = client.post(
        f"/api/v1/public/qr/{qr}/orders",
        json={"items": [{"menu_item_id": item_id, "quantity": 1}]},
        headers={"Idempotency-Key": "phase-loyalty-order-1"},
    )
    assert submit.status_code == 200, submit.text
    return submit.json()["order"]["id"], item_id


def test_loyalty_account_transactions_and_coupons(
    client: TestClient, owner: dict
) -> None:
    account = client.get("/api/v1/loyalty/account", headers=owner)
    assert account.status_code == 200, account.text
    assert account.json()["points_balance"] == 0

    earned = client.post(
        "/api/v1/loyalty/transactions",
        json={"type": "EARN", "points": 100, "reason": "Welcome bonus"},
        headers=owner,
    )
    assert earned.status_code == 201, earned.text

    account = client.get("/api/v1/loyalty/account", headers=owner).json()
    assert account["points_balance"] == 100
    assert account["total_earned"] == 100

    redeemed = client.post(
        "/api/v1/loyalty/transactions",
        json={"type": "REDEEM", "points": 40, "reason": "Free dessert"},
        headers=owner,
    )
    assert redeemed.status_code == 201, redeemed.text

    account = client.get("/api/v1/loyalty/account", headers=owner).json()
    assert account["points_balance"] == 60

    too_many = client.post(
        "/api/v1/loyalty/transactions",
        json={"type": "REDEEM", "points": 1000, "reason": "Too much"},
        headers=owner,
    )
    assert too_many.status_code == 422

    coupon = client.post(
        "/api/v1/loyalty/coupons",
        json={
            "code": "WELCOME10",
            "name": "Welcome 10%",
            "discount_type": "PERCENT",
            "discount_value": 10,
            "valid_from": "2026-01-01T00:00:00Z",
            "maximum_redeem_count": 5,
            "usage_limit_per_customer": 1,
        },
        headers=owner,
    )
    assert coupon.status_code == 201, coupon.text
    coupon_id = coupon.json()["id"]

    order_id, _ = _place_order(client)
    redemption = client.post(
        "/api/v1/loyalty/coupons/redeem",
        json={
            "coupon_id": coupon_id,
            "order_id": order_id,
            "discount_amount_minor": 500,
        },
        headers=owner,
    )
    assert redemption.status_code == 201, redemption.text

    # Per-customer limit is enforced
    second = client.post(
        "/api/v1/loyalty/coupons/redeem",
        json={
            "coupon_id": coupon_id,
            "order_id": order_id,
            "discount_amount_minor": 500,
        },
        headers=owner,
    )
    assert second.status_code == 422


def test_reviews_flow(client: TestClient, owner: dict) -> None:
    created = client.post(
        "/api/v1/reviews",
        json={"rating": 5, "title": "Great", "content": "Loved it"},
        headers=owner,
    )
    assert created.status_code == 201, created.text
    review_id = created.json()["id"]

    listed = client.get("/api/v1/reviews", headers=owner)
    assert listed.status_code == 200
    assert len(listed.json()) == 1

    summary = client.get("/api/v1/reviews/summary", headers=owner)
    assert summary.status_code == 200
    assert summary.json()["average_rating"] == 5.0

    responded = client.post(
        f"/api/v1/reviews/{review_id}/respond",
        json={"response_text": "Thank you for visiting!"},
        headers=owner,
    )
    assert responded.status_code == 200, responded.text
    assert responded.json()["response_text"] == "Thank you for visiting!"

    status = client.patch(
        f"/api/v1/reviews/{review_id}/status?status=APPROVED", headers=owner
    )
    assert status.status_code == 200
    assert status.json()["status"] == "APPROVED"


def test_subscription_flow(client: TestClient, owner: dict) -> None:
    plan = client.post(
        "/api/v1/subscriptions/plans",
        json={
            "name": "Professional",
            "price_minor": 7900,
            "billing_interval": "MONTHLY",
            "trial_days": 14,
            "features": "branches,inventory",
        },
        headers=owner,
    )
    assert plan.status_code == 201, plan.text
    plan_id = plan.json()["id"]

    plans = client.get("/api/v1/subscriptions/plans", headers=owner)
    assert plans.status_code == 200
    assert len(plans.json()) == 1

    subscription = client.post(
        "/api/v1/subscriptions/subscription",
        json={"plan_id": plan_id, "status": "TRIAL"},
        headers=owner,
    )
    assert subscription.status_code == 201, subscription.text
    subscription_id = subscription.json()["id"]
    assert subscription.json()["status"] == "TRIAL"

    current = client.get("/api/v1/subscriptions/subscription", headers=owner)
    assert current.status_code == 200
    assert current.json()["id"] == subscription_id

    billing = client.post(
        "/api/v1/subscriptions/billing",
        json={
            "subscription_id": subscription_id,
            "amount_minor": 7900,
            "billing_date": "2026-12-01T00:00:00Z",
        },
        headers=owner,
    )
    assert billing.status_code == 201, billing.text

    history = client.get("/api/v1/subscriptions/billing", headers=owner)
    assert history.status_code == 200
    assert len(history.json()) == 1

    canceled = client.patch(
        "/api/v1/subscriptions/subscription?cancel_at_period_end=true",
        headers=owner,
    )
    assert canceled.status_code == 200
    assert canceled.json()["cancel_at_period_end"] is True
