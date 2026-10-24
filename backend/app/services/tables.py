from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.security import new_token
from app.domain.enums import DiningSessionStatus, OrderStatus
from app.models.orders import Order
from app.models.tables import DiningSession, RestaurantTable, TableQrCode
from app.schemas.staff import TableOut


def list_tables(db: Session, restaurant_id: UUID) -> list[TableOut]:
    tables = db.scalars(
        select(RestaurantTable)
        .where(RestaurantTable.restaurant_id == restaurant_id)
        .order_by(RestaurantTable.sort_order, RestaurantTable.table_code)
    ).all()
    sessions = db.scalars(
        select(DiningSession).where(
            DiningSession.restaurant_id == restaurant_id,
            DiningSession.status.in_(
                [DiningSessionStatus.OPEN, DiningSessionStatus.CHECKOUT_PENDING]
            ),
        )
    ).all()
    session_by_table = {s.table_id: s for s in sessions}
    pending_counts = dict(
        db.execute(
            select(Order.table_id, func.count(Order.id))
            .where(
                Order.restaurant_id == restaurant_id,
                Order.status == OrderStatus.PENDING_CONFIRMATION,
            )
            .group_by(Order.table_id)
        ).all()
    )
    qr_rows = db.scalars(
        select(TableQrCode).where(
            TableQrCode.restaurant_id == restaurant_id, TableQrCode.status == "ACTIVE"
        )
    ).all()
    qr_by_table = {qr.table_id: qr for qr in qr_rows}

    result: list[TableOut] = []
    for table in tables:
        session = session_by_table.get(table.id)
        occupancy = "AVAILABLE"
        if session and session.status == DiningSessionStatus.CHECKOUT_PENDING:
            occupancy = "CHECKOUT"
        elif session:
            occupancy = "OCCUPIED"
        qr = qr_by_table.get(table.id)
        result.append(
            TableOut(
                id=table.id,
                table_code=table.table_code,
                display_name=table.display_name,
                seating_capacity=table.seating_capacity,
                status=table.status,
                sort_order=table.sort_order,
                occupancy=occupancy,
                active_session_id=session.id if session else None,
                pending_qr_count=int(pending_counts.get(table.id, 0)),
                qr_token=qr.token_preview if qr else None,
            )
        )
    return result


def rotate_qr(db: Session, restaurant_id: UUID, table_id: UUID) -> str:
    table = db.scalar(
        select(RestaurantTable).where(
            RestaurantTable.id == table_id, RestaurantTable.restaurant_id == restaurant_id
        )
    )
    if table is None:
        from app.core.errors import AppError

        raise AppError(404, "TABLE_NOT_FOUND", "Not found", "Table was not found.")
    from datetime import UTC, datetime

    from app.core.security import hash_token

    for qr in db.scalars(
        select(TableQrCode).where(TableQrCode.table_id == table_id, TableQrCode.status == "ACTIVE")
    ):
        qr.status = "REVOKED"
        qr.revoked_at = datetime.now(UTC)
    raw = new_token(24)
    db.add(
        TableQrCode(
            restaurant_id=restaurant_id,
            table_id=table_id,
            token_hash=hash_token(raw),
            token_preview=raw,
            status="ACTIVE",
        )
    )
    db.commit()
    return raw
