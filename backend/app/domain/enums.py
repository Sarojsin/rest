from enum import StrEnum


class RestaurantStatus(StrEnum):
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    CLOSED = "CLOSED"


class UserStatus(StrEnum):
    ACTIVE = "ACTIVE"
    LOCKED = "LOCKED"
    DISABLED = "DISABLED"


class MembershipStatus(StrEnum):
    INVITED = "INVITED"
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    REVOKED = "REVOKED"


class TableStatus(StrEnum):
    ACTIVE = "ACTIVE"
    OUT_OF_SERVICE = "OUT_OF_SERVICE"
    ARCHIVED = "ARCHIVED"


class DiningSessionStatus(StrEnum):
    OPEN = "OPEN"
    CHECKOUT_PENDING = "CHECKOUT_PENDING"
    CLOSED = "CLOSED"
    VOID = "VOID"


class MenuItemStatus(StrEnum):
    DRAFT = "DRAFT"
    PUBLISHED = "PUBLISHED"
    UNAVAILABLE = "UNAVAILABLE"
    ARCHIVED = "ARCHIVED"


class OrderSource(StrEnum):
    WAITER = "WAITER"
    CUSTOMER_QR = "CUSTOMER_QR"


class OrderStatus(StrEnum):
    PENDING_CONFIRMATION = "PENDING_CONFIRMATION"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"
    COMPLETED = "COMPLETED"


class KitchenTicketStatus(StrEnum):
    NEW = "NEW"
    IN_PROGRESS = "IN_PROGRESS"
    READY = "READY"
    CANCELLED = "CANCELLED"


class KitchenItemStatus(StrEnum):
    NEW = "NEW"
    PREPARING = "PREPARING"
    READY = "READY"
    SERVED = "SERVED"
    CANCELLED = "CANCELLED"


class BillStatus(StrEnum):
    OPEN = "OPEN"
    ISSUED = "ISSUED"
    PARTIALLY_PAID = "PARTIALLY_PAID"
    PAID = "PAID"
    VOID = "VOID"


class PaymentStatus(StrEnum):
    INITIATED = "INITIATED"
    PENDING = "PENDING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class PaymentMethodKind(StrEnum):
    """What a configured payment method does at checkout.

    CASH is recorded directly by authorized staff. QR shows an owner-uploaded
    static QR image for the customer to scan; displaying it never settles the
    bill — staff must verify the received amount before recording payment.
    """

    CASH = "CASH"
    QR = "QR"


class ServiceCallKind(StrEnum):
    GUEST = "GUEST"
    KITCHEN = "KITCHEN"


class ServiceCallStatus(StrEnum):
    REQUESTED = "REQUESTED"
    ACKNOWLEDGED = "ACKNOWLEDGED"
