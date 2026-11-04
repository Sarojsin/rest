"""PA-0.11 — tenant suspension gate and in-flight allowlist (PA D-6).

The contract:

- a suspended/cancelled tenant cannot sign in, start a new session, or create a
  new order (staff or customer QR);
- work that demonstrably started before the suspension — an existing dining
  session, its bill, and its payment — still completes;
- the in-flight test is the session timestamp, never a broad string match.
"""

from __future__ import annotations

from collections.abc import Generator
from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.main import app
from app.modules.operations.models import DiningSession
from app.modules.tenancy.models import Restaurant
from app.modules.tenancy.services.tenant_lifecycle import (
    ensure_inflight_allowed,
    ensure_tenant_active,
)
from app.seed import DEMO_QR_TOKENS, seed_if_empty
from app.shared import tenant_access
from app.shared.errors import AppError

OWNER_EMAIL = "owner@harbor.example"
OWNER_PASSWORD = "HarborOwner!1"


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


@pytest.fixture()
def db() -> Generator[Session, None, None]:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def _login(client: TestClient) -> dict:
    response = client.post(
        "/api/v1/auth/login",
        json={"email": OWNER_EMAIL, "password": OWNER_PASSWORD},
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _restaurant(db: Session) -> Restaurant:
    restaurant = db.scalar(select(Restaurant).where(Restaurant.slug == "harbor-table"))
    assert restaurant is not None
    return restaurant


def _suspend(db: Session, *, at: datetime | None = None) -> None:
    restaurant = _restaurant(db)
    restaurant.status = "SUSPENDED"
    restaurant.suspended_at = at or datetime.now(UTC)
    restaurant.suspended_reason = "test suspension"
    db.commit()


def _reactivate(db: Session) -> None:
    restaurant = _restaurant(db)
    restaurant.status = "ACTIVE"
    restaurant.suspended_at = None
    restaurant.suspended_reason = None
    restaurant.archived_at = None
    db.commit()


@pytest.fixture()
def restored_tenant(db: Session) -> Generator[None, None, None]:
    try:
        yield
    finally:
        _reactivate(db)


def _table_id(client: TestClient, headers: dict) -> str:
    response = client.get("/api/v1/tables", headers=headers)
    assert response.status_code == 200, response.text
    return response.json()[0]["id"]


def _menu_item_id(client: TestClient, headers: dict) -> str:
    response = client.get("/api/v1/menu", headers=headers)
    assert response.status_code == 200, response.text
    return response.json()[0]["items"][0]["id"]


def _create_order(client: TestClient, headers: dict, table_id: str, item_id: str, key: str):
    return client.post(
        "/api/v1/orders",
        json={
            "table_id": table_id,
            "items": [{"menu_item_id": item_id, "quantity": 1}],
        },
        headers={**headers, "Idempotency-Key": key},
    )


def test_suspended_tenant_blocks_a_new_staff_order(
    client: TestClient, db: Session, restored_tenant: None
) -> None:
    headers = _login(client)
    table_id = _table_id(client, headers)
    item_id = _menu_item_id(client, headers)

    _suspend(db)

    response = _create_order(client, headers, table_id, item_id, "suspended-new-order")

    assert response.status_code == 403, response.text
    assert response.json()["code"] == "TENANT_SUSPENDED"


def test_suspended_tenant_blocks_a_new_customer_qr_order(
    client: TestClient, db: Session, restored_tenant: None
) -> None:
    qr = DEMO_QR_TOKENS["T1"]

    _suspend(db)

    response = client.post(
        f"/api/v1/public/qr/{qr}/orders",
        json={"items": [{"menu_item_id": str(UUID(int=0)), "quantity": 1}]},
        headers={"Idempotency-Key": "suspended-qr-order"},
    )

    assert response.status_code == 403, response.text
    assert response.json()["code"] == "TENANT_SUSPENDED"


def test_suspended_tenant_cannot_sign_in(
    client: TestClient, db: Session, restored_tenant: None
) -> None:
    _suspend(db)

    response = client.post(
        "/api/v1/auth/login",
        json={"email": OWNER_EMAIL, "password": OWNER_PASSWORD},
    )

    assert response.status_code == 403, response.text
    assert response.json()["code"] == "TENANT_SUSPENDED"


def test_inflight_session_can_be_billed_and_paid_after_suspension(
    client: TestClient, db: Session, restored_tenant: None
) -> None:
    headers = _login(client)
    table_id = _table_id(client, headers)
    item_id = _menu_item_id(client, headers)

    created = _create_order(client, headers, table_id, item_id, "inflight-order")
    assert created.status_code == 200, created.text
    session_id = created.json()["dining_session_id"]
    assert session_id

    # Suspend strictly after the session opened.
    _suspend(db)

    bill = client.post(f"/api/v1/sessions/{session_id}/bill/issue", headers=headers)
    assert bill.status_code == 200, bill.text
    bill_body = bill.json()
    assert bill_body["total_minor"] > 0

    methods = client.get("/api/v1/payment-methods", headers=headers)
    assert methods.status_code == 200, methods.text
    method_id = next(m["id"] for m in methods.json() if m["kind"] == "CASH")

    payment = client.post(
        f"/api/v1/bills/{bill_body['id']}/payments",
        json={
            "method_id": method_id,
            "amount_minor": bill_body["balance_due_minor"],
            "note": "in-flight settlement",
        },
        headers={**headers, "Idempotency-Key": "inflight-payment"},
    )
    assert payment.status_code == 200, payment.text
    assert payment.json()["status"] == "PAID"


def test_suspended_tenant_rejects_a_new_session(
    client: TestClient, db: Session, restored_tenant: None
) -> None:
    headers = _login(client)
    table_id = _table_id(client, headers)
    item_id = _menu_item_id(client, headers)

    _suspend(db)

    response = _create_order(client, headers, table_id, item_id, "suspended-new-session")

    assert response.status_code == 403
    session = db.scalar(
        select(DiningSession).where(DiningSession.table_id == UUID(table_id))
    )
    # A previous test may have opened this table's session; the point is that
    # no *new* session was created by the rejected request.
    if session is not None:
        assert tenant_access.started_before_suspension(
            started_at=session.opened_at,
            suspended_at=_restaurant(db).suspended_at,
        )


def test_cancelled_tenant_gets_no_inflight_grace(client: TestClient, db: Session) -> None:
    headers = _login(client)
    table_id = _table_id(client, headers)
    item_id = _menu_item_id(client, headers)

    created = _create_order(client, headers, table_id, item_id, "cancelled-order")
    assert created.status_code == 200, created.text
    session_id = created.json()["dining_session_id"]

    session = db.get(DiningSession, UUID(session_id))
    assert session is not None

    restaurant = _restaurant(db)
    restaurant.status = "CANCELLED"
    restaurant.suspended_at = datetime.now(UTC)
    db.commit()
    try:
        response = client.post(
            f"/api/v1/sessions/{session_id}/bill/issue", headers=headers
        )
        assert response.status_code == 403
        assert response.json()["code"] == "TENANT_SUSPENDED"
    finally:
        _reactivate(db)


def test_inflight_comparison_is_timestamp_based() -> None:
    suspended_at = datetime(2026, 11, 4, 12, 0, tzinfo=UTC)

    allowed = tenant_access.inflight_allowed(
        status="SUSPENDED",
        archived_at=None,
        suspended_at=suspended_at,
        started_at=suspended_at - timedelta(minutes=5),
    )
    blocked = tenant_access.inflight_allowed(
        status="SUSPENDED",
        archived_at=None,
        suspended_at=suspended_at,
        started_at=suspended_at + timedelta(seconds=1),
    )
    missing_start = tenant_access.inflight_allowed(
        status="SUSPENDED",
        archived_at=None,
        suspended_at=suspended_at,
        started_at=None,
    )

    assert allowed is True
    assert blocked is False
    assert missing_start is False


def test_archived_tenant_is_never_active() -> None:
    with pytest.raises(AppError) as excinfo:
        tenant_access.ensure_tenant_active(
            status="ACTIVE", archived_at=datetime.now(UTC)
        )
    assert excinfo.value.code == "TENANT_SUSPENDED"

    # The tenancy wrapper agrees for an ORM object.
    restaurant = Restaurant(
        name="Archived",
        slug="archived",
        status="ACTIVE",
        timezone="UTC",
        currency_code="USD",
        archived_at=datetime.now(UTC),
    )
    with pytest.raises(AppError):
        ensure_tenant_active(restaurant)
    with pytest.raises(AppError):
        ensure_inflight_allowed(restaurant, datetime.now(UTC))
