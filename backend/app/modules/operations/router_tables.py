from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import (
    Actor,
    consume_tenant_limit,
    release_tenant_limit,
    require_permission,
    require_tenant_feature,
)
from app.db.session import get_db
from app.modules.operations.schemas import TableCreate, TableOut, TableUpdate
from app.modules.operations.services import tables as table_service

router = APIRouter(tags=["tables"])


@router.get("/tables", response_model=list[TableOut])
def list_tables(
    include_archived: bool = Query(default=False),
    actor: Actor = Depends(require_permission("orders.read")),
    db: Session = Depends(get_db),
) -> list[TableOut]:
    return table_service.list_tables(db, actor.restaurant_id, include_archived=include_archived)


@router.post(
    "/tables",
    response_model=TableOut,
    dependencies=[
        Depends(require_tenant_feature("qr_ordering")),
        Depends(consume_tenant_limit("tables")),
    ],
)
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


@router.post(
    "/tables/{table_id}/archive",
    response_model=TableOut,
    dependencies=[Depends(release_tenant_limit("tables"))],
)
def archive_table(
    table_id: UUID,
    actor: Actor = Depends(require_permission("tables.configure")),
    db: Session = Depends(get_db),
) -> TableOut:
    return table_service.archive_table(db, actor.membership, table_id)


@router.post(
    "/tables/{table_id}/restore",
    response_model=TableOut,
    dependencies=[
        Depends(require_tenant_feature("qr_ordering")),
        Depends(consume_tenant_limit("tables")),
    ],
)
def restore_table(
    table_id: UUID,
    actor: Actor = Depends(require_permission("tables.configure")),
    db: Session = Depends(get_db),
) -> TableOut:
    return table_service.restore_table(db, actor.membership, table_id)


@router.post(
    "/tables/{table_id}/qr/rotate",
    dependencies=[Depends(require_tenant_feature("qr_ordering"))],
)
def rotate_qr(
    table_id: UUID,
    actor: Actor = Depends(require_permission("tables.configure")),
    db: Session = Depends(get_db),
) -> dict:
    token = table_service.rotate_qr(db, actor.membership, table_id)
    return {"qr_token": token}
