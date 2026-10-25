from fastapi import APIRouter

from app.api.v1.routes import (
    auth,
    kitchen,
    menu,
    orders,
    payment_methods,
    public,
    reports,
    restaurant,
    service_calls,
    tables,
)

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(public.router)
api_router.include_router(restaurant.router)
api_router.include_router(tables.router)
api_router.include_router(menu.router)
api_router.include_router(orders.router)
api_router.include_router(kitchen.router)
api_router.include_router(service_calls.router)
api_router.include_router(payment_methods.router)
api_router.include_router(reports.router)
