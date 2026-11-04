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
    # Phase 11-16 modules
    "branches.read",
    "branches.create",
    "branches.update",
    "inventory.read",
    "inventory.manage",
    "employees.read",
    "employees.create",
    "employees.update",
    "shifts.read",
    "shifts.create",
    "loyalty.read",
    "loyalty.manage",
    "loyalty.redeem",
    "reviews.read",
    "reviews.create",
    "reviews.respond",
    "subscriptions.read",
    "subscriptions.create",
    "subscriptions.manage",
}

MANAGER = OWNER.copy()

WAITER = {
    "orders.read",
    "orders.create",
    "orders.confirm_qr",
    "orders.serve",
    "kitchen.read",
    "tables.manage",
    "branches.read",
    "inventory.read",
    "employees.read",
    "shifts.read",
    "loyalty.read",
    "reviews.read",
    "reviews.create",
}

KITCHEN = {
    "orders.read",
    "kitchen.read",
    "kitchen.update",
    "inventory.read",
}

CASHIER = {
    "orders.read",
    "bills.issue",
    "payments.record",
    "reports.read",
    "kitchen.read",
    "branches.read",
    "loyalty.read",
    "loyalty.redeem",
    "reviews.read",
    "subscriptions.read",
}

ROLE_PERMISSIONS = {
    "owner": OWNER,
    "manager": MANAGER,
    "waiter": WAITER,
    "kitchen": KITCHEN,
    "cashier": CASHIER,
}
