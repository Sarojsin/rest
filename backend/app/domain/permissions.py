OWNER = {
    "orders.read",
    "orders.create",
    "orders.confirm_qr",
    "orders.serve",
    "orders.cancel",
    "kitchen.read",
    "kitchen.update",
    "bills.issue",
    "payments.record",
    "menu.manage",
    "tables.manage",
    "tables.configure",
    "reports.read",
    "staff.manage",
    "settings.manage",
    "audit.read",
}

MANAGER = OWNER.copy()

WAITER = {
    "orders.read",
    "orders.create",
    "orders.confirm_qr",
    "orders.serve",
    "kitchen.read",
    "tables.manage",
}

KITCHEN = {
    "orders.read",
    "kitchen.read",
    "kitchen.update",
}

CASHIER = {
    "orders.read",
    "bills.issue",
    "payments.record",
    "reports.read",
    "kitchen.read",
}

ROLE_PERMISSIONS = {
    "owner": OWNER,
    "manager": MANAGER,
    "waiter": WAITER,
    "kitchen": KITCHEN,
    "cashier": CASHIER,
}
