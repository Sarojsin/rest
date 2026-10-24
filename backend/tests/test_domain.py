import pytest

from app.core.errors import AppError
from app.domain.enums import KitchenItemStatus, OrderStatus
from app.domain.transitions import assert_kitchen_item_transition, assert_order_transition
from app.services.money import line_amounts


def test_qr_order_cannot_skip_confirmation() -> None:
    with pytest.raises(AppError) as exc:
        assert_order_transition(OrderStatus.PENDING_CONFIRMATION, OrderStatus.COMPLETED)
    assert exc.value.status == 409


def test_accept_from_pending_is_allowed() -> None:
    assert_order_transition(OrderStatus.PENDING_CONFIRMATION, OrderStatus.ACCEPTED)


def test_kitchen_cannot_skip_preparing() -> None:
    with pytest.raises(AppError):
        assert_kitchen_item_transition(KitchenItemStatus.NEW, KitchenItemStatus.READY)


def test_money_rounding_half_up() -> None:
    subtotal, tax, total = line_amounts(999, 1, 1000)
    assert subtotal == 999
    assert tax == 100
    assert total == 1099
