"""Platform (Super Admin) bounded context.

PA-0 owns the separate platform identity, session, invite, and audit tables.
Tenant data is reached only through the documented
``platform -> tenancy : services.platform_directory`` edge.
"""

from app.modules.platform import models  # noqa: F401  (register with Base.metadata)
