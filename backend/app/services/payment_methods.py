import uuid as uuid_mod
from pathlib import Path
from uuid import UUID

from fastapi import UploadFile
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import AppError
from app.domain.enums import PaymentMethodKind
from app.models.billing import Payment, PaymentMethodConfig
from app.models.identity import RestaurantMembership
from app.schemas.staff import PaymentMethodOut, PaymentMethodPatch, PaymentMethodWrite
from app.services.audit import record_audit

# Actual file signatures, never trust the client-declared content type alone.
_MAGIC_PNG = b"\x89PNG\r\n\x1a\n"
_MAGIC_JPEG = b"\xff\xd8\xff"
_MAGIC_WEBP = b"RIFF"

_MEDIA_TYPES = {
    "png": "image/png",
    "jpg": "image/jpeg",
    "webp": "image/webp",
}


def _qr_directory() -> Path:
    return Path(settings.uploads_dir) / "payment_qr"


def payment_method_out(method: PaymentMethodConfig) -> PaymentMethodOut:
    has_image = bool(method.qr_image_name and method.qr_image_ext)
    return PaymentMethodOut(
        id=method.id,
        label=method.label,
        kind=method.kind,
        account_hint=method.account_hint,
        instructions=method.instructions,
        is_active=method.is_active,
        display_order=method.display_order,
        has_qr_image=has_image,
        qr_image_url=f"/api/v1/payment-methods/{method.id}/qr-image" if has_image else None,
    )


def list_methods(
    db: Session, restaurant_id: UUID, include_inactive: bool
) -> list[PaymentMethodConfig]:
    stmt = (
        select(PaymentMethodConfig)
        .where(PaymentMethodConfig.restaurant_id == restaurant_id)
        .order_by(PaymentMethodConfig.display_order, PaymentMethodConfig.created_at)
    )
    methods = db.scalars(stmt).unique().all()
    if not include_inactive:
        methods = [m for m in methods if m.is_active]
    return list(methods)


def _load_method(
    db: Session, restaurant_id: UUID, method_id: UUID
) -> PaymentMethodConfig:
    method = db.scalar(
        select(PaymentMethodConfig).where(
            PaymentMethodConfig.id == method_id,
            PaymentMethodConfig.restaurant_id == restaurant_id,
        )
    )
    if method is None:
        raise AppError(
            404, "PAYMENT_METHOD_NOT_FOUND", "Not found", "Payment method was not found."
        )
    return method


def _ensure_unique_label(
    db: Session, restaurant_id: UUID, label: str, exclude_id: UUID | None = None
) -> None:
    stmt = select(PaymentMethodConfig).where(
        PaymentMethodConfig.restaurant_id == restaurant_id,
        PaymentMethodConfig.label == label,
    )
    if exclude_id is not None:
        stmt = stmt.where(PaymentMethodConfig.id != exclude_id)
    if db.scalar(stmt) is not None:
        raise AppError(
            409, "METHOD_LABEL_EXISTS", "Label in use", "A method with this label already exists."
        )


def create_method(
    db: Session, membership: RestaurantMembership, payload: PaymentMethodWrite
) -> PaymentMethodConfig:
    _ensure_unique_label(db, membership.restaurant_id, payload.label)
    method = PaymentMethodConfig(
        restaurant_id=membership.restaurant_id,
        label=payload.label,
        kind=payload.kind,
        account_hint=payload.account_hint,
        instructions=payload.instructions,
        is_active=payload.is_active,
        display_order=payload.display_order,
    )
    db.add(method)
    record_audit(
        db,
        restaurant_id=membership.restaurant_id,
        action="settings.payment_method_upsert",
        entity_type="payment_method",
        entity_id=method.id,
        actor_user_id=membership.user_id,
        actor_membership_id=membership.id,
        detail=f"label={payload.label};kind={payload.kind}",
    )
    db.commit()
    return _load_method(db, membership.restaurant_id, method.id)


def update_method(
    db: Session,
    membership: RestaurantMembership,
    method_id: UUID,
    payload: PaymentMethodPatch,
) -> PaymentMethodConfig:
    method = _load_method(db, membership.restaurant_id, method_id)
    if payload.label is not None and payload.label != method.label:
        _ensure_unique_label(db, membership.restaurant_id, payload.label, exclude_id=method.id)
    changes = []
    for field, value in (
        ("label", payload.label),
        ("account_hint", payload.account_hint),
        ("instructions", payload.instructions),
        ("is_active", payload.is_active),
        ("display_order", payload.display_order),
    ):
        if value is not None:
            setattr(method, field, value)
            changes.append(f"{field}={value}")
    if changes:
        record_audit(
            db,
            restaurant_id=membership.restaurant_id,
            action="settings.payment_method_upsert",
            entity_type="payment_method",
            entity_id=method.id,
            actor_user_id=membership.user_id,
            actor_membership_id=membership.id,
            detail=";".join(changes),
        )
    db.commit()
    return _load_method(db, membership.restaurant_id, method_id)


def delete_method(
    db: Session, membership: RestaurantMembership, method_id: UUID
) -> None:
    method = _load_method(db, membership.restaurant_id, method_id)
    used = db.scalar(
        select(Payment.id).where(
            Payment.restaurant_id == membership.restaurant_id,
            Payment.method == method.label,
        )
    )
    if used is not None:
        raise AppError(
            409,
            "METHOD_IN_USE",
            "Method in use",
            "This method has recorded payments. Deactivate it instead of deleting.",
        )
    record_audit(
        db,
        restaurant_id=membership.restaurant_id,
        action="settings.payment_method_delete",
        entity_type="payment_method",
        entity_id=method.id,
        actor_user_id=membership.user_id,
        actor_membership_id=membership.id,
        detail=f"label={method.label}",
    )
    _remove_qr_file(method)
    db.execute(
        delete(PaymentMethodConfig).where(PaymentMethodConfig.id == method.id)
    )
    db.commit()


def _remove_qr_file(method: PaymentMethodConfig) -> None:
    if not (method.qr_image_name and method.qr_image_ext):
        return
    path = _qr_directory() / f"{method.qr_image_name}.{method.qr_image_ext}"
    try:
        path.unlink(missing_ok=True)
    except OSError:
        pass


def validate_qr_upload(upload: UploadFile) -> str:
    """Return the validated file extension or raise a stable domain error."""
    extension = Path(upload.filename or "").suffix.lstrip(".").lower()
    canonical = {"jpeg": "jpg"}.get(extension, extension)
    if canonical not in {"png", "jpg", "webp"}:
        raise AppError(
            422,
            "UNSUPPORTED_IMAGE_TYPE",
            "Unsupported image type",
            "QR images must be PNG, JPEG, or WebP.",
        )
    header = upload.file.read(16)
    upload.file.seek(0)
    if header.startswith(_MAGIC_PNG):
        actual = "png"
    elif header.startswith(_MAGIC_JPEG):
        actual = "jpg"
    elif header[:4] == _MAGIC_WEBP and header[8:12] == b"WEBP":
        actual = "webp"
    else:
        actual = None
    if actual is None or actual != canonical:
        raise AppError(
            422,
            "IMAGE_SIGNATURE_MISMATCH",
            "Invalid image",
            "The file content does not match its image type.",
        )
    return canonical


def save_qr_image(
    db: Session,
    membership: RestaurantMembership,
    method_id: UUID,
    upload: UploadFile,
) -> PaymentMethodConfig:
    method = _load_method(db, membership.restaurant_id, method_id)
    if method.kind != PaymentMethodKind.QR:
        raise AppError(
            422, "NOT_QR_METHOD", "Not a QR method", "This method does not use a QR image."
        )
    extension = validate_qr_upload(upload)
    data = upload.file.read(settings.max_qr_image_bytes + 1)
    if len(data) == 0:
        raise AppError(422, "EMPTY_IMAGE", "Empty file", "The uploaded image is empty.")
    if len(data) > settings.max_qr_image_bytes:
        raise AppError(
            413,
            "IMAGE_TOO_LARGE",
            "Image too large",
            "QR images must be 2 MB or smaller.",
        )

    directory = _qr_directory()
    directory.mkdir(parents=True, exist_ok=True)
    _remove_qr_file(method)
    name = uuid_mod.uuid4().hex
    (directory / f"{name}.{extension}").write_bytes(data)

    method.qr_image_name = name
    method.qr_image_ext = extension
    record_audit(
        db,
        restaurant_id=membership.restaurant_id,
        action="settings.payment_method_upsert",
        entity_type="payment_method",
        entity_id=method.id,
        actor_user_id=membership.user_id,
        actor_membership_id=membership.id,
        detail=f"label={method.label};qr_image_replaced=true",
    )
    db.commit()
    return _load_method(db, membership.restaurant_id, method.id)


def open_qr_file(
    db: Session, restaurant_id: UUID, method_id: UUID
) -> tuple[Path, str]:
    method = _load_method(db, restaurant_id, method_id)
    if not (method.qr_image_name and method.qr_image_ext):
        raise AppError(404, "QR_IMAGE_NOT_FOUND", "Not found", "No QR image is set.")
    media_type = _MEDIA_TYPES.get(method.qr_image_ext, "application/octet-stream")
    return _qr_directory() / f"{method.qr_image_name}.{method.qr_image_ext}", media_type
