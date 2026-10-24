from app.core.errors import AppError
from app.domain.enums import BillStatus, KitchenItemStatus, OrderStatus

ORDER_TRANSITIONS: dict[OrderStatus, set[OrderStatus]] = {
    OrderStatus.PENDING_CONFIRMATION: {
        OrderStatus.ACCEPTED,
        OrderStatus.REJECTED,
        OrderStatus.CANCELLED,
    },
    OrderStatus.ACCEPTED: {OrderStatus.CANCELLED, OrderStatus.COMPLETED},
    OrderStatus.REJECTED: set(),
    OrderStatus.CANCELLED: set(),
    OrderStatus.COMPLETED: set(),
}

KITCHEN_ITEM_TRANSITIONS: dict[KitchenItemStatus, set[KitchenItemStatus]] = {
    KitchenItemStatus.NEW: {KitchenItemStatus.PREPARING, KitchenItemStatus.CANCELLED},
    KitchenItemStatus.PREPARING: {KitchenItemStatus.READY, KitchenItemStatus.CANCELLED},
    KitchenItemStatus.READY: {KitchenItemStatus.SERVED, KitchenItemStatus.CANCELLED},
    KitchenItemStatus.SERVED: set(),
    KitchenItemStatus.CANCELLED: set(),
}

BILL_TRANSITIONS: dict[BillStatus, set[BillStatus]] = {
    BillStatus.OPEN: {BillStatus.ISSUED, BillStatus.VOID},
    BillStatus.ISSUED: {BillStatus.PARTIALLY_PAID, BillStatus.PAID, BillStatus.VOID},
    BillStatus.PARTIALLY_PAID: {BillStatus.PAID, BillStatus.VOID},
    BillStatus.PAID: set(),
    BillStatus.VOID: set(),
}


def _assert_transition(current: str, nxt: str, allowed: dict, code: str, title: str) -> None:
    permitted = allowed.get(current, set())
    if nxt not in permitted:
        raise AppError(
            409,
            code,
            title,
            f"Cannot transition from {current} to {nxt}.",
        )


def assert_order_transition(current: OrderStatus, nxt: OrderStatus) -> None:
    _assert_transition(
        current, nxt, ORDER_TRANSITIONS, "ORDER_STATE_CONFLICT", "Order state conflict"
    )


def assert_kitchen_item_transition(current: KitchenItemStatus, nxt: KitchenItemStatus) -> None:
    _assert_transition(
        current,
        nxt,
        KITCHEN_ITEM_TRANSITIONS,
        "KITCHEN_STATE_CONFLICT",
        "Kitchen state conflict",
    )


def assert_bill_transition(current: BillStatus, nxt: BillStatus) -> None:
    _assert_transition(current, nxt, BILL_TRANSITIONS, "BILL_STATE_CONFLICT", "Bill state conflict")
