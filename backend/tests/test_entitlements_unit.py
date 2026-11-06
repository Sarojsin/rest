"""Unit tests for plan entitlement enforcement service (Plan 02).

Tests the business logic in app/modules/platform/services/entitlements.py
against the existing test database (migrated via Alembic).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

import app.modules  # noqa: F401  (register all module models with Base.metadata)
from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.modules.platform.models import (
    PlatformPlan,
    PlatformPlanFeature,
    PlatformPlanLimit,
    PlatformPlanVersion,
    PlatformSubscription,
    PlatformTenantUsage,
    PlatformUsageEvent,
)
from app.modules.platform.services.entitlements import (
    backfill_usage_counters,
    check_feature_enabled,
    check_limit_available,
    consume_limit,
    get_effective_entitlements,
    get_usage_status,
    reconcile_usage_counters,
    release_limit,
)
from app.modules.tenancy.models import Restaurant  # noqa: F401  (register model)


@pytest.fixture(scope="function")
def db() -> Session:
    """Create a database session for each test (migrated via Alembic)."""
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture
def plan(db: Session) -> PlatformPlan:
    """Create a test plan with a unique code."""
    p = PlatformPlan(
        code=f"tplan_{uuid4().hex[:8]}",
        name="Test Plan",
        description="Entitlement test plan",
        price_monthly_minor=299900,
        price_annual_minor=2999000,
        currency_code="NPR",
        trial_days=14,
        status="ACTIVE",
        is_public=True,
        sort_order=1,
    )
    db.add(p)
    db.commit()
    db.refresh(p)
    yield p
    db.delete(p)
    db.commit()


@pytest.fixture
def plan_version(db: Session, plan: PlatformPlan) -> PlatformPlanVersion:
    """Create an active plan version with features and limits."""
    v = PlatformPlanVersion(
        plan_id=plan.id,
        version=1,
        price_monthly_minor=300000,
        price_annual_minor=3000000,
        currency_code="NPR",
        trial_days=30,
        is_active=True,
    )
    db.add(v)
    db.flush()
    db.add(PlatformPlanFeature(plan_version_id=v.id, feature_key="qr_ordering", enabled=True))
    db.add(PlatformPlanFeature(plan_version_id=v.id, feature_key="inventory", enabled=False))
    db.add(PlatformPlanLimit(plan_version_id=v.id, limit_key="branches", limit_value=3))
    db.add(PlatformPlanLimit(plan_version_id=v.id, limit_key="waiters", limit_value=5))
    db.commit()
    db.refresh(v)
    yield v
    db.delete(v)
    db.commit()


@pytest.fixture
def restaurant(db: Session) -> Restaurant:
    """Create a test restaurant."""
    r = Restaurant(
        name=f"Test Restaurant {uuid4().hex[:6]}",
        slug=f"test-rest-{uuid4().hex[:8]}",
        status="ACTIVE",
        timezone="Asia/Kathmandu",
        currency_code="NPR",
    )
    db.add(r)
    db.commit()
    db.refresh(r)
    yield r
    # Clean up dependent rows before the restaurant (FK constraints).
    db.query(PlatformUsageEvent).filter(
        PlatformUsageEvent.restaurant_id == r.id
    ).delete(synchronize_session=False)
    db.query(PlatformTenantUsage).filter(
        PlatformTenantUsage.restaurant_id == r.id
    ).delete(synchronize_session=False)
    db.commit()
    db.delete(r)
    db.commit()


@pytest.fixture
def subscription(
    db: Session, restaurant: Restaurant, plan_version: PlatformPlanVersion
) -> PlatformSubscription:
    """Create an active subscription for the restaurant."""
    now = datetime.now(UTC)
    s = PlatformSubscription(
        restaurant_id=restaurant.id,
        plan_id=plan_version.plan_id,
        plan_version_id=plan_version.id,
        status="ACTIVE",
        current_period_start=now,
        current_period_end=now + timedelta(days=30),
        trial_ends_at=now + timedelta(days=14),
        price_snapshot_minor=plan_version.price_monthly_minor,
        currency_snapshot=plan_version.currency_code,
        billing_interval_snapshot="MONTHLY",
    )
    db.add(s)
    db.commit()
    db.refresh(s)
    yield s
    db.delete(s)
    db.commit()


class TestGetEffectiveEntitlements:
    def test_get_entitlements(
        self,
        db: Session,
        restaurant: Restaurant,
        subscription: PlatformSubscription,
        plan_version: PlatformPlanVersion,
    ):
        ent = get_effective_entitlements(db, restaurant_id=restaurant.id)
        assert ent is not None
        assert ent["features"] == {"qr_ordering": True, "inventory": False}
        assert ent["limits"] == {"branches": 3, "waiters": 5}

    def test_no_subscription(self, db: Session, restaurant: Restaurant):
        assert get_effective_entitlements(db, restaurant_id=restaurant.id) is None


class TestCheckFeatureEnabled:
    def test_feature_enabled(self, db: Session, restaurant: Restaurant, subscription):
        assert check_feature_enabled(
            db, restaurant_id=restaurant.id, feature_key="qr_ordering"
        ) is True

    def test_feature_disabled(self, db: Session, restaurant: Restaurant, subscription):
        assert check_feature_enabled(
            db, restaurant_id=restaurant.id, feature_key="inventory"
        ) is False

    def test_feature_unknown(self, db: Session, restaurant: Restaurant, subscription):
        assert check_feature_enabled(
            db, restaurant_id=restaurant.id, feature_key="nonexistent"
        ) is False

    def test_no_subscription(self, db: Session, restaurant: Restaurant):
        assert check_feature_enabled(
            db, restaurant_id=restaurant.id, feature_key="qr_ordering"
        ) is False


class TestCheckLimitAvailable:
    def test_limit_available(self, db: Session, restaurant: Restaurant, subscription):
        assert check_limit_available(
            db, restaurant_id=restaurant.id, limit_key="branches"
        ) is True

    def test_limit_at_capacity(self, db: Session, restaurant: Restaurant, subscription):
        for _ in range(3):
            assert consume_limit(db, restaurant_id=restaurant.id, limit_key="branches") is True
        assert check_limit_available(
            db, restaurant_id=restaurant.id, limit_key="branches"
        ) is False

    def test_increment_check(self, db: Session, restaurant: Restaurant, subscription):
        assert check_limit_available(
            db, restaurant_id=restaurant.id, limit_key="waiters", increment=3
        ) is True
        assert check_limit_available(
            db, restaurant_id=restaurant.id, limit_key="waiters", increment=5
        ) is True
        assert check_limit_available(
            db, restaurant_id=restaurant.id, limit_key="waiters", increment=6
        ) is False


class TestConsumeLimit:
    def test_consume_limit(self, db: Session, restaurant: Restaurant, subscription):
        assert consume_limit(db, restaurant_id=restaurant.id, limit_key="branches") is True
        assert consume_limit(db, restaurant_id=restaurant.id, limit_key="branches") is True
        status = get_usage_status(db, restaurant_id=restaurant.id)
        assert status["usage"]["branches"]["current"] == 2

    def test_consume_limit_rejected(self, db: Session, restaurant: Restaurant, subscription):
        for _ in range(3):
            assert consume_limit(db, restaurant_id=restaurant.id, limit_key="branches") is True
        assert consume_limit(db, restaurant_id=restaurant.id, limit_key="branches") is False

    def test_consume_no_subscription(self, db: Session, restaurant: Restaurant):
        assert consume_limit(db, restaurant_id=restaurant.id, limit_key="branches") is False

    def test_consume_record_usage_event(
        self, db: Session, restaurant: Restaurant, subscription
    ):
        assert consume_limit(
            db,
            restaurant_id=restaurant.id,
            limit_key="waiters",
            reason="test reason",
        ) is True
        events = db.query(PlatformUsageEvent).filter(
            PlatformUsageEvent.restaurant_id == restaurant.id,
            PlatformUsageEvent.resource_type == "waiters",
        ).all()
        assert len(events) == 1
        assert events[0].change == 1
        assert events[0].reason == "test reason"


class TestReleaseLimit:
    def test_release_limit(self, db: Session, restaurant: Restaurant, subscription):
        assert consume_limit(db, restaurant_id=restaurant.id, limit_key="waiters") is True
        assert consume_limit(db, restaurant_id=restaurant.id, limit_key="waiters") is True
        assert release_limit(db, restaurant_id=restaurant.id, limit_key="waiters") is True
        status = get_usage_status(db, restaurant_id=restaurant.id)
        assert status["usage"]["waiters"]["current"] == 1


class TestGetUsageStatus:
    def test_get_usage_status(self, db: Session, restaurant: Restaurant, subscription):
        status = get_usage_status(db, restaurant_id=restaurant.id)
        assert status is not None
        assert status["usage"]["branches"]["current"] == 0
        assert status["usage"]["branches"]["limit"] == 3
        assert status["usage"]["branches"]["remaining"] == 3
        assert status["usage"]["branches"]["at_limit"] is False

    def test_get_usage_status_no_subscription(self, db: Session, restaurant: Restaurant):
        assert get_usage_status(db, restaurant_id=restaurant.id) is None


class TestReconcileUsageCounters:
    def test_reconcile(self, db: Session, restaurant: Restaurant, subscription):
        assert consume_limit(db, restaurant_id=restaurant.id, limit_key="waiters") is True
        assert consume_limit(db, restaurant_id=restaurant.id, limit_key="waiters") is True
        result = reconcile_usage_counters(db, restaurant_id=restaurant.id)
        assert result["current"]["waiter_count"] == 2
        assert result["previous"]["waiter_count"] == 2


class TestReleaseLimitFloor:
    def test_release_floors_at_zero(self, db: Session, restaurant: Restaurant, subscription):
        # Release a counter that is already at zero — must floor, not go negative.
        assert release_limit(db, restaurant_id=restaurant.id, limit_key="waiters") is True
        status = get_usage_status(db, restaurant_id=restaurant.id)
        assert status["usage"]["waiters"]["current"] == 0

    def test_release_decrements(self, db: Session, restaurant: Restaurant, subscription):
        assert consume_limit(db, restaurant_id=restaurant.id, limit_key="waiters") is True
        assert consume_limit(db, restaurant_id=restaurant.id, limit_key="waiters") is True
        assert release_limit(db, restaurant_id=restaurant.id, limit_key="waiters") is True
        status = get_usage_status(db, restaurant_id=restaurant.id)
        assert status["usage"]["waiters"]["current"] == 1


class TestBackfillUsageCounters:
    def test_backfill_creates_usage_row(
        self, db: Session, restaurant: Restaurant, subscription
    ):
        # No usage row exists yet.
        assert db.scalar(
            select(PlatformTenantUsage).where(
                PlatformTenantUsage.restaurant_id == restaurant.id
            )
        ) is None

        summary = backfill_usage_counters(db, restaurant_id=restaurant.id)
        assert str(restaurant.id) in summary
        row = db.scalar(
            select(PlatformTenantUsage).where(
                PlatformTenantUsage.restaurant_id == restaurant.id
            )
        )
        assert row is not None
        assert row.branch_count == 0
        assert row.table_count == 0

    def test_backfill_idempotent(
        self, db: Session, restaurant: Restaurant, subscription
    ):
        backfill_usage_counters(db, restaurant_id=restaurant.id)
        first = backfill_usage_counters(db, restaurant_id=restaurant.id)
        second = backfill_usage_counters(db, restaurant_id=restaurant.id)
        # Second run: nothing changed (no new events).
        assert all(v == 0 for v in second[str(restaurant.id)].values())
