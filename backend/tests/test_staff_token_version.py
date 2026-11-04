"""PA-0.10 — staff token version and force-logout stub."""

from __future__ import annotations

from collections.abc import Generator
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.main import app
from app.modules.tenancy.models import RestaurantMembership
from app.modules.tenancy.services.force_logout import (
    force_logout_membership,
    force_logout_restaurant,
)
from app.seed import seed_if_empty

OWNER_EMAIL = "owner@harbor.example"
OWNER_PASSWORD = "HarborOwner!1"


@pytest.fixture()
def db() -> Generator[Session, None, None]:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


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


def _login(client: TestClient) -> str:
    response = client.post(
        "/api/v1/auth/login",
        json={"email": OWNER_EMAIL, "password": OWNER_PASSWORD},
    )
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def test_staff_token_carries_the_membership_version(client: TestClient) -> None:
    token = _login(client)
    payload = decode_access_token(token)
    assert payload["ver"] == 0
    assert payload["realm"] == "staff"


def test_bumping_membership_version_revokes_existing_tokens(
    client: TestClient, db: Session
) -> None:
    token = _login(client)
    me = client.get("/api/v1/me", headers=_auth(token)).json()
    membership_id = UUID(me["membership"]["id"])

    membership = db.get(RestaurantMembership, membership_id)
    assert membership is not None
    before = membership.token_version
    force_logout_membership(db, membership)
    db.commit()

    assert membership.token_version == before + 1

    revoked = client.get("/api/v1/me", headers=_auth(token))
    assert revoked.status_code == 401
    assert revoked.json()["code"] == "TOKEN_REVOKED"

    fresh = _login(client)
    assert decode_access_token(fresh)["ver"] == membership.token_version
    assert client.get("/api/v1/me", headers=_auth(fresh)).status_code == 200


def test_force_logout_restaurant_bumps_every_membership(
    client: TestClient, db: Session
) -> None:
    token = _login(client)
    me = client.get("/api/v1/me", headers=_auth(token)).json()
    restaurant_id = UUID(me["membership"]["restaurant_id"])

    memberships = db.scalars(
        select(RestaurantMembership).where(
            RestaurantMembership.restaurant_id == restaurant_id
        )
    ).all()
    before = {m.id: m.token_version for m in memberships}

    affected = force_logout_restaurant(db, restaurant_id)
    db.commit()

    assert affected == len(memberships)
    for membership in memberships:
        db.refresh(membership)
        assert membership.token_version == before[membership.id] + 1

    assert client.get("/api/v1/me", headers=_auth(token)).status_code == 401
