from app.shared.enums import OrderStatus
from app.shared.errors import AppError

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


def assert_order_transition(current: OrderStatus, nxt: OrderStatus) -> None:
    permitted = ORDER_TRANSITIONS.get(current, set())
    if nxt not in permitted:
        raise AppError(
            409,
            "ORDER_STATE_CONFLICT",
            "Order state conflict",
            f"Cannot transition from {current} to {nxt}.",
        )
