from fastapi import APIRouter, Depends, Header
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.db.session import get_db
from app.models.tables import RestaurantTable
from app.schemas.public import (
    PublicMenuOut,
    PublicOrderStatusOut,
    SubmitQrOrderRequest,
    SubmitQrOrderResponse,
)
from app.services import menu as menu_service
from app.services import orders as order_service

router = APIRouter(prefix="/public", tags=["public"])


def _idempotency_key(idempotency_key: str | None = Header(default=None, alias="Idempotency-Key")) -> str:
    if not idempotency_key or len(idempotency_key) < 8:
        raise AppError(
            400,
            "IDEMPOTENCY_KEY_REQUIRED",
            "Idempotency key required",
            "Provide an Idempotency-Key header of at least 8 characters.",
        )
    return idempotency_key


@router.get("/qr/{qr_token}/menu", response_model=PublicMenuOut)
def get_public_menu(qr_token: str, db: Session = Depends(get_db)) -> PublicMenuOut:
    qr, table = order_service.resolve_qr(db, qr_token)
    return menu_service.public_menu(db, qr.restaurant_id, table)


@router.post("/qr/{qr_token}/orders", response_model=SubmitQrOrderResponse)
def submit_qr_order(
    qr_token: str,
    payload: SubmitQrOrderRequest,
    db: Session = Depends(get_db),
    idempotency_key: str = Depends(_idempotency_key),
) -> SubmitQrOrderResponse:
    order, status_token = order_service.submit_qr_order(
        db,
        qr_token=qr_token,
        items=payload.items,
        customer_note=payload.customer_note,
        idempotency_key=idempotency_key,
    )
    out = order_service.order_to_out(order)
    if not status_token:
        return SubmitQrOrderResponse(order=out, status_token="", message="Duplicate submission returned.")
    return SubmitQrOrderResponse(order=out, status_token=status_token)


@router.get("/orders/{status_token}", response_model=PublicOrderStatusOut)
def get_order_status(status_token: str, db: Session = Depends(get_db)) -> PublicOrderStatusOut:
    order = order_service.get_public_order_status(db, status_token)
    table = db.get(RestaurantTable, order.table_id)
    out = order_service.order_to_out(order)
    return PublicOrderStatusOut(
        order_id=order.id,
        status=order.status,
        table_display_name=table.display_name if table else "Table",
        submitted_at=order.submitted_at.isoformat(),
        accepted_at=order.accepted_at.isoformat() if order.accepted_at else None,
        rejected_at=order.rejected_at.isoformat() if order.rejected_at else None,
        rejection_note=order.rejection_note,
        items=[
            {
                "name": item.item_name_snapshot,
                "quantity": item.quantity,
                "line_total_minor": item.line_total_minor,
            }
            for item in out.items
        ],
        total_minor=out.total_minor,
        currency_code=out.items[0].currency_code if out.items else "USD",
    )
