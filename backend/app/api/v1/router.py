"""Staff-realm API composition (api is a composition layer — 02 §2.1 rule 5).

Realm split plan: staff under /api/v1 (here), customer QR surface already
composed under /public in app/api/qr (becomes its own realm host in Phase 7),
platform realm arrives in Phase 5.
"""

from fastapi import APIRouter

from app.api.qr.router import router as qr_router
from app.modules.billing.router import router as billing_router
from app.modules.catalog.router import router as catalog_router
from app.modules.identity.router import router as identity_router
from app.modules.kitchen.router import router as kitchen_router
from app.modules.operations.router import router as operations_router
from app.modules.payments.router import router as payments_router
from app.modules.reports.router import router as reports_router
from app.modules.service_calls.router import router as service_calls_router
from app.modules.tenancy.router import router as tenancy_router

api_router = APIRouter()
api_router.include_router(identity_router)
api_router.include_router(qr_router)
api_router.include_router(tenancy_router)
api_router.include_router(operations_router)
api_router.include_router(catalog_router)
api_router.include_router(kitchen_router)
api_router.include_router(billing_router)
api_router.include_router(payments_router)
api_router.include_router(service_calls_router)
api_router.include_router(reports_router)
