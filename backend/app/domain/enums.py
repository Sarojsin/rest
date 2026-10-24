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


class PaymentMethod(StrEnum):
    CASH = "CASH"
    ONLINE_PROVIDER = "ONLINE_PROVIDER"
