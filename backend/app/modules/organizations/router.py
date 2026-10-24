from fastapi import APIRouter, HTTPException
from sqlalchemy.exc import IntegrityError

from app.api.dependencies import CurrentAccount, DbSession
from app.modules.institutions.service import InstitutionAccessError
from app.modules.organizations.schemas import CampaignCreate, CampaignStatusUpdate, FacultyAssignmentCreate, FacultyAssignmentUpdate, TeamCreate, TeamMemberUpsert
from app.modules.organizations.service import OrganizationService, OrganizationWorkflowError

router = APIRouter(prefix="/institutions/{institution_id}", tags=["teams", "assessment campaigns"])


async def _call(operation, db):
    try:
        return await operation
    except (OrganizationWorkflowError, InstitutionAccessError) as exc:
        status_code = getattr(exc, "status_code", 500)
        message = getattr(exc, "message", str(exc))
        raise HTTPException(status_code=status_code, detail=message) from None
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail="The operation conflicts with existing data") from None


def _team(item):
    return {"id": item.id, "name": item.name, "department_id": item.department_id,
            "created_by_account_id": item.created_by_account_id, "created_at": item.created_at}


def _member(item):
    return {"team_id": item.team_id, "account_id": item.account_id, "role_in_team": item.role_in_team,
            "status": item.status, "joined_at": item.joined_at}


def _campaign(item):
    return {"id": item.id, "institution_id": item.institution_id, "title": item.title,
            "description": item.description, "start_date": item.start_date, "end_date": item.end_date,
            "is_active": item.is_active, "created_at": item.created_at}


def _assignment(item):
    return {"id": item.id, "campaign_id": item.campaign_id, "faculty_id": item.faculty_id,
            "assigned_reason": item.assigned_reason, "status": item.status,
            "assigned_at": item.assigned_at, "completed_at": item.completed_at, "score": str(item.score) if item.score is not None else None, "feedback_comments": item.feedback_comments, "submitted_at": item.submitted_at}


@router.post("/teams", status_code=201)
async def create_team(institution_id: str, payload: TeamCreate, account: CurrentAccount, db: DbSession):
    item = await _call(OrganizationService(db).create_team(institution_id, account.id, payload.department_id, payload.name), db)
    return _team(item)


@router.get("/teams")
async def list_teams(institution_id: str, account: CurrentAccount, db: DbSession):
    items = await _call(OrganizationService(db).list_teams(institution_id, account.id), db)
    return {"items": [_team(item) for item in items]}


@router.post("/teams/{team_id}/members", status_code=201)
async def add_team_member(institution_id: str, team_id: str, payload: TeamMemberUpsert, account: CurrentAccount, db: DbSession):
    item = await _call(OrganizationService(db).add_team_member(institution_id, account.id, team_id, payload.account_id, payload.role_in_team), db)
    return _member(item)


@router.get("/teams/{team_id}/members")
async def list_team_members(institution_id: str, team_id: str, account: CurrentAccount, db: DbSession):
    items = await _call(OrganizationService(db).list_team_members(institution_id, account.id, team_id), db)
    return {"items": [_member(item) for item in items]}


@router.delete("/teams/{team_id}/members/{target_account_id}", status_code=204)
async def remove_team_member(institution_id: str, team_id: str, target_account_id: str, account: CurrentAccount, db: DbSession):
    await _call(OrganizationService(db).remove_team_member(institution_id, account.id, team_id, target_account_id), db)
    return None


@router.post("/assessment-campaigns", status_code=201)
async def create_campaign(institution_id: str, payload: CampaignCreate, account: CurrentAccount, db: DbSession):
    item = await _call(OrganizationService(db).create_campaign(institution_id, account.id, payload.title, payload.description, payload.start_date, payload.end_date), db)
    return _campaign(item)


@router.get("/assessment-campaigns")
async def list_campaigns(institution_id: str, account: CurrentAccount, db: DbSession):
    items = await _call(OrganizationService(db).list_campaigns(institution_id, account.id), db)
    return {"items": [_campaign(item) for item in items]}


@router.patch("/assessment-campaigns/{campaign_id}/status")
async def set_campaign_active(institution_id: str, campaign_id: str, payload: CampaignStatusUpdate, account: CurrentAccount, db: DbSession):
    item = await _call(OrganizationService(db).set_campaign_active(institution_id, account.id, campaign_id, payload.is_active), db)
    return _campaign(item)


@router.post("/assessment-campaigns/{campaign_id}/assignments", status_code=201)
async def assign_faculty(institution_id: str, campaign_id: str, payload: FacultyAssignmentCreate, account: CurrentAccount, db: DbSession):
    item = await _call(OrganizationService(db).assign_faculty(institution_id, account.id, campaign_id, payload.faculty_account_id, payload.reason), db)
    return _assignment(item)


@router.get("/assessment-campaigns/{campaign_id}/assignments")
async def list_assignments(institution_id: str, campaign_id: str, account: CurrentAccount, db: DbSession):
    items = await _call(OrganizationService(db).list_assignments(institution_id, account.id, campaign_id), db)
    return {"items": [_assignment(item) for item in items]}


@router.patch("/assessment-campaigns/{campaign_id}/assignments/{assignment_id}")
async def update_assignment(institution_id: str, campaign_id: str, assignment_id: str,
                            payload: FacultyAssignmentUpdate, account: CurrentAccount, db: DbSession):
    item = await _call(OrganizationService(db).update_assignment(
        institution_id, account.id, campaign_id, assignment_id, payload.status,
        payload.score, payload.feedback_comments
    ), db)
    return _assignment(item)
