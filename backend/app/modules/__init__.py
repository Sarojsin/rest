"""Bounded-context module registry (D14).

Importing `app.modules` loads every module's models so SQLAlchemy can
resolve cross-module relationship string references at mapper
configuration time. Modules themselves must not import each other's
models — this registry is the one central place that touches all of them.
"""

from app.modules import (  # noqa: F401
    audit,
    billing,
    branches,
    catalog,
    employees,
    entitlements,
    identity,
    inventory,
    kitchen,
    loyalty,
    notifications,
    operations,
    payments,
    platform,
    reports,
    reviews,
    service_calls,
    subscriptions,
    tenancy,
)
