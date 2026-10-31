from datetime import UTC, datetime
from re import Pattern
from re import compile as re_compile
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.core.security import hash_token, new_token
from app.domain.enums import DiningSessionStatus, OrderStatus, TableStatus
from app.models.identity import RestaurantMembership
from app.models.orders import Order
from app.models.tables import DiningSession, RestaurantTable, TableQrCode
from app.schemas.staff import TableCreate, TableOut, TableUpdate
from app.services.audit import record_audit

_CODE_PATTERN: Pattern[str] = re_compile(r"^[A-Z0-9-]{1,32}$")

_EDITABLE_STATUSES = {TableStatus.ACTIVE, TableStatus.OUT_OF_SERVICE}


def _load_table(db: Session, restaurant_id: UUID, table_id: UUID) -> RestaurantTable:
    table = db.scalar(
        select(RestaurantTable).where(
            RestaurantTable.id == table_id,
            RestaurantTable.restaurant_id == restaurant_id,
        )
    )
    if table is None:
        raise AppError(404, "TABLE_NOT_FOUND", "Not found", "Table was not found.")
    return table


# ── Read model ────────────────────────────────────────────────────────────────


def _table_out(
    db: Session,
    restaurant_id: UUID,
    table: RestaurantTable,
    *,
    sessions_by_table: dict[UUID, DiningSession] | None = None,
    pending_counts: dict[UUID, int] | None = None,
    active_qr_by_table: dict[UUID, TableQrCode] | None = None,
) -> TableOut:
    if sessions_by_table is None:
        sessions_by_table = _open_sessions(db, restaurant_id)
    if pending_counts is None:
        pending_counts = _pending_order_counts(db, restaurant_id)
    if active_qr_by_table is None:
        active_qr_by_table = _active_qr_tokens(db, restaurant_id)
    session = sessions_by_table.get(table.id)
    occupancy = "AVAILABLE"
    if session and session.status == DiningSessionStatus.CHECKOUT_PENDING:
        occupancy = "CHECKOUT"
    elif session:
        occupancy = "OCCUPIED"
    qr = active_qr_by_table.get(table.id)
    return TableOut(
        id=table.id,
        table_code=table.table_code,
        display_name=table.display_name,
        seating_capacity=table.seating_capacity,
        status=table.status,
        sort_order=table.sort_order,
        occupancy=occupancy,
        active_session_id=session.id if session else None,
        pending_qr_count=int((pending_counts or {}).get(table.id, 0)),
        qr_token=qr.token_preview if qr else None,
    )


def _open_sessions(
    db: Session, restaurant_id: UUID
) -> dict[UUID, DiningSession]:
    sessions = db.scalars(
        select(DiningSession).where(
            DiningSession.restaurant_id == restaurant_id,
            DiningSession.status.in_(
                [DiningSessionStatus.OPEN, DiningSessionStatus.CHECKOUT_PENDING]
            ),
        )
    ).all()
    return {s.table_id: s for s in sessions}


def _pending_order_counts(db: Session, restaurant_id: UUID) -> dict[UUID, int]:
    return dict(
        db.execute(
            select(Order.table_id, func.count(Order.id))
            .where(
                Order.restaurant_id == restaurant_id,
                Order.status == OrderStatus.PENDING_CONFIRMATION,
            )
            .group_by(Order.table_id)
        ).all()
    )


def _active_qr_tokens(db: Session, restaurant_id: UUID) -> dict[UUID, TableQrCode]:
    qr_rows = db.scalars(
        select(TableQrCode).where(
            TableQrCode.restaurant_id == restaurant_id,
            TableQrCode.status == "ACTIVE",
        )
    ).all()
    return {qr.table_id: qr for qr in qr_rows}


def list_tables(
    db: Session, restaurant_id: UUID, include_archived: bool = False
) -> list[TableOut]:
    stmt = (
        select(RestaurantTable)
        .where(RestaurantTable.restaurant_id == restaurant_id)
        .order_by(RestaurantTable.sort_order, RestaurantTable.table_code)
    )
    if not include_archived:
        stmt = stmt.where(RestaurantTable.status != TableStatus.ARCHIVED)
    tables = db.scalars(stmt).all()

    sessions_by_table = _open_sessions(db, restaurant_id)
    pending_counts = _pending_order_counts(db, restaurant_id)
    active_qr_by_table = _active_qr_tokens(db, restaurant_id)

    return [
        _table_out(
            db,
            restaurant_id,
            table,
            sessions_by_table=sessions_by_table,
            pending_counts=pending_counts,
            active_qr_by_table=active_qr_by_table,
        )
        for table in tables
    ]


# ── QR issuance (shared by create / rotate / restore) ─────────────────────────


def _issue_qr(db: Session, restaurant_id: UUID, table: RestaurantTable) -> str:
    for qr in db.scalars(
        select(TableQrCode).where(
            TableQrCode.table_id == table.id, TableQrCode.status == "ACTIVE"
        )
    ):
        qr.status = "REVOKED"
        qr.revoked_at = datetime.now(UTC)
    raw = new_token(24)
    db.add(
        TableQrCode(
            restaurant_id=restaurant_id,
            table_id=table.id,
            token_hash=hash_token(raw),
            token_preview=raw,
            status="ACTIVE",
        )
    )
    return raw


# ── Write operations ──────────────────────────────────────────────────────────


def _validate_code(code: str) -> str:
    code = code.strip().upper()
    if not _CODE_PATTERN.match(code):
        raise AppError(
            422,
            "TABLE_CODE_INVALID",
            "Invalid table code",
            "Use 1-32 characters: letters, numbers, or dashes (e.g. T7 or PATIO-1).",
        )
    return code


def _ensure_code_available(
    db: Session, restaurant_id: UUID, code: str, exclude_id: UUID | None = None
) -> None:
    stmt = select(RestaurantTable.id).where(
        RestaurantTable.restaurant_id == restaurant_id,
        func.upper(RestaurantTable.table_code) == code,
    )
    if exclude_id is not None:
        stmt = stmt.where(RestaurantTable.id != exclude_id)
    if db.scalar(stmt) is not None:
        raise AppError(
            409,
            "TABLE_CODE_EXISTS",
            "Table code in use",
            f"Table code {code} is already used in this restaurant.",
        )


def create_table(
    db: Session, membership: RestaurantMembership, payload: TableCreate
) -> TableOut:
    code = _validate_code(payload.table_code)
    _ensure_code_available(db, membership.restaurant_id, code)

    if payload.sort_order is None:
        max_order = db.scalar(
            select(func.max(RestaurantTable.sort_order)).where(
                RestaurantTable.restaurant_id == membership.restaurant_id
            )
        )
        sort_order = (max_order or 0) + 1
    else:
        sort_order = payload.sort_order

    table = RestaurantTable(
        restaurant_id=membership.restaurant_id,
        table_code=code,
        display_name=payload.display_name.strip(),
        seating_capacity=payload.seating_capacity,
        status=TableStatus.ACTIVE,
        sort_order=sort_order,
    )
    db.add(table)
    db.flush()

    raw_token = _issue_qr(db, membership.restaurant_id, table)
    record_audit(
        db,
        restaurant_id=membership.restaurant_id,
        action="tables.create",
        entity_type="table",
        entity_id=str(table.id),
        actor_user_id=membership.user_id,
        actor_membership_id=membership.id,
        detail=f"code={code};name={table.display_name};seats={payload.seating_capacity or ''}",
    )
    db.commit()

    out = _table_out(db, membership.restaurant_id, table)
    out.qr_token = raw_token
    return out


def update_table(
    db: Session,
    membership: RestaurantMembership,
    table_id: UUID,
    payload: TableUpdate,
) -> TableOut:
    table = _load_table(db, membership.restaurant_id, table_id)
    if table.status == TableStatus.ARCHIVED:
        raise AppError(
            409,
            "TABLE_ARCHIVED",
            "Table archived",
            "Restore this table before editing it.",
        )

    changes: list[str] = []
    if payload.display_name is not None:
        name = payload.display_name.strip()
        if name != table.display_name:
            table.display_name = name
            changes.append(f"name={name}")
    if payload.seating_capacity is not None:
        if payload.seating_capacity != table.seating_capacity:
            table.seating_capacity = payload.seating_capacity
            changes.append(f"seats={payload.seating_capacity}")
    if payload.sort_order is not None:
        if payload.sort_order != table.sort_order:
            table.sort_order = payload.sort_order
            changes.append(f"sort={payload.sort_order}")
    if payload.status is not None:
        new_status = TableStatus(payload.status)
        if new_status != TableStatus(table.status):
            table.status = new_status
            changes.append(f"status={new_status}")

    if changes:
        record_audit(
            db,
            restaurant_id=membership.restaurant_id,
            action="tables.update",
            entity_type="table",
            entity_id=str(table.id),
            actor_user_id=membership.user_id,
            actor_membership_id=membership.id,
            detail=";".join(changes),
        )
        db.commit()
    return _table_out(db, membership.restaurant_id, table)


def _ensure_not_in_active_use(db: Session, restaurant_id: UUID, table: RestaurantTable) -> None:
    session = _open_sessions(db, restaurant_id).get(table.id)
    if session is not None:
        raise AppError(
            409,
            "TABLE_OCCUPIED",
            "Table occupied",
            "Close the open dining session before archiving this table.",
        )
    pending = db.scalar(
        select(Order.id).where(
            Order.restaurant_id == restaurant_id,
            Order.table_id == table.id,
            Order.status == OrderStatus.PENDING_CONFIRMATION,
        )
    )
    if pending is not None:
        raise AppError(
            409,
            "TABLE_HAS_PENDING_ORDERS",
            "Pending orders",
            "Confirm or reject pending orders before archiving this table.",
        )


def archive_table(
    db: Session,
    membership: RestaurantMembership,
    table_id: UUID,
) -> TableOut:
    table = _load_table(db, membership.restaurant_id, table_id)
    if table.status == TableStatus.ARCHIVED:
        raise AppError(
            409, "ALREADY_ARCHIVED", "Already archived", "This table is already archived."
        )
    _ensure_not_in_active_use(db, membership.restaurant_id, table)

    table.status = TableStatus.ARCHIVED
    for qr in db.scalars(
        select(TableQrCode).where(
            TableQrCode.table_id == table.id, TableQrCode.status == "ACTIVE"
        )
    ):
        qr.status = "REVOKED"
        qr.revoked_at = datetime.now(UTC)

    record_audit(
        db,
        restaurant_id=membership.restaurant_id,
        action="tables.archive",
        entity_type="table",
        entity_id=str(table.id),
        actor_user_id=membership.user_id,
        actor_membership_id=membership.id,
        detail=f"code={table.table_code};qr_revoked=true",
    )
    db.commit()
    return _table_out(db, membership.restaurant_id, table)


def restore_table(
    db: Session,
    membership: RestaurantMembership,
    table_id: UUID,
) -> TableOut:
    table = _load_table(db, membership.restaurant_id, table_id)
    if table.status != TableStatus.ARCHIVED:
        raise AppError(
            409, "NOT_ARCHIVED", "Not archived", "Only archived tables can be restored."
        )

    table.status = TableStatus.ACTIVE
    db.flush()
    raw_token = _issue_qr(db, membership.restaurant_id, table)
    record_audit(
        db,
        restaurant_id=membership.restaurant_id,
        action="tables.restore",
        entity_type="table",
        entity_id=str(table.id),
        actor_user_id=membership.user_id,
        actor_membership_id=membership.id,
        detail=f"code={table.table_code};qr_reissued=true",
    )
    db.commit()

    out = _table_out(db, membership.restaurant_id, table)
    out.qr_token = raw_token
    return out


# ── QR rotation ───────────────────────────────────────────────────────────────


def rotate_qr(
    db: Session,
    membership: RestaurantMembership,
    table_id: UUID,
) -> str:
    table = _load_table(db, membership.restaurant_id, table_id)
    raw = _issue_qr(db, membership.restaurant_id, table)
    record_audit(
        db,
        restaurant_id=membership.restaurant_id,
        action="tables.rotate_qr",
        entity_type="table",
        entity_id=str(table.id),
        actor_user_id=membership.user_id,
        actor_membership_id=membership.id,
        detail=f"code={table.table_code}",
    )
    db.commit()
    return raw
