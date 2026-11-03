from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import Actor, require_permission
from app.db.session import get_db
from app.modules.loyalty.models import LoyaltyAccount, LoyaltyTransaction, Coupon, CouponRedemption
from app.modules.loyalty.schemas import (
    LoyaltyAccountOut,
    LoyaltyAccountIn,
    LoyaltyTransactionOut,
    LoyaltyTransactionIn,
    CouponOut,
    CouponIn,
    CouponRedemptionOut,
    CouponRedemptionIn,
)
from app.shared.errors import AppError

router = APIRouter(tags=["loyalty"])


# ── LoyaltyAccount ──────────────────────────────────────────────────────────

@router.get("/account", response_model=LoyaltyAccountOut)
def get_loyalty_account(
    actor: Actor = Depends(require_permission("loyalty.read")),
    db: Session = Depends(get_db),
) -> LoyaltyAccountOut | None:
    account = db.scalar(
        select(LoyaltyAccount).where(
            LoyaltyAccount.membership_id == actor.membership.id
        )
    )
    if account is None:
        # Create default account
        account = LoyaltyAccount(membership_id=actor.membership.id)
        db.add(account)
        db.flush()
    return LoyaltyAccountOut.model_validate(account)


@router.patch("/account", response_model=LoyaltyAccountOut)
def update_loyalty_account(
    payload: LoyaltyAccountIn,
    actor: Actor = Depends(require_permission("loyalty.update")),
    db: Session = Depends(get_db),
) -> LoyaltyAccountOut:
    account = db.scalar(
        select(LoyaltyAccount).where(
            LoyaltyAccount.membership_id == actor.membership.id
        )
    )
    if account is None:
        account = LoyaltyAccount(membership_id=actor.membership.id)
        db.add(account)

    if payload.points_balance is not None:
        account.points_balance = payload.points_balance
    if payload.tier is not None:
        account.tier = payload.tier

    db.flush()
    db.commit()
    return LoyaltyAccountOut.model_validate(account)


# ── LoyaltyTransactions ───────────────────────────────────────────────────

@router.get("/transactions", response_model=list[LoyaltyTransactionOut])
def list_loyalty_transactions(
    actor: Actor = Depends(require_permission("loyalty.read")),
    db: Session = Depends(get_db),
) -> list[LoyaltyTransactionOut]:
    transactions = db.scalars(
        select(LoyaltyTransaction).where(
            LoyaltyTransaction.membership_id == actor.membership.id
        )
    ).all()
    return [LoyaltyTransactionOut.model_validate(t) for t in transactions]


@router.post("/transactions", response_model=LoyaltyTransactionOut)
def create_loyalty_transaction(
    payload: LoyaltyTransactionIn,
    actor: Actor = Depends(require_permission("loyalty.manage")),
    db: Session = Depends(get_db),
) -> LoyaltyTransactionOut:
    transaction = LoyaltyTransaction(
        membership_id=actor.membership.id,
        type=payload.type,
        points=payload.points,
        reason=payload.reference_id,
        reference_id=payload.reference_id,
    )
    db.add(transaction)
    db.flush()
    db.commit()
    return LoyaltyTransactionOut.model_validate(transaction)


# ── Coupons ───────────────────────────────────────────────────────────────

@router.get("/coupons", response_model=list[CouponOut])
def list_coupons(
    actor: Actor = Depends(require_permission("loyalty.read")),
    db: Session = Depends(get_db),
) -> list[CouponOut]:
    coupons = db.scalars(
        select(Coupon).where(Coupon.restaurant_id == actor.restaurant_id, Coupon.is_active)
    ).all()
    return [CouponOut.model_validate(c) for c in coupons]


@router.post("/coupons", response_model=CouponOut)
def create_coupon(
    payload: CouponIn,
    actor: Actor = Depends(require_permission("loyalty.manage")),
    db: Session = Depends(get_db),
) -> CouponOut:
    # Check for duplicate code
    existing = db.scalar(
        select(Coupon).where(
            Coupon.restaurant_id == actor.restaurant_id,
            Coupon.code == payload.code,
        )
    )
    if existing:
        raise AppError(409, "COUPON_CODE_EXISTS", "Coupon code in use", "A coupon with this code already exists.")

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
    db.flush()
    db.commit()
    return CouponOut.model_validate(coupon)


@router.post("/coupons/redeem", response_model=CouponRedemptionOut)
def redeem_coupon(
    payload: CouponRedemptionIn,
    actor: Actor = Depends(require_permission("loyalty.redeem")),
    db: Session = Depends(get_db),
) -> CouponRedemptionOut:
    # Verify coupon exists and is active
    coupon = db.get(Coupon, payload.coupon_id)
    if not coupon or not coupon.is_active:
        raise AppError(404, "COUPON_NOT_FOUND", "Not found", "Coupon was not found.")

    if coupon.valid_until and coupon.valid_until < datetime.now():
        raise AppError(422, "COUPON_EXPIRED", "Coupon expired", "This coupon has expired.")

    if coupon.current_redeem_count >= coupon.maximum_redeem_count:
        raise AppError(422, "COUPON_LIMIT_REACHED", "Redemption limit reached", "This coupon has reached its redemption limit.")

    # Verify membership is eligible
    from app.modules.tenancy.models import RestaurantMembership
    membership = db.get(RestaurantMembership, actor.membership.id)
    if not membership or membership.restaurant_id != coupon.restaurant_id:
        raise AppError(403, "PERMISSION_DENIED", "Insufficient permissions", "Membership does not belong to this restaurant.")

    # Check usage limit per customer
    if coupon.usage_limit_per_customer:
        # Check how many times this membership has used this coupon
        count = db.scalar(
            select(CouponRedemption).where(
                CouponRedemption.coupon_id == payload.coupon_id,
                CouponRedemption.membership_id == actor.membership.id,
            )
        )
        if count and count >= coupon.usage_limit_per_customer:
            raise AppError(422, "COUPON_USAGE_LIMIT_REACHED", "Usage limit reached per customer", "This customer has reached the usage limit for this coupon.")

    # Check current redeem count
    if coupon.current_redeem_count >= coupon.maximum_redeem_count:
        raise AppError(422, "COUPON_MAX_REDEEMS_REACHED", "Maximum redemptions reached", "This coupon has reached its maximum redemption count.")

    # Create redemption
    redemption = CouponRedemption(
        coupon_id=payload.coupon_id,
        membership_id=actor.membership.id,
        order_id=payload.order_id,
        discount_amount_minor=payload.discount_amount_minor,
    )

    # Update coupon stats
    coupon.current_redeem_count += 1

    db.add(redemption)
    db.flush()
    db.commit()
    return CouponRedemptionOut.model_validate(redemption)