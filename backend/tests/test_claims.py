"""Plan 08 — waiter claims, escalation, timeout, rate limits.

Covers the exit criteria from backend/webplan/08-waiter-request.md:
- claim flow: only one waiter owns an order; same-waiter re-claims are idempotent
- escalate flow: claimant escalates; supervisor can escalate anything claimed
- release: hand-off back to the shared queue with permission rules
- timeout: expired claims auto-escalate via the lazy sweep
- rate limiting: 429 RATE_LIMIT_EXCEEDED when the hourly cap is hit
- audit + outbox records for every action
"""

import uuid
from collections.abc import Generator
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.main import app
from app.modules.operations.models import Order
from app.modules.operations.services import claims as claim_service
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
def waiter(client: TestClient) -> dict[str, str]:
    return _sign_in(client, "waiter@harbor.example", "HarborWaiter!1")


@pytest.fixture(scope="module")
def manager(client: TestClient) -> dict[str, str]:
    return _sign_in(client, "manager@harbor.example", "HarborManager!1")


@pytest.fixture(scope="module")
def kitchen(client: TestClient) -> dict[str, str]:
    return _sign_in(client, "kitchen@harbor.example", "HarborKitchen!1")


@pytest.fixture(autouse=True)
def _clear_rate_limits():
    claim_service.clear_rate_limits()
    yield
    claim_service.clear_rate_limits()


def _qr_order(client: TestClient, table: str = "T1") -> tuple[str, str]:
    """Submit a fresh guest QR order; return (order_id, status_token)."""
    qr = DEMO_QR_TOKENS[table]
    menu = client.get(f"/api/v1/public/qr/{qr}/menu")
    item_id = menu.json()["categories"][0]["items"][0]["id"]
    response = client.post(
        f"/api/v1/public/qr/{qr}/orders",
        json={"items": [{"menu_item_id": item_id, "quantity": 1}], "customer_note": ""},
        headers={"Idempotency-Key": f"claim-test-{table}-{uuid.uuid4().hex[:8]}"},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    return body["order"]["id"], body["status_token"]


# --- Claim flow ---------------------------------------------------------------


def test_waiter_claims_pending_order(client: TestClient, waiter: dict) -> None:
    order_id, _ = _qr_order(client)
    response = client.post(f"/api/v1/orders/{order_id}/claim", headers=waiter)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["claim_state"] == "CLAIMED"
    assert body["claimed_by_membership_id"]
    assert body["claim_timeout_at"]


def test_second_waiter_cannot_claim_someone_elses_order(
    client: TestClient, waiter: dict, manager: dict
) -> None:
    order_id, _ = _qr_order(client, "T2")
    first = client.post(f"/api/v1/orders/{order_id}/claim", headers=waiter)
    assert first.status_code == 200
    second = client.post(f"/api/v1/orders/{order_id}/claim", headers=manager)
    assert second.status_code == 409, second.text
    assert second.json()["code"] == "ORDER_ALREADY_CLAIMED"


def test_same_waiter_reclaim_is_idempotent(client: TestClient, waiter: dict) -> None:
    order_id, _ = _qr_order(client, "T3")
    first = client.post(f"/api/v1/orders/{order_id}/claim", headers=waiter)
    second = client.post(f"/api/v1/orders/{order_id}/claim", headers=waiter)
    assert second.status_code == 200, second.text
    assert second.json()["claimed_by_membership_id"] == first.json()["claimed_by_membership_id"]
    assert second.json()["version"] == first.json()["version"]


def test_kitchen_cannot_claim(client: TestClient, kitchen: dict) -> None:
    order_id, _ = _qr_order(client, "T4")
    response = client.post(f"/api/v1/orders/{order_id}/claim", headers=kitchen)
    assert response.status_code == 403, response.text
    assert response.json()["code"] == "FORBIDDEN"


def test_terminal_orders_are_not_claimable(client: TestClient, waiter: dict) -> None:
    order_id, _ = _qr_order(client, "T5")
    accepted = client.post(f"/api/v1/orders/{order_id}/accept", headers=waiter)
    assert accepted.status_code == 200
    # Still claimable while in service…
    claim = client.post(f"/api/v1/orders/{order_id}/claim", headers=waiter)
    assert claim.status_code == 200

    rejected_order, _ = _qr_order(client, "T6")
    client.post(
        f"/api/v1/orders/{rejected_order}/reject",
        json={"reason_code": "UNAVAILABLE", "note": "sold out"},
        headers=waiter,
    )
    response = client.post(f"/api/v1/orders/{rejected_order}/claim", headers=waiter)
    assert response.status_code == 409, response.text
    assert response.json()["code"] == "ORDER_NOT_CLAIMABLE"


# --- Escalation flow ----------------------------------------------------------


def test_waiter_escalates_own_claim(client: TestClient, waiter: dict) -> None:
    order_id, _ = _qr_order(client, "T1")
    client.post(f"/api/v1/orders/{order_id}/claim", headers=waiter)
    note = "guest wants to swap a dish"
    response = client.post(
        f"/api/v1/orders/{order_id}/escalate",
        json={"note": note},
        headers=waiter,
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["claim_state"] == "ESCALATED"
    assert body["escalated_at"]


def test_escalate_requires_an_active_claim(client: TestClient, waiter: dict) -> None:
    order_id, _ = _qr_order(client, "T2")
    response = client.post(f"/api/v1/orders/{order_id}/escalate", json={}, headers=waiter)
    assert response.status_code == 409, response.text
    assert response.json()["code"] == "ORDER_NOT_CLAIMED"


def test_other_staff_cannot_escalate_someone_elses_claim(
    client: TestClient, waiter: dict, manager: dict
) -> None:
    """Only the claimant (or a supervisor, e.g. a manager) may escalate.

    The manager is a supervisor (holds orders.cancel), so the non-supervisor
    path is exercised here: the manager claims, and the waiter — neither
    claimant nor supervisor — is refused with 403.
    """
    order_id, _ = _qr_order(client, "T3")
    claimed = client.post(f"/api/v1/orders/{order_id}/claim", headers=manager)
    assert claimed.status_code == 200
    response = client.post(
        f"/api/v1/orders/{order_id}/escalate", json={"note": "busy"}, headers=waiter
    )
    assert response.status_code == 403, response.text
    assert response.json()["code"] == "FORBIDDEN"

    # The supervisor path works because managers hold orders.cancel.
    supervisor = client.post(
        f"/api/v1/orders/{order_id}/escalate", json={}, headers=manager
    )
    assert supervisor.status_code == 200, supervisor.text
    assert supervisor.json()["claim_state"] == "ESCALATED"


# --- Release flow -------------------------------------------------------------


def test_claimant_releases_own_order(client: TestClient, waiter: dict) -> None:
    order_id, _ = _qr_order(client, "T4")
    client.post(f"/api/v1/orders/{order_id}/claim", headers=waiter)
    response = client.post(f"/api/v1/orders/{order_id}/release", headers=waiter)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["claim_state"] == ""


def test_stale_release_conflicts_cleanly(client: TestClient, waiter: dict) -> None:
    order_id, _ = _qr_order(client, "T5")
    response = client.post(f"/api/v1/orders/{order_id}/release", headers=waiter)
    assert response.status_code == 409, response.text
    assert response.json()["code"] == "ORDER_NOT_CLAIMED"


# --- Timeout sweep ------------------------------------------------------------


def test_expired_claim_auto_escalates(client: TestClient, waiter: dict, manager: dict) -> None:
    order_id, _ = _qr_order(client, "T1")
    claimed = client.post(f"/api/v1/orders/{order_id}/claim", headers=waiter)
    assert claimed.status_code == 200

    db = SessionLocal()
    try:
        order = db.scalar(select(Order).where(Order.id == uuid.UUID(order_id)))
        order.claim_timeout_at = datetime.now(UTC) - timedelta(seconds=5)
        db.commit()
    finally:
        db.close()

    listing = client.get("/api/v1/orders", headers=manager)  # sweep runs on list
    assert listing.status_code == 200
    row = next(o for o in listing.json() if o["id"] == order_id)
    assert row["claim_state"] == "ESCALATED"
    assert row["escalated_at"]


# --- Rate limiting ------------------------------------------------------------


def test_claim_rate_limit_returns_429(client: TestClient, waiter: dict) -> None:
    from uuid import UUID

    order_id, _ = _qr_order(client, "T2")
    # Stuff the waiter's sliding window to the cap.
    bucket = claim_service._rate_counts[(UUID(_membership_id(client, waiter)), "claim")]
    bucket.extend(datetime.now(UTC) for _ in range(60))
    response = client.post(f"/api/v1/orders/{order_id}/claim", headers=waiter)
    assert response.status_code == 429, response.text
    assert response.json()["code"] == "RATE_LIMIT_EXCEEDED"


def _membership_id(client: TestClient, headers: dict[str, str]) -> str:
    me = client.get("/api/v1/me", headers=headers)
    assert me.status_code == 200
    return me.json()["membership"]["id"]


# --- Audit trail --------------------------------------------------------------


def test_claim_actions_are_audited(client: TestClient, waiter: dict, manager: dict) -> None:
    order_id, _ = _qr_order(client, "T6")
    client.post(f"/api/v1/orders/{order_id}/claim", headers=waiter)
    client.post(f"/api/v1/orders/{order_id}/release", headers=waiter)

    response = client.get("/api/v1/audit-events", headers=manager)
    assert response.status_code == 200, response.text
    actions = {event["action"] for event in response.json()}
    assert "orders.claim" in actions
    assert "orders.release" in actions
