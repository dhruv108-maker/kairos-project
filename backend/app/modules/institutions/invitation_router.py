from fastapi import APIRouter, HTTPException
from sqlalchemy.exc import IntegrityError

from app.api.dependencies import CurrentAccount, DbSession
from app.modules.institutions.invitation_service import InstitutionInvitationService, InvitationWorkflowError
from app.modules.institutions.invitation_schemas import InstitutionInvitationAccept, InstitutionInvitationCreate
from app.modules.institutions.service import InstitutionAccessError

admin_router = APIRouter(prefix="/institutions/{institution_id}/invitations", tags=["institution invitations"])
accept_router = APIRouter(prefix="/institutions/invitations", tags=["institution invitations"])


async def _call(operation, db):
    try:
        return await operation
    except (InvitationWorkflowError, InstitutionAccessError) as exc:
        raise HTTPException(status_code=exc.status_code, detail=getattr(exc, "message", str(exc))) from None
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Invitation operation conflicts with existing data") from None


def _invitation(item):
    return {"id": item.id, "institution_id": item.institution_id, "email": item.email, "role": item.role,
            "expires_at": item.expires_at, "accepted_at": item.accepted_at, "revoked_at": item.revoked_at,
            "created_at": item.created_at}


@admin_router.post("", status_code=201)
async def create_invitation(institution_id: str, payload: InstitutionInvitationCreate, account: CurrentAccount, db: DbSession):
    item, email_sent = await _call(InstitutionInvitationService(db).invite(institution_id, account.id, payload.email, payload.role), db)
    return {**_invitation(item), "email_sent": email_sent}


@admin_router.get("")
async def list_invitations(institution_id: str, account: CurrentAccount, db: DbSession):
    items = await _call(InstitutionInvitationService(db).list_invitations(institution_id, account.id), db)
    return {"items": [_invitation(item) for item in items]}


@admin_router.delete("/{invitation_id}", status_code=204)
async def revoke_invitation(institution_id: str, invitation_id: str, account: CurrentAccount, db: DbSession):
    await _call(InstitutionInvitationService(db).revoke(institution_id, account.id, invitation_id), db)
    return None


@accept_router.post("/accept")
async def accept_invitation(payload: InstitutionInvitationAccept, account: CurrentAccount, db: DbSession):
    item = await _call(InstitutionInvitationService(db).accept(account.id, payload.token), db)
    return {"institution_id": item.institution_id, "account_id": item.account_id, "role": item.role, "status": item.status}
