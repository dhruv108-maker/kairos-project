from fastapi import APIRouter, HTTPException, Query
from app.api.dependencies import CurrentAccount, DbSession
from app.modules.audit.service import AuditAccessError, AuditService

router = APIRouter(prefix="/institutions/{institution_id}/audit-events", tags=["audit"])


@router.get("")
async def list_audit_events(
    institution_id: str, account: CurrentAccount, db: DbSession,
    action: str | None = Query(default=None, max_length=100),
    entity_type: str | None = Query(default=None, max_length=100),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    try:
        items = await AuditService(db).list_for_institution(institution_id, account.id, limit, offset, action, entity_type)
    except AuditAccessError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from None
    return {"items": [{
        "id": item.id, "actor_account_id": item.actor_account_id,
        "institution_id": item.institution_id, "action": item.action,
        "entity_type": item.entity_type, "entity_id": item.entity_id,
        "details": item.details, "created_at": item.created_at,
    } for item in items], "limit": limit, "offset": offset}
