from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import Actor, require_permission
from app.db.session import get_db
from app.schemas.staff import TableCreate, TableOut, TableUpdate
from app.services import tables as table_service

router = APIRouter(tags=["tables"])


@router.get("/tables", response_model=list[TableOut])
def list_tables(
    include_archived: bool = Query(default=False),
    actor: Actor = Depends(require_permission("orders.read")),
    db: Session = Depends(get_db),
) -> list[TableOut]:
    return table_service.list_tables(
        db, actor.restaurant_id, include_archived=include_archived
    )


@router.post("/tables", response_model=TableOut)
def create_table(
    payload: TableCreate,
    actor: Actor = Depends(require_permission("tables.configure")),
    db: Session = Depends(get_db),
) -> TableOut:
    return table_service.create_table(db, actor.membership, payload)


@router.patch("/tables/{table_id}", response_model=TableOut)
def update_table(
    table_id: UUID,
    payload: TableUpdate,
    actor: Actor = Depends(require_permission("tables.configure")),
    db: Session = Depends(get_db),
) -> TableOut:
    return table_service.update_table(db, actor.membership, table_id, payload)


@router.post("/tables/{table_id}/archive", response_model=TableOut)
def archive_table(
    table_id: UUID,
    actor: Actor = Depends(require_permission("tables.configure")),
    db: Session = Depends(get_db),
) -> TableOut:
    return table_service.archive_table(db, actor.membership, table_id)


@router.post("/tables/{table_id}/restore", response_model=TableOut)
def restore_table(
    table_id: UUID,
    actor: Actor = Depends(require_permission("tables.configure")),
    db: Session = Depends(get_db),
) -> TableOut:
    return table_service.restore_table(db, actor.membership, table_id)


@router.post("/tables/{table_id}/qr/rotate")
def rotate_qr(
    table_id: UUID,
    actor: Actor = Depends(require_permission("tables.configure")),
    db: Session = Depends(get_db),
) -> dict:
    token = table_service.rotate_qr(db, actor.membership, table_id)
    return {"qr_token": token}
