"""Platform API composition (PA-0.14 / PA-1).

All platform routes carry the CSRF/Origin guard. The guard is applied at the
composition layer so no module router can accidentally be mounted unprotected.
"""

from fastapi import APIRouter, Depends

import app.modules  # noqa: F401  (resolve cross-module FK/relationship names)

from app.api.platform.router_audit import router as platform_audit_router
from app.api.platform.router_billing import router as platform_billing_router
from app.api.platform.router_dashboard import router as platform_dashboard_router
from app.api.platform.router_plans import router as platform_plans_router
from app.api.platform.router_platform_users import router as platform_users_router
from app.api.platform.router_self_service import router as platform_self_service_router
from app.api.platform.router_settings import router as platform_settings_router
from app.api.platform.router_subscriptions import router as platform_subscriptions_router
from app.api.platform.router_tenants import router as platform_tenants_router
from app.modules.platform.csrf import platform_request_guard
from app.modules.platform.router_auth import router as platform_auth_router

platform_router = APIRouter(dependencies=[Depends(platform_request_guard)])
platform_router.include_router(platform_auth_router)
platform_router.include_router(platform_dashboard_router)
platform_router.include_router(platform_tenants_router)
platform_router.include_router(platform_plans_router)
platform_router.include_router(platform_subscriptions_router)
platform_router.include_router(platform_billing_router)
platform_router.include_router(platform_users_router)
platform_router.include_router(platform_self_service_router)
platform_router.include_router(platform_audit_router)
platform_router.include_router(platform_settings_router)
