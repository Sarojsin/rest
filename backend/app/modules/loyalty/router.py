from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.api.deps import Actor, require_permission
from app.db.session import get_db
from app.modules.loyalty.models import (
    Coupon,
    CouponRedemption,
    LoyaltyAccount,
    LoyaltyTransaction,
)
from app.modules.loyalty.schemas import (
    CouponIn,
    CouponOut,
    CouponRedemptionIn,
    CouponRedemptionOut,
    LoyaltyAccountIn,
    LoyaltyAccountOut,
    LoyaltyTransactionIn,
    LoyaltyTransactionOut,
)
from app.shared.errors import AppError

router = APIRouter(tags=["loyalty"])


def _account_for(db: Session, actor: Actor, create: bool = False) -> LoyaltyAccount | None:
    account = db.scalar(
        select(LoyaltyAccount).where(
            LoyaltyAccount.restaurant_id == actor.restaurant_id,
            LoyaltyAccount.membership_id == actor.membership.id,
        )
    )
    if account is None and create:
        account = LoyaltyAccount(
            restaurant_id=actor.restaurant_id,
            membership_id=actor.membership.id,
        )
        db.add(account)
        db.commit()
        db.refresh(account)
    return account


# ── LoyaltyAccount ──────────────────────────────────────────────────────────

@router.get("/account", response_model=LoyaltyAccountOut)
def get_loyalty_account(
    actor: Actor = Depends(require_permission("loyalty.read")),
    db: Session = Depends(get_db),
) -> LoyaltyAccountOut:
    account = _account_for(db, actor, create=True)
    assert account is not None
    return LoyaltyAccountOut.model_validate(account)


@router.patch("/account", response_model=LoyaltyAccountOut)
def update_loyalty_account(
    payload: LoyaltyAccountIn,
    actor: Actor = Depends(require_permission("loyalty.manage")),
    db: Session = Depends(get_db),
) -> LoyaltyAccountOut:
    account = _account_for(db, actor, create=True)
    assert account is not None
    account.points_balance = payload.points_balance
    account.tier = payload.tier
    db.commit()
    db.refresh(account)
    return LoyaltyAccountOut.model_validate(account)


# ── LoyaltyTransactions ───────────────────────────────────────────────────

@router.get("/transactions", response_model=list[LoyaltyTransactionOut])
def list_loyalty_transactions(
    actor: Actor = Depends(require_permission("loyalty.read")),
    db: Session = Depends(get_db),
) -> list[LoyaltyTransactionOut]:
    rows = db.scalars(
        select(LoyaltyTransaction)
        .where(
            LoyaltyTransaction.restaurant_id == actor.restaurant_id,
            LoyaltyTransaction.membership_id == actor.membership.id,
        )
        .order_by(LoyaltyTransaction.created_at.desc())
    ).all()
    return [LoyaltyTransactionOut.model_validate(t) for t in rows]


@router.post("/transactions", response_model=LoyaltyTransactionOut, status_code=201)
def create_loyalty_transaction(
    payload: LoyaltyTransactionIn,
    actor: Actor = Depends(require_permission("loyalty.manage")),
    db: Session = Depends(get_db),
) -> LoyaltyTransactionOut:
    account = _account_for(db, actor, create=True)
    assert account is not None

    transaction = LoyaltyTransaction(
        restaurant_id=actor.restaurant_id,
        membership_id=actor.membership.id,
        type=payload.type,
        points=payload.points,
        reason=payload.reason,
        reference_id=payload.reference_id,
    )

    if payload.type == "EARN":
        account.points_balance += payload.points
        account.total_earned += payload.points
        account.last_earned_at = datetime.now(UTC)
    else:
        if payload.points > account.points_balance:
            raise AppError(
                422, "INSUFFICIENT_POINTS", "Insufficient points",
                "The account does not have enough points to redeem.",
            )
        account.points_balance -= payload.points
        account.total_redeemed += payload.points
        account.last_redeemed_at = datetime.now(UTC)

    db.add(transaction)
    db.commit()
    db.refresh(transaction)
    return LoyaltyTransactionOut.model_validate(transaction)


# ── Coupons ───────────────────────────────────────────────────────────────

@router.get("/coupons", response_model=list[CouponOut])
def list_coupons(
    include_inactive: bool = False,
    actor: Actor = Depends(require_permission("loyalty.read")),
    db: Session = Depends(get_db),
) -> list[CouponOut]:
    stmt = select(Coupon).where(Coupon.restaurant_id == actor.restaurant_id)
    if not include_inactive:
        stmt = stmt.where(Coupon.is_active.is_(True))
    coupons = db.scalars(stmt.order_by(Coupon.code)).all()
    return [CouponOut.model_validate(c) for c in coupons]


@router.post("/coupons", response_model=CouponOut, status_code=201)
def create_coupon(
    payload: CouponIn,
    actor: Actor = Depends(require_permission("loyalty.manage")),
    db: Session = Depends(get_db),
) -> CouponOut:
    existing = db.scalar(
        select(Coupon).where(
            Coupon.restaurant_id == actor.restaurant_id,
            Coupon.code == payload.code,
        )
    )
    if existing:
        raise AppError(
            409, "COUPON_CODE_EXISTS", "Coupon code in use",
            "A coupon with this code already exists.",
        )

    coupon = Coupon(
        restaurant_id=actor.restaurant_id,
        code=payload.code,
        name=payload.name,
        description=payload.description,
        discount_type=payload.discount_type,
        discount_value=payload.discount_value,
        minimum_spend_minor=payload.minimum_spend_minor,
        maximum_redeem_count=payload.maximum_redeem_count,
        valid_from=payload.valid_from,
        valid_until=payload.valid_until,
        usage_limit_per_customer=payload.usage_limit_per_customer,
    )
    db.add(coupon)
    db.commit()
    db.refresh(coupon)
    return CouponOut.model_validate(coupon)


@router.get("/coupons/{coupon_id}", response_model=CouponOut)
def get_coupon(
    coupon_id: UUID,
    actor: Actor = Depends(require_permission("loyalty.read")),
    db: Session = Depends(get_db),
) -> CouponOut:
    coupon = db.get(Coupon, coupon_id)
    if coupon is None or coupon.restaurant_id != actor.restaurant_id:
        raise AppError(404, "COUPON_NOT_FOUND", "Not found", "Coupon was not found.")
    return CouponOut.model_validate(coupon)


@router.post("/coupons/redeem", response_model=CouponRedemptionOut, status_code=201)
def redeem_coupon(
    payload: CouponRedemptionIn,
    actor: Actor = Depends(require_permission("loyalty.redeem")),
    db: Session = Depends(get_db),
) -> CouponRedemptionOut:
    coupon = db.get(Coupon, payload.coupon_id)
    if coupon is None or coupon.restaurant_id != actor.restaurant_id:
        raise AppError(404, "COUPON_NOT_FOUND", "Not found", "Coupon was not found.")
    if not coupon.is_active:
        raise AppError(422, "COUPON_INACTIVE", "Coupon inactive", "This coupon is not active.")

    now = datetime.now(UTC)
    if coupon.valid_from > now:
        raise AppError(
            422, "COUPON_NOT_STARTED", "Coupon not active yet",
            "This coupon is not valid yet.",
        )
    if coupon.valid_until is not None and coupon.valid_until < now:
        raise AppError(422, "COUPON_EXPIRED", "Coupon expired", "This coupon has expired.")
    if (
        coupon.maximum_redeem_count is not None
        and coupon.current_redeem_count >= coupon.maximum_redeem_count
    ):
        raise AppError(
            422, "COUPON_LIMIT_REACHED", "Redemption limit reached",
            "This coupon has reached its redemption limit.",
        )

    order_exists = db.execute(
        text("SELECT 1 FROM orders WHERE id = :id AND restaurant_id = :rid"),
        {"id": payload.order_id, "rid": actor.restaurant_id},
    ).scalar_one_or_none()
    if order_exists is None:
        raise AppError(404, "ORDER_NOT_FOUND", "Not found", "Order was not found.")

    if coupon.usage_limit_per_customer is not None:
        used = db.scalar(
            select(func.count())
            .select_from(CouponRedemption)
            .where(
                CouponRedemption.coupon_id == coupon.id,
                CouponRedemption.membership_id == actor.membership.id,
            )
        )
        if used is not None and used >= coupon.usage_limit_per_customer:
            raise AppError(
                422, "COUPON_USAGE_LIMIT_REACHED", "Usage limit reached",
                "This customer has reached the usage limit for this coupon.",
            )

    redemption = CouponRedemption(
        restaurant_id=actor.restaurant_id,
        coupon_id=coupon.id,
        membership_id=actor.membership.id,
        order_id=payload.order_id,
        discount_amount_minor=payload.discount_amount_minor,
        redeemed_at=now,
    )
    coupon.current_redeem_count += 1
    db.add(redemption)
    db.commit()
    db.refresh(redemption)
    return CouponRedemptionOut.model_validate(redemption)
