"""Platform API composition (PA-0.14).

All platform routes carry the CSRF/Origin guard. The guard is applied at the
composition layer so no module router can accidentally be mounted unprotected.
"""

from fastapi import APIRouter, Depends

from app.modules.platform.csrf import platform_request_guard
from app.modules.platform.router_auth import router as platform_auth_router

platform_router = APIRouter(dependencies=[Depends(platform_request_guard)])
platform_router.include_router(platform_auth_router)
