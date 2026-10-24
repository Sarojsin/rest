from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import Actor, require_permission
from app.db.session import get_db
from app.schemas.staff import TableOut
from app.services import tables as table_service

router = APIRouter(tags=["tables"])


@router.get("/tables", response_model=list[TableOut])
def list_tables(
    actor: Actor = Depends(require_permission("orders.read")),
    db: Session = Depends(get_db),
) -> list[TableOut]:
    return table_service.list_tables(db, actor.restaurant_id)


@router.post("/tables/{table_id}/qr/rotate")
def rotate_qr(
    table_id: UUID,
    actor: Actor = Depends(require_permission("tables.manage")),
    db: Session = Depends(get_db),
) -> dict:
    token = table_service.rotate_qr(db, actor.restaurant_id, table_id)
    return {"qr_token": token}
