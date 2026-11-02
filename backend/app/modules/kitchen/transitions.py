from app.shared.enums import KitchenItemStatus
from app.shared.errors import AppError

KITCHEN_ITEM_TRANSITIONS: dict[KitchenItemStatus, set[KitchenItemStatus]] = {
    KitchenItemStatus.NEW: {KitchenItemStatus.PREPARING, KitchenItemStatus.CANCELLED},
    KitchenItemStatus.PREPARING: {KitchenItemStatus.READY, KitchenItemStatus.CANCELLED},
    KitchenItemStatus.READY: {KitchenItemStatus.SERVED, KitchenItemStatus.CANCELLED},
    KitchenItemStatus.SERVED: set(),
    KitchenItemStatus.CANCELLED: set(),
}


def assert_kitchen_item_transition(current: KitchenItemStatus, nxt: KitchenItemStatus) -> None:
    permitted = KITCHEN_ITEM_TRANSITIONS.get(current, set())
    if nxt not in permitted:
        raise AppError(
            409,
            "KITCHEN_STATE_CONFLICT",
            "Kitchen state conflict",
            f"Cannot transition from {current} to {nxt}.",
        )
