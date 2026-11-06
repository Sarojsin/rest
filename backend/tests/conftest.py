"""Shared pytest configuration.

Guarantees every bounded-context model is registered with the SQLAlchemy
registry and that all mappers are configured before any test runs. Several
modules expose relationships that span contexts (e.g. ``Restaurant.branches``),
so importing the registry alone is not always enough when a test instantiates
those models directly.
"""

from __future__ import annotations

import app.modules  # noqa: F401  (imports every module's models)

# Importing the registry is normally sufficient, but importing the packages
# that own cross-context relationships makes registration order-independent.
import app.modules.audit.models  # noqa: F401,E402
import app.modules.billing.models  # noqa: F401,E402
import app.modules.branches.models  # noqa: F401,E402
import app.modules.catalog.models  # noqa: F401,E402
import app.modules.employees.models  # noqa: F401,E402
import app.modules.identity.models  # noqa: F401,E402
import app.modules.inventory.models  # noqa: F401,E402
import app.modules.kitchen.models  # noqa: F401,E402
import app.modules.loyalty.models  # noqa: F401,E402
import app.modules.notifications.models  # noqa: F401,E402
import app.modules.operations.models  # noqa: F401,E402
import app.modules.payments.models  # noqa: F401,E402
import app.modules.platform.models  # noqa: F401,E402
import app.modules.reviews.models  # noqa: F401,E402
import app.modules.service_calls.models  # noqa: F401,E402
import app.modules.subscriptions.models  # noqa: F401,E402
import app.modules.tenancy.models  # noqa: F401,E402
from sqlalchemy.orm import configure_mappers  # noqa: E402

configure_mappers()