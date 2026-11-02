from app.shared.enums import BillStatus
from app.shared.errors import AppError

BILL_TRANSITIONS: dict[BillStatus, set[BillStatus]] = {
    BillStatus.OPEN: {BillStatus.ISSUED, BillStatus.VOID},
    BillStatus.ISSUED: {BillStatus.PARTIALLY_PAID, BillStatus.PAID, BillStatus.VOID},
    BillStatus.PARTIALLY_PAID: {BillStatus.PAID, BillStatus.VOID},
    BillStatus.PAID: set(),
    BillStatus.VOID: set(),
}


def assert_bill_transition(current: BillStatus, nxt: BillStatus) -> None:
    permitted = BILL_TRANSITIONS.get(current, set())
    if nxt not in permitted:
        raise AppError(
            409,
            "BILL_STATE_CONFLICT",
            "Bill state conflict",
            f"Cannot transition from {current} to {nxt}.",
        )
