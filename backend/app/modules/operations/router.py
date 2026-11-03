"""Operations module router — composition of tables + orders + dashboard sub-routers."""

from fastapi import APIRouter

from app.modules.operations.router_dashboard import router as dashboard_router
from app.modules.operations.router_orders import router as orders_router
from app.modules.operations.router_tables import router as tables_router

router = APIRouter()
router.include_router(dashboard_router)
router.include_router(orders_router)
router.include_router(tables_router)
