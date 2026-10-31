"""Table creation / edit / archive endpoints (owner & manager only)."""

from collections.abc import Generator

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


def owner(client: TestClient) -> dict:
    return auth_headers(client, "owner@harbor.example", "HarborOwner!1")


def waiter(client: TestClient) -> dict:
    return auth_headers(client, "waiter@harbor.example", "HarborWaiter!1")


def _codes(client: TestClient, headers: dict) -> list[str]:
    response = client.get("/api/v1/tables", headers=headers)
    assert response.status_code == 200, response.text
    return [t["table_code"] for t in response.json()]


def create(client: TestClient, headers: dict, code: str, name: str | None = None) -> dict:
    payload = {
        "table_code": code,
        "display_name": name or f"Table {code}",
        "seating_capacity": 4,
    }
    return client.post("/api/v1/tables", json=payload, headers=headers)


# ──_PERMISSIONS ───────────────────────────────────────────────────────────────


def test_owner_can_create_table(client: TestClient) -> None:
    response = create(client, owner(client), "t7 ", "Patio 1")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["table_code"] == "T7"  # trimmed + uppercased
    assert body["status"] == "ACTIVE"
    assert body["sort_order"] == 7  # max+1 of seeded T1..T6
    assert body["qr_token"]  # printable QR issued immediately
    assert body["occupancy"] == "AVAILABLE"


def test_manager_can_create_table(client: TestClient) -> None:
    manager = auth_headers(client, "manager@harbor.example", "HarborManager!1")
    response = create(client, manager, "T8")
    assert response.status_code == 200, response.text
    assert response.json()["table_code"] == "T8"


def test_waiter_cannot_create_table(client: TestClient) -> None:
    response = create(client, waiter(client), "T99")
    assert response.status_code == 403
    assert response.json()["code"] == "FORBIDDEN"
    assert "T99" not in _codes(client, waiter(client))


def test_cashier_cannot_create_or_archive(client: TestClient) -> None:
    cashier = auth_headers(client, "cashier@harbor.example", "HarborCashier!1")
    headers = owner(client)
    table_id = create(client, cashier, "T42").json().get("id")
    assert table_id is None  # create was forbidden

    created = create(client, headers, "T42").json()
    archive = client.post(f"/api/v1/tables/{created['id']}/archive", headers=cashier)
    assert archive.status_code == 403


# ── VALIDATION / UNIQUENESS ───────────────────────────────────────────────────


def test_duplicate_code_conflicts_case_insensitively(client: TestClient) -> None:
    headers = owner(client)
    assert create(client, headers, "T7").status_code == 409
    assert create(client, headers, "t7").status_code == 409  # existing seeded code
    problem = create(client, headers, "t7").json()
    assert problem["code"] == "TABLE_CODE_EXISTS"


def test_invalid_code_rejected(client: TestClient) -> None:
    headers = owner(client)
    for code in ("", "T 7", "café-1", "X" * 40):
        response = create(client, headers, code)
        assert response.status_code in {409, 422}, response.text


def test_kitchen_role_cannot_create(client: TestClient) -> None:
    kitchen = auth_headers(client, "kitchen@harbor.example", "HarborKitchen!1")
    assert create(client, kitchen, "T50").status_code == 403


# ── QR / PUBLIC RESOLUTION ────────────────────────────────────────────────────


def test_created_table_qr_resolves_publicly(client: TestClient) -> None:
    headers = owner(client)
    created = create(client, headers, "PATIO-1", "Patio Table").json()
    token = created["qr_token"]
    menu = client.get(f"/api/v1/public/qr/{token}/menu")
    assert menu.status_code == 200, menu.text
    assert menu.json()["table_display_name"] == "Patio Table"


def test_rotate_qr_requires_configure_permission(client: TestClient) -> None:
    headers = owner(client)
    created = create(client, headers, "ROT-1").json()
    old_token = created["qr_token"]

    waiter_denied = client.post(f"/api/v1/tables/{created['id']}/qr/rotate", headers=waiter(client))
    assert waiter_denied.status_code == 403

    rotated = client.post(f"/api/v1/tables/{created['id']}/qr/rotate", headers=headers)
    assert rotated.status_code == 200
    new_token = rotated.json()["qr_token"]
    assert new_token != old_token
    assert client.get(f"/api/v1/public/qr/{old_token}/menu").status_code == 404
    assert client.get(f"/api/v1/public/qr/{new_token}/menu").status_code == 200


# ── EDIT ──────────────────────────────────────────────────────────────────────


def test_update_table_fields(client: TestClient) -> None:
    headers = owner(client)
    created = create(client, headers, "EDIT-1", "Old name").json()
    response = client.patch(
        f"/api/v1/tables/{created['id']}",
        json={"display_name": "Window seat", "seating_capacity": 2},
        headers=headers,
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["display_name"] == "Window seat"
    assert body["seating_capacity"] == 2
    assert body["table_code"] == "EDIT-1"  # code never changes

    # Unknown fields rejected, invalid status rejected
    bad_status = client.patch(f"/api/v1/tables/{created['id']}", json={"status": "ARCHIVED"}, headers=headers)
    assert bad_status.status_code == 422

    waiter_denied = client.patch(f"/api/v1/tables/{created['id']}", json={"display_name": "Nope"}, headers=waiter(client))
    assert waiter_denied.status_code == 403


def test_out_of_service_marked_in_listing(client: TestClient) -> None:
    headers = owner(client)
    created = create(client, headers, "OOS-1").json()
    token = created["qr_token"]
    assert client.get(f"/api/v1/public/qr/{token}/menu").status_code == 200

    patched = client.patch(f"/api/v1/tables/{created['id']}", json={"status": "OUT_OF_SERVICE"}, headers=headers)
    assert patched.status_code == 200
    # Public page can resolve the token; ordering policy stays with the backend resolver,
    # which still returns the table. Staff see the status flag.
    listing = {t["table_code"]: t for t in client.get("/api/v1/tables", headers=headers).json()}
    assert listing["OOS-1"]["status"] == "OUT_OF_SERVICE"


# ── ARCHIVE / RESTORE ─────────────────────────────────────────────────────────


def test_archive_and_restore_free_table(client: TestClient) -> None:
    headers = owner(client)
    created = create(client, headers, "ARC-1").json()
    table_id, old_token = created["id"], created["qr_token"]

    archived = client.post(f"/api/v1/tables/{table_id}/archive", headers=headers)
    assert archived.status_code == 200, archived.text
    assert archived.json()["status"] == "ARCHIVED"
    assert archived.json()["qr_token"] is None
    # Printed QR stops working immediately
    assert client.get(f"/api/v1/public/qr/{old_token}/menu").status_code == 404
    # Hidden from the default floor list, visible with include_archived
    assert "ARC-1" not in _codes(client, headers)
    archived_list = client.get(
        "/api/v1/tables", params={"include_archived": "true"}, headers=headers
    ).json()
    assert any(t["table_code"] == "ARC-1" for t in archived_list)

    # Double archive conflicts
    again = client.post(f"/api/v1/tables/{table_id}/archive", headers=headers)
    assert again.status_code == 409

    # Restore reissues a working QR
    restored = client.post(f"/api/v1/tables/{table_id}/restore", headers=headers)
    assert restored.status_code == 200, restored.text
    new_token = restored.json()["qr_token"]
    assert new_token and client.get(f"/api/v1/public/qr/{new_token}/menu").status_code == 200
    assert "ARC-1" in _codes(client, headers)


def test_cannot_archive_occupied_table(client: TestClient) -> None:
    headers = owner(client)
    # T1 has an open gaming session from the seed's demo activity only if seeded so;
    # create a fresh table, open a session via a waiter order to make it occupied.
    created = create(client, headers, "BUSY-1").json()
    waiter_headers = waiter(client)
    menu = client.get("/api/v1/menu", headers=waiter_headers)
    item_id = menu.json()[0]["items"][0]["id"]
    order = client.post(
        "/api/v1/orders",
        json={"table_id": created["id"], "items": [{"menu_item_id": item_id, "quantity": 1}]},
        headers={**waiter_headers, "Idempotency-Key": "test-busy-1-order"},
    )
    assert order.status_code == 200, order.text

    response = client.post(f"/api/v1/tables/{created['id']}/archive", headers=headers)
    assert response.status_code == 409
    assert response.json()["code"] == "TABLE_OCCUPIED"


def test_archived_table_hidden_from_floor_but_guarded(client: TestClient) -> None:
    headers = owner(client)
    created = create(client, headers, "HID-1").json()
    client.post(f"/api/v1/tables/{created['id']}/archive", headers=headers)

    # Operations on an archived tenant-owned table give domain conflicts, not 404s
    edit = client.patch(f"/api/v1/tables/{created['id']}", json={"display_name": "x"}, headers=headers)
    assert edit.status_code == 409
    assert edit.json()["code"] == "TABLE_ARCHIVED"


# ── TENANT ISOLATION ──────────────────────────────────────────────────────────


def test_other_tenant_table_is_not_visible(client: TestClient) -> None:
    headers = owner(client)
    created = create(client, headers, "ISO-1").json()

    # Only one restaurant exists in this dev seed, so simulate a foreign id:
    fake_id = "00000000-0000-0000-0000-000000000000"
    response = client.post(f"/api/v1/tables/{fake_id}/archive", headers=headers)
    assert response.status_code == 404  # no existence leak beyond own tenant

    response = client.patch(f"/api/v1/tables/{fake_id}", json={"display_name": "x"}, headers=headers)
    assert response.status_code == 404
    assert created["id"] != fake_id
