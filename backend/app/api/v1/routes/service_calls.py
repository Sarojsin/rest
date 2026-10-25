from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import Actor, require_permission
from app.db.session import get_db
from app.schemas.staff import ServiceCallOut
from app.services import service_calls as service_call_service

router = APIRouter(prefix="/service-calls", tags=["service-calls"])


@router.get("", response_model=list[ServiceCallOut])
def list_service_calls(
    status: str | None = Query(default=None),
    actor: Actor = Depends(require_permission("orders.read")),
    db: Session = Depends(get_db),
) -> list[ServiceCallOut]:
    rows = service_call_service.list_service_calls(db, actor.restaurant_id, status)
    ticket_numbers = service_call_service.ticket_numbers_for_calls(db, [call for call, _ in rows])
    return [
        ServiceCallOut(
            id=call.id,
            kind=call.kind,
            table_id=table.id,
            table_display_name=table.display_name,
            ticket_number=ticket_numbers.get(call.kitchen_ticket_id),
            items_summary=call.detail,
            status=call.status,
            requested_at=call.created_at,
            acknowledged_at=call.acknowledged_at,
        )
        for call, table in rows
    ]


@router.post("/{call_id}/acknowledge", response_model=ServiceCallOut)
def acknowledge_service_call(
    call_id: UUID,
    actor: Actor = Depends(require_permission("tables.manage")),
    db: Session = Depends(get_db),
) -> ServiceCallOut:
    call, _deduplicated = service_call_service.acknowledge_service_call(
        db, actor.membership, call_id
    )
    ticket_number = service_call_service.ticket_numbers_for_calls(db, [call]).get(
        call.kitchen_ticket_id
    )
    return ServiceCallOut(
        id=call.id,
        kind=call.kind,
        table_id=call.table_id,
        table_display_name=call.table.display_name if call.table else "Table",
        ticket_number=ticket_number,
        items_summary=call.detail,
        status=call.status,
        requested_at=call.created_at,
        acknowledged_at=call.acknowledged_at,
    )
