"""Unit tests for plan version service layer (Plan 01).

Tests the business logic in app/modules/platform/services/plan_versions.py
against the existing test database (migrated via Alembic).
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy.orm import Session

import app.modules  # noqa: F401  (register all module models with Base.metadata)
from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.modules.platform.models import PlatformPlan, PlatformPlanVersion
from app.modules.platform.services.plan_versions import (
    create_plan_version,
    get_plan_versions,
    get_active_plan_version,
    update_plan_version,
    publish_plan_version,
    add_plan_feature,
    add_plan_limit,
    get_plan_entitlements,
)
from app.shared.errors import AppError


@pytest.fixture(scope="function")
def db() -> Session:
    """Create a fresh database session for each test.

    Uses the existing test database (migrated via Alembic) rather than
    create_all/drop_all, since the latter has FK ordering issues with
    cross-module tables. Ensures tables exist via create_all (checkfirst).
    """
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
    # Cleanup versions first (FK dependency), then plan
    db.execute(
        __import__("sqlalchemy").delete(PlatformPlanVersion)
        .where(PlatformPlanVersion.plan_id == p.id)
    )
    db.delete(p)
    db.commit()


class TestCreatePlanVersion:
    """Tests for creating plan versions."""

    def test_create_first_version(self, db: Session, plan: PlatformPlan):
        """Creating the first version should set version number to 1."""
        version = create_plan_version(
            db,
            plan_id=plan.id,
            price_monthly_minor=300000,
            price_annual_minor=3000000,
            currency_code="NPR",
            trial_days=30,
            effective_from=None,
            admin_id=uuid4(),
            reason="Initial version",
        )
        assert version.version == 1
        assert version.is_active is False  # Draft by default
        assert version.price_monthly_minor == 300000
        assert version.trial_days == 30

    def test_create_second_version(self, db: Session, plan: PlatformPlan):
        """Creating a second version should increment the version number."""
        v1 = create_plan_version(
            db,
            plan_id=plan.id,
            price_monthly_minor=300000,
            price_annual_minor=3000000,
            currency_code="NPR",
            trial_days=30,
            effective_from=None,
            admin_id=uuid4(),
            reason="V1",
        )
        assert v1.version == 1

        v2 = create_plan_version(
            db,
            plan_id=plan.id,
            price_monthly_minor=350000,
            price_annual_minor=3500000,
            currency_code="NPR",
            trial_days=30,
            effective_from=None,
            admin_id=uuid4(),
            reason="V2",
        )
        assert v2.version == 2
        assert v2.is_active is False


class TestPublishPlanVersion:
    """Tests for publishing plan versions."""

    def test_publish_activates_version(self, db: Session, plan: PlatformPlan):
        """Publishing a draft version should set is_active=True."""
        version = create_plan_version(
            db,
            plan_id=plan.id,
            price_monthly_minor=300000,
            price_annual_minor=3000000,
            currency_code="NPR",
            trial_days=30,
            effective_from=None,
            admin_id=uuid4(),
            reason="Draft",
        )
        assert version.is_active is False

        published = publish_plan_version(
            db,
            version_id=version.id,
            admin_id=uuid4(),
            reason="Publish V1",
        )
        assert published.is_active is True

        # Verify no other active version exists for this plan
        active = get_active_plan_version(db, plan.id)
        assert active is not None
        assert active.id == version.id

    def test_publish_deactivates_previous(self, db: Session, plan: PlatformPlan):
        """Publishing a new version should deactivate the previous active one."""
        v1 = create_plan_version(
            db,
            plan_id=plan.id,
            price_monthly_minor=300000,
            price_annual_minor=3000000,
            currency_code="NPR",
            trial_days=30,
            effective_from=None,
            admin_id=uuid4(),
            reason="V1",
        )
        publish_plan_version(db, version_id=v1.id, admin_id=uuid4(), reason="Publish V1")

        v2 = create_plan_version(
            db,
            plan_id=plan.id,
            price_monthly_minor=350000,
            price_annual_minor=3500000,
            currency_code="NPR",
            trial_days=30,
            effective_from=None,
            admin_id=uuid4(),
            reason="V2",
        )
        publish_plan_version(db, version_id=v2.id, admin_id=uuid4(), reason="Publish V2")

        # V1 should now be inactive
        v1_refreshed = db.get(PlatformPlanVersion, v1.id)
        assert v1_refreshed.is_active is False

        # V2 should be active
        active = get_active_plan_version(db, plan.id)
        assert active is not None
        assert active.id == v2.id

    def test_publish_already_active_raises(self, db: Session, plan: PlatformPlan):
        """Publishing an already-active version should raise 409."""
        version = create_plan_version(
            db,
            plan_id=plan.id,
            price_monthly_minor=300000,
            price_annual_minor=3000000,
            currency_code="NPR",
            trial_days=30,
            effective_from=None,
            admin_id=uuid4(),
            reason="Draft",
        )
        publish_plan_version(db, version_id=version.id, admin_id=uuid4(), reason="Publish")

        with pytest.raises(AppError) as exc:
            publish_plan_version(
                db, version_id=version.id, admin_id=uuid4(), reason="Publish again"
            )
        assert exc.value.status == 409
        assert exc.value.code == "PLAN_VERSION_ALREADY_ACTIVE"


class TestUpdatePlanVersion:
    """Tests for updating plan versions."""

    def test_update_draft_version(self, db: Session, plan: PlatformPlan):
        """Updating a draft version should succeed."""
        version = create_plan_version(
            db,
            plan_id=plan.id,
            price_monthly_minor=300000,
            price_annual_minor=3000000,
            currency_code="NPR",
            trial_days=30,
            effective_from=None,
            admin_id=uuid4(),
            reason="Draft",
        )

        updated = update_plan_version(
            db,
            version_id=version.id,
            price_monthly_minor=350000,
            price_annual_minor=None,
            currency_code=None,
            trial_days=45,
            effective_from=None,
            admin_id=uuid4(),
            reason="Update price and trial",
        )
        assert updated.price_monthly_minor == 350000
        assert updated.trial_days == 45
        # Unchanged fields preserved
        assert updated.price_annual_minor == 3000000
        assert updated.currency_code == "NPR"

    def test_update_active_version_raises(self, db: Session, plan: PlatformPlan):
        """Updating an active version should raise 409."""
        version = create_plan_version(
            db,
            plan_id=plan.id,
            price_monthly_minor=300000,
            price_annual_minor=3000000,
            currency_code="NPR",
            trial_days=30,
            effective_from=None,
            admin_id=uuid4(),
            reason="Draft",
        )
        publish_plan_version(db, version_id=version.id, admin_id=uuid4(), reason="Publish")

        with pytest.raises(AppError) as exc:
            update_plan_version(
                db,
                version_id=version.id,
                price_monthly_minor=350000,
                price_annual_minor=None,
                currency_code=None,
                trial_days=None,
                effective_from=None,
                admin_id=uuid4(),
                reason="Try to update active",
            )
        assert exc.value.status == 409
        assert exc.value.code == "PLAN_VERSION_ACTIVE"


class TestPlanFeaturesAndLimits:
    """Tests for plan features and limits."""

    def test_add_feature_to_draft(self, db: Session, plan: PlatformPlan):
        """Adding a feature to a draft version should succeed."""
        version = create_plan_version(
            db,
            plan_id=plan.id,
            price_monthly_minor=300000,
            price_annual_minor=3000000,
            currency_code="NPR",
            trial_days=30,
            effective_from=None,
            admin_id=uuid4(),
            reason="Draft",
        )

        feature = add_plan_feature(
            db,
            version_id=version.id,
            feature_key="qr_ordering",
            enabled=True,
            admin_id=uuid4(),
            reason="Add QR ordering",
        )
        assert feature.feature_key == "qr_ordering"
        assert feature.enabled is True

    def test_add_feature_to_active_raises(self, db: Session, plan: PlatformPlan):
        """Adding a feature to an active version should raise 409."""
        version = create_plan_version(
            db,
            plan_id=plan.id,
            price_monthly_minor=300000,
            price_annual_minor=3000000,
            currency_code="NPR",
            trial_days=30,
            effective_from=None,
            admin_id=uuid4(),
            reason="Draft",
        )
        publish_plan_version(db, version_id=version.id, admin_id=uuid4(), reason="Publish")

        with pytest.raises(AppError) as exc:
            add_plan_feature(
                db,
                version_id=version.id,
                feature_key="inventory",
                enabled=True,
                admin_id=uuid4(),
                reason="Try to add feature",
            )
        assert exc.value.status == 409
        assert exc.value.code == "PLAN_VERSION_ACTIVE"

    def test_add_limit_to_draft(self, db: Session, plan: PlatformPlan):
        """Adding a limit to a draft version should succeed."""
        version = create_plan_version(
            db,
            plan_id=plan.id,
            price_monthly_minor=300000,
            price_annual_minor=3000000,
            currency_code="NPR",
            trial_days=30,
            effective_from=None,
            admin_id=uuid4(),
            reason="Draft",
        )

        limit = add_plan_limit(
            db,
            version_id=version.id,
            limit_key="branches",
            limit_value=3,
            admin_id=uuid4(),
            reason="Add branch limit",
        )
        assert limit.limit_key == "branches"
        assert limit.limit_value == 3

    def test_get_entitlements(self, db: Session, plan: PlatformPlan):
        """Getting entitlements should return features and limits."""
        version = create_plan_version(
            db,
            plan_id=plan.id,
            price_monthly_minor=300000,
            price_annual_minor=3000000,
            currency_code="NPR",
            trial_days=30,
            effective_from=None,
            admin_id=uuid4(),
            reason="Draft",
        )
        add_plan_feature(
            db,
            version_id=version.id,
            feature_key="qr_ordering",
            enabled=True,
            admin_id=uuid4(),
            reason="Add feature",
        )
        add_plan_limit(
            db,
            version_id=version.id,
            limit_key="branches",
            limit_value=3,
            admin_id=uuid4(),
            reason="Add limit",
        )

        entitlements = get_plan_entitlements(db, version.id)
        assert entitlements["features"] == {"qr_ordering": True}
        assert entitlements["limits"] == {"branches": 3}


class TestListPlanVersions:
    """Tests for listing plan versions."""

    def test_list_versions_ordered(self, db: Session, plan: PlatformPlan):
        """Versions should be ordered by version number."""
        v1 = create_plan_version(
            db,
            plan_id=plan.id,
            price_monthly_minor=300000,
            price_annual_minor=3000000,
            currency_code="NPR",
            trial_days=30,
            effective_from=None,
            admin_id=uuid4(),
            reason="V1",
        )
        v2 = create_plan_version(
            db,
            plan_id=plan.id,
            price_monthly_minor=350000,
            price_annual_minor=3500000,
            currency_code="NPR",
            trial_days=30,
            effective_from=None,
            admin_id=uuid4(),
            reason="V2",
        )

        versions = get_plan_versions(db, plan.id)
        assert len(versions) == 2
        assert versions[0]["version"] == 1
        assert versions[1]["version"] == 2
        assert versions[0]["id"] == str(v1.id)
        assert versions[1]["id"] == str(v2.id)

    def test_get_active_version(self, db: Session, plan: PlatformPlan):
        """get_active_plan_version should return the published version."""
        assert get_active_plan_version(db, plan.id) is None

        v1 = create_plan_version(
            db,
            plan_id=plan.id,
            price_monthly_minor=300000,
            price_annual_minor=3000000,
            currency_code="NPR",
            trial_days=30,
            effective_from=None,
            admin_id=uuid4(),
            reason="V1",
        )
        publish_plan_version(db, version_id=v1.id, admin_id=uuid4(), reason="Publish")

        active = get_active_plan_version(db, plan.id)
        assert active is not None
        assert active.id == v1.id
