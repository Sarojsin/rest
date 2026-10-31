from fastapi import APIRouter, Depends, Header
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.db.session import get_db
from app.models.identity import Restaurant
from app.models.tables import RestaurantTable
from app.schemas.public import (
    PublicMenuOut,
    PublicOrderStatusOut,
    PublicServiceCallOut,
    SubmitQrOrderRequest,
    SubmitQrOrderResponse,
)
from app.services import menu as menu_service
from app.services import orders as order_service
from app.services import service_calls as service_call_service

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
    restaurant = db.get(Restaurant, order.restaurant_id)
    out = order_service.order_to_out(order)
    return PublicOrderStatusOut(
        order_id=order.id,
        status=order.status,
        restaurant_name=restaurant.name if restaurant else "",
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
        currency_code=out.currency_code,
    )
from app.schemas.public_extra import CancelOrderRequest, RateOrderRequest, PublicBillOut, PublicBillItemOut
from app.services import billing as billing_service


@router.get("/orders/{status_token}/bill", response_model=PublicBillOut)
def get_public_bill(status_token: str, db: Session = Depends(get_db)) -> PublicBillOut:
    order = order_service.get_public_order_status(db, status_token)
    bill = billing_service.get_session_bill(db, order.restaurant_id, order.dining_session_id) if order.dining_session_id else None
    if bill is None:
        raise AppError(404, "BILL_NOT_FOUND", "Not found", "No bill is available yet. Please ask staff to issue the bill.")
    items = []
    for bi in bill.items:
        items.append(
            PublicBillItemOut(
                name=bi.description_snapshot,
                quantity=bi.quantity,
                unit_price_minor=bi.unit_price_minor,
                line_total_minor=bi.line_total_minor,
                currency_code=bill.currency_code,
            )
        )
    payments = [{"id": str(p.id), "method": p.method, "status": p.status, "amount_minor": p.amount_minor} for p in bill.payments]
    return PublicBillOut(
        bill_id=str(bill.id),
        status=bill.status,
        currency_code=bill.currency_code,
        subtotal_minor=bill.subtotal_minor,
        tax_minor=bill.tax_minor,
        total_minor=bill.total_minor,
        paid_minor=bill.paid_minor,
        balance_due_minor=bill.balance_due_minor,
        items=items,
        payments=payments,
    )


@router.post("/orders/{status_token}/cancel")
def cancel_order_public(status_token: str, payload: CancelOrderRequest, db: Session = Depends(get_db)) -> dict:
    order = order_service.cancel_public_order(db, status_token, payload.reason)
    return {"order_id": str(order.id), "status": order.status}


@router.post("/orders/{status_token}/rate")
def rate_order_public(status_token: str, payload: RateOrderRequest, db: Session = Depends(get_db)) -> dict:
    return order_service.rate_public_order(db, status_token, payload.rating, payload.comment)


def _service_call_out(call, *, deduplicated: bool = False) -> PublicServiceCallOut:
    return PublicServiceCallOut(
        id=call.id,
        status=call.status,
        requested_at=call.created_at.isoformat(),
        acknowledged_at=call.acknowledged_at.isoformat() if call.acknowledged_at else None,
        deduplicated=deduplicated,
    )


@router.post("/qr/{qr_token}/service-calls", response_model=PublicServiceCallOut)
def call_waiter(qr_token: str, db: Session = Depends(get_db)) -> PublicServiceCallOut:
    call, created = service_call_service.create_service_call(db, qr_token)
    return _service_call_out(call, deduplicated=not created)


@router.get("/qr/{qr_token}/service-calls/latest")
def latest_service_call(qr_token: str, db: Session = Depends(get_db)) -> dict:
    call = service_call_service.latest_service_call_for_qr(db, qr_token)
    return {"call": _service_call_out(call).model_dump() if call else None}
