from uuid import UUID

from fastapi import APIRouter, Depends, File, Response, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.deps import Actor, get_actor, require_permission
from app.db.session import get_db
from app.schemas.staff import (
    PaymentMethodOut,
    PaymentMethodPatch,
    PaymentMethodWrite,
)
from app.services import payment_methods as methods_service

router = APIRouter(tags=["payment-methods"])


@router.get("/payment-methods", response_model=list[PaymentMethodOut])
def list_payment_methods(
    actor: Actor = Depends(get_actor),
    db: Session = Depends(get_db),
) -> list[PaymentMethodOut]:
    include_inactive = "settings.manage" in actor.permissions
    return [
        methods_service.payment_method_out(method)
        for method in methods_service.list_methods(
            db, actor.restaurant_id, include_inactive
        )
    ]


@router.post("/payment-methods", response_model=PaymentMethodOut)
def create_payment_method(
    payload: PaymentMethodWrite,
    actor: Actor = Depends(require_permission("settings.manage")),
    db: Session = Depends(get_db),
) -> PaymentMethodOut:
    method = methods_service.create_method(db, actor.membership, payload)
    return methods_service.payment_method_out(method)


@router.patch("/payment-methods/{method_id}", response_model=PaymentMethodOut)
def update_payment_method(
    method_id: UUID,
    payload: PaymentMethodPatch,
    actor: Actor = Depends(require_permission("settings.manage")),
    db: Session = Depends(get_db),
) -> PaymentMethodOut:
    method = methods_service.update_method(db, actor.membership, method_id, payload)
    return methods_service.payment_method_out(method)


@router.delete("/payment-methods/{method_id}", status_code=204)
def delete_payment_method(
    method_id: UUID,
    actor: Actor = Depends(require_permission("settings.manage")),
    db: Session = Depends(get_db),
) -> Response:
    methods_service.delete_method(db, actor.membership, method_id)
    return Response(status_code=204)


@router.post(
    "/payment-methods/{method_id}/qr-image", response_model=PaymentMethodOut
)
def upload_qr_image(
    method_id: UUID,
    image: UploadFile = File(...),
    actor: Actor = Depends(require_permission("settings.manage")),
    db: Session = Depends(get_db),
) -> PaymentMethodOut:
    method = methods_service.save_qr_image(db, actor.membership, method_id, image)
    return methods_service.payment_method_out(method)


@router.get("/payment-methods/{method_id}/qr-image")
def download_qr_image(
    method_id: UUID,
    actor: Actor = Depends(get_actor),
    db: Session = Depends(get_db),
) -> FileResponse:
    path, media_type = methods_service.open_qr_file(db, actor.restaurant_id, method_id)
    return FileResponse(path, media_type=media_type)
