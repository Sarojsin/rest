"""Unit tests for trial lifecycle service (Plan 03).

Tests the business logic in app/modules/platform/services/trial.py
against the existing test database (migrated via Alembic).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

import app.modules  # noqa: F401  (register all module models with Base.metadata)
from app.db.session import SessionLocal
from app.modules.platform.models import (
    PlatformPlan,
    PlatformPlanVersion,
    PlatformSubscription,
    PlatformSubscriptionTrialHistory,
    PlatformPlanFeature,
    PlatformPlanLimit,
    PlatformUsageEvent,
)
from app.modules.tenancy.models import Restaurant
from app.modules.platform.services.trial import (
    expire_expired_trials,
    get_trial_expirations,
    has_prior_trial,
    record_trial_history,
    mark_trial_converted,
    can_create_trial,
    extend_trial,
    expire_trial_manually,
    get_trial_status,
)
from app.modules.platform.services.entitlements import (
    check_feature_enabled,
    check_limit_available,
    consume_limit,
    release_limit,
    get_effective_entitlements,
    get_usage_status,
    reconcile_usage_counters,
)
from app.shared.errors import AppError


@pytest.fixture(scope="function")
def db() -> Session:
    """Create a fresh database session for each test."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture
def plan(db: Session) -> PlatformPlan:
    """Create a test plan with a unique code."""
    code = f"test_plan_{uuid4().hex[:8]}"
    p = PlatformPlan(
        code=code,
        name="Test Plan",
        description="Test plan for unit tests",
        price_monthly_minor=299900,
        price_annual_minor=299900 * 10,
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
    db.execute(
        __import__("sqlalchemy").delete(PlatformPlanVersion).where(
            PlatformPlanVersion.plan_id == p.id
        )
    )
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

    db.add(
        PlatformPlanFeature(
            plan_version_id=v.id,
            feature_key="qr_ordering",
            enabled=True,
        )
    )
    db.add(
        PlatformPlanFeature(
            plan_version_id=v.id,
            feature_key="inventory",
            enabled=False,
        )
    )
    db.add(
        PlatformPlanLimit(
            plan_version_id=v.id,
            limit_key="branches",
            limit_value=3,
        )
    )
    db.add(
        PlatformPlanLimit(
            plan_version_id=v.id,
            limit_key="waiters",
            limit_value=5,
        )
    )
    db.commit()
    db.refresh(v)
    yield v
    # Clean dependents that reference this version before it is removed.
    db.rollback()
    db.execute(
        __import__("sqlalchemy").text(
            "DELETE FROM platform_subscription_trial_history WHERE plan_version_id = :v_id"
        ),
        {"v_id": v.id},
    )
    db.execute(
        __import__("sqlalchemy").text(
            "UPDATE platform_subscriptions SET plan_version_id = NULL WHERE plan_version_id = :v_id"
        ),
        {"v_id": v.id},
    )
    db.execute(
        __import__("sqlalchemy").delete(PlatformPlanFeature).where(
            PlatformPlanFeature.plan_version_id == v.id
        )
    )
    db.execute(
        __import__("sqlalchemy").delete(PlatformPlanLimit).where(
            PlatformPlanLimit.plan_version_id == v.id
        )
    )
    db.commit()


@pytest.fixture
def restaurant_id(db: Session) -> uuid4:
    """Create a test restaurant."""
    rid = uuid4()
    db.execute(
        text(
            "INSERT INTO restaurants (id, name, slug, status, timezone, currency_code, created_at, updated_at) "
            "VALUES (:id, :name, :slug, 'ACTIVE', :timezone, :currency_code, :now, :now)"
        ),
        {
            "id": rid,
            "name": f"Test Restaurant {uuid4().hex[:8]}",
            "slug": f"rest-{uuid4().hex[:8]}",
            "timezone": "Asia/Kathmandu",
            "currency_code": "NPR",
            "now": datetime.now(UTC),
        },
    )
    db.commit()
    yield rid
    # Clean dependent rows first (usage counters/events hold FK to restaurants).
    db.execute(
        text("DELETE FROM platform_usage_events WHERE restaurant_id = :id"), {"id": rid}
    )
    db.execute(
        text("DELETE FROM platform_tenant_usage WHERE restaurant_id = :id"), {"id": rid}
    )
    db.execute(text("DELETE FROM restaurants WHERE id = :id"), {"id": rid})
    db.commit()


@pytest.fixture
def subscription(
    db: Session, restaurant_id: uuid4, plan_version: PlatformPlanVersion
) -> PlatformSubscription:
    """Create an active subscription for the restaurant."""
    now = datetime.now(UTC)
    s = PlatformSubscription(
        restaurant_id=restaurant_id,
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


@pytest.fixture
def trialing_subscription(
    db: Session, restaurant_id: uuid4, plan_version: PlatformPlanVersion
) -> PlatformSubscription:
    """Create a TRIALING subscription for the restaurant."""
    now = datetime.now(UTC)
    s = PlatformSubscription(
        restaurant_id=restaurant_id,
        plan_id=plan_version.plan_id,
        plan_version_id=plan_version.id,
        status="TRIALING",
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


class TestCanCreateTrial:
    """Tests for trial eligibility."""

    def test_can_create_trial(self, db: Session, restaurant_id: uuid4):
        """A tenant with no prior trial can create one."""
        eligible, reason = can_create_trial(db, restaurant_id=restaurant_id)
        assert eligible is True
        assert reason is None

    def test_cannot_create_trial_after_prior(
        self, db: Session, restaurant_id: uuid4, trialing_subscription: PlatformSubscription
    ):
        """A tenant with a prior trial cannot create another."""
        record_trial_history(
            db,
            restaurant_id=restaurant_id,
            trial_start_at=datetime.now(UTC) - timedelta(days=30),
            trial_end_at=datetime.now(UTC) - timedelta(days=16),
            plan_version_id=trialing_subscription.plan_version_id,
            reason="previous trial",
        )
        db.commit()

        eligible, reason = can_create_trial(db, restaurant_id=restaurant_id)
        assert eligible is False
        assert "already" in reason.lower()


class TestExtendTrial:
    """Tests for trial extension."""

    def test_extend_trial(
        self, db: Session, restaurant_id: uuid4, trialing_subscription: PlatformSubscription
    ):
        """Extending a trial moves the end date forward."""
        original_end = trialing_subscription.trial_ends_at

        result = extend_trial(
            db,
            subscription=trialing_subscription,
            days=7,
            actor_admin_id=uuid4(),
            reason="Customer requested extension",
        )

        assert result.trial_ends_at == original_end + timedelta(days=7)
        assert result.trial_extension_count == 1
        assert result.trial_extension_total_days == 7

    def test_extend_trial_exceeds_per_action(
        self, db: Session, restaurant_id: uuid4, trialing_subscription: PlatformSubscription
    ):
        """Extending beyond per-action limit raises 422."""
        with pytest.raises(AppError) as exc:
            extend_trial(
                db,
                subscription=trialing_subscription,
                days=31,
                actor_admin_id=uuid4(),
                reason="Too long extension",
            )
        assert exc.value.status == 422
        assert exc.value.code == "INVALID_AMOUNT"

    def test_extend_non_trialing_raises(
        self, db: Session, restaurant_id: uuid4, plan_version: PlatformPlanVersion
    ):
        """Extending a non-trialing subscription raises 409."""
        now = datetime.now(UTC)
        active_sub = PlatformSubscription(
            restaurant_id=restaurant_id,
            plan_id=plan_version.plan_id,
            plan_version_id=plan_version.id,
            status="ACTIVE",
            current_period_start=now,
            current_period_end=now + timedelta(days=30),
            price_snapshot_minor=plan_version.price_monthly_minor,
            currency_snapshot=plan_version.currency_code,
            billing_interval_snapshot="MONTHLY",
        )
        db.add(active_sub)
        db.commit()
        db.refresh(active_sub)

        try:
            with pytest.raises(AppError) as exc:
                extend_trial(
                    db,
                    subscription=active_sub,
                    days=7,
                    actor_admin_id=uuid4(),
                    reason="Extend active",
                )
            assert exc.value.status == 409
            assert exc.value.code == "INVALID_STATUS_TRANSITION"
        finally:
            db.delete(active_sub)
            db.commit()


class TestExpireTrialManually:
    """Tests for manual trial expiration."""

    def test_expire_trial_manually(
        self, db: Session, restaurant_id: uuid4, trialing_subscription: PlatformSubscription
    ):
        """Manually expiring a trial changes status to EXPIRED."""
        result = expire_trial_manually(
            db,
            subscription=trialing_subscription,
            actor_admin_id=uuid4(),
            reason="Customer requested early termination",
        )

        assert result.status == "EXPIRED"

        history = db.scalars(
            __import__("sqlalchemy").select(PlatformSubscriptionTrialHistory).where(
                PlatformSubscriptionTrialHistory.restaurant_id == restaurant_id
            )
        ).all()
        assert len(history) == 1
        assert history[0].converted_to_paid is False


class TestGetTrialStatus:
    """Tests for get_trial_status."""

    def test_get_trial_status(
        self, db: Session, restaurant_id: uuid4, trialing_subscription: PlatformSubscription
    ):
        """Getting trial status returns days remaining."""
        status = get_trial_status(db, restaurant_id=restaurant_id)
        assert status is not None
        assert status["status"] == "TRIALING"
        # ``days_remaining`` floors; a 14-day window is 13 while the remainder
        # of the current day is still elapsing.
        assert status["days_remaining"] in (13, 14)
        assert status["trial_extension_count"] == 0

    def test_get_trial_status_no_trial(
        self, db: Session, restaurant_id: uuid4
    ):
        """Getting trial status for a tenant with no trial returns None."""
        assert get_trial_status(db, restaurant_id=restaurant_id) is None


class TestExpireExpiredTrials:
    """Tests for bulk trial expiration."""

    def test_expire_expired_trials(
        self, db: Session, restaurant_id: uuid4, trialing_subscription: PlatformSubscription
    ):
        """Expiring expired trials marks them as EXPIRED."""
        trialing_subscription.trial_ends_at = datetime.now(UTC) - timedelta(days=1)
        db.commit()

        count = expire_expired_trials(db)
        assert count == 1

        db.refresh(trialing_subscription)
        assert trialing_subscription.status == "EXPIRED"


class TestGetTrialExpirations:
    """Tests for getting expiring trials."""

    def test_get_trial_expirations(
        self, db: Session, restaurant_id: uuid4, trialing_subscription: PlatformSubscription
    ):
        """Getting expiring trials returns trials within the window."""
        trialing_subscription.trial_ends_at = datetime.now(UTC) + timedelta(days=2)
        db.commit()

        trials = get_trial_expirations(db, days_ahead=3)
        assert len(trials) == 1
        assert trials[0]["restaurant_id"] == str(restaurant_id)
        # Floor rounding: a 2-day window is 1 while today's remainder elapses.
        assert trials[0]["days_remaining"] in (1, 2)

    def test_get_trial_expirations_outside_window(
        self, db: Session, restaurant_id: uuid4, trialing_subscription: PlatformSubscription
    ):
        """Trials expiring beyond the window are not returned."""
        trialing_subscription.trial_ends_at = datetime.now(UTC) + timedelta(days=10)
        db.commit()

        trials = get_trial_expirations(db, days_ahead=3)
        assert len(trials) == 0


class TestTrialHistory:
    """Tests for trial history recording."""

    def test_record_trial_history(
        self, db: Session, restaurant_id: uuid4, plan_version: PlatformPlanVersion
    ):
        """Recording trial history creates a history record."""
        history = record_trial_history(
            db,
            restaurant_id=restaurant_id,
            trial_start_at=datetime.now(UTC) - timedelta(days=30),
            trial_end_at=datetime.now(UTC) - timedelta(days=16),
            plan_version_id=plan_version.id,
            reason="previous trial",
        )

        assert history.restaurant_id == restaurant_id
        assert history.plan_version_id == plan_version.id
        assert history.converted_to_paid is False

    def test_mark_trial_converted(
        self, db: Session, restaurant_id: uuid4, plan_version: PlatformPlanVersion
    ):
        """Marking trial as converted sets converted_to_paid."""
        history = record_trial_history(
            db,
            restaurant_id=restaurant_id,
            trial_start_at=datetime.now(UTC) - timedelta(days=30),
            trial_end_at=datetime.now(UTC) - timedelta(days=16),
            plan_version_id=plan_version.id,
            reason="previous trial",
        )
        db.commit()

        # A conversion may reference the confirming payment; here we assert the
        # conversion state itself, so no payment row is required.
        mark_trial_converted(
            db,
            restaurant_id=restaurant_id,
            converted_payment_id=None,
        )

        db.refresh(history)
        assert history.converted_to_paid is True
        assert history.converted_at is not None
        assert history.converted_payment_id is None
