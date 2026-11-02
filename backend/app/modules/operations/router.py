"""Operations module router — composition of tables + orders sub-routers."""

from fastapi import APIRouter

from app.modules.operations.router_orders import router as orders_router
from app.modules.operations.router_tables import router as tables_router

router = APIRouter()
router.include_router(orders_router)
router.include_router(tables_router)
