"""HTTP endpoints for institution, employer and student campus recruitment flows."""
from datetime import date, datetime
from pydantic import BaseModel, ConfigDict, Field, model_validator
from fastapi import APIRouter, HTTPException, Query, status

from app.api.dependencies import CurrentAccount, DbSession, require_role
from app.modules.employers.campus_recruitment_service import CampusRecruitmentService
from app.modules.employers.service import EmployerError

router = APIRouter(tags=["campus-recruitment"])


def _error(exc: EmployerError) -> HTTPException:
    return HTTPException(status_code=exc.status_code, detail=exc.message)


class DriveCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=2, max_length=255)
    description: str | None = Field(default=None, max_length=10000)
    academic_year_id: str | None = None
    starts_on: date | None = None
    ends_on: date | None = None
    application_opens_at: datetime | None = None
    application_closes_at: datetime | None = None
    programme_ids: list[str] = Field(default_factory=list, max_length=250)
    cohort_ids: list[str] = Field(default_factory=list, max_length=500)
    graduation_years: list[int] = Field(default_factory=list, max_length=20)

    @model_validator(mode="after")
    def validate_dates(self):
        if self.starts_on and self.ends_on and self.ends_on < self.starts_on:
            raise ValueError("ends_on must be on or after starts_on")
        if self.application_opens_at and self.application_closes_at and self.application_closes_at <= self.application_opens_at:
            raise ValueError("application close must follow open")
        return self


class DrivePatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str | None = Field(default=None, min_length=2, max_length=255)
    description: str | None = Field(default=None, max_length=10000)
    academic_year_id: str | None = None
    starts_on: date | None = None
    ends_on: date | None = None
    application_opens_at: datetime | None = None
    application_closes_at: datetime | None = None
    programme_ids: list[str] | None = Field(default=None, max_length=250)
    cohort_ids: list[str] | None = Field(default=None, max_length=500)
    graduation_years: list[int] | None = Field(default=None, max_length=20)


class InviteEmployer(BaseModel):
    model_config = ConfigDict(extra="forbid")
    organization_id: str


class InvitationResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    decision: str


class AssociateOpportunity(BaseModel):
    model_config = ConfigDict(extra="forbid")
    opportunity_id: str


def _participation(item):
    return {"id": item.id, "drive_id": item.drive_id, "organization_id": item.organization_id,
        "status": item.status, "invited_at": item.invited_at, "responded_at": item.responded_at}


@router.post("/institutions/{institution_id}/recruitment-drives", status_code=status.HTTP_201_CREATED)
async def create_drive(institution_id: str, payload: DriveCreate, account: CurrentAccount, db: DbSession):
    try:
        service = CampusRecruitmentService(db)
        item = await service.create_drive(institution_id, account.id, payload.model_dump())
        return await service.drive_view(item)
    except EmployerError as exc:
        raise _error(exc) from None


@router.get("/institutions/{institution_id}/recruitment-drives")
async def list_drives(institution_id: str, account: CurrentAccount, db: DbSession,
    limit: int = Query(default=50, ge=1, le=100), offset: int = Query(default=0, ge=0)):
    try:
        service = CampusRecruitmentService(db)
        items = await service.list_drives(institution_id, account.id, limit, offset)
        return {"items": [await service.drive_view(item) for item in items], "limit": limit, "offset": offset}
    except EmployerError as exc:
        raise _error(exc) from None


@router.get("/recruitment-drives/{drive_id}")
async def get_drive(drive_id: str, account: CurrentAccount, db: DbSession):
    try:
        service = CampusRecruitmentService(db)
        return await service.drive_view(await service.get_drive(drive_id, account.id))
    except EmployerError as exc:
        raise _error(exc) from None


@router.patch("/recruitment-drives/{drive_id}")
async def update_drive(drive_id: str, payload: DrivePatch, account: CurrentAccount, db: DbSession):
    try:
        service = CampusRecruitmentService(db)
        item = await service.update_drive(drive_id, account.id, payload.model_dump(exclude_unset=True))
        return await service.drive_view(item)
    except EmployerError as exc:
        raise _error(exc) from None


@router.post("/recruitment-drives/{drive_id}/{action}")
async def transition_drive(drive_id: str, action: str, account: CurrentAccount, db: DbSession):
    if action not in {"publish", "activate", "complete", "cancel", "archive"}:
        raise HTTPException(status_code=404, detail="Unknown recruitment drive action")
    try:
        item = await CampusRecruitmentService(db).transition_drive(drive_id, account.id, action)
        return {"id": item.id, "status": item.status}
    except EmployerError as exc:
        raise _error(exc) from None


@router.post("/recruitment-drives/{drive_id}/employers", status_code=status.HTTP_201_CREATED)
async def invite_employer(drive_id: str, payload: InviteEmployer, account: CurrentAccount, db: DbSession):
    try:
        return _participation(await CampusRecruitmentService(db).invite_employer(drive_id, account.id, payload.organization_id))
    except EmployerError as exc:
        raise _error(exc) from None


@router.get("/employers/organizations/{organization_id}/recruitment-drive-invitations")
async def list_drive_invitations(organization_id: str, account: CurrentAccount, db: DbSession):
    try:
        items = await CampusRecruitmentService(db).list_employer_invitations(organization_id, account.id)
        return {"items": [_participation(item) for item in items]}
    except EmployerError as exc:
        raise _error(exc) from None


@router.post("/employers/organizations/{organization_id}/recruitment-drive-invitations/{participation_id}/respond")
async def respond_drive_invitation(organization_id: str, participation_id: str, payload: InvitationResponse,
    account: CurrentAccount, db: DbSession):
    try:
        item = await CampusRecruitmentService(db).respond_invitation(organization_id, account.id, participation_id, payload.decision.upper())
        return _participation(item)
    except EmployerError as exc:
        raise _error(exc) from None


@router.post("/employers/organizations/{organization_id}/recruitment-drives/{drive_id}/opportunities", status_code=status.HTTP_201_CREATED)
async def associate_opportunity(organization_id: str, drive_id: str, payload: AssociateOpportunity,
    account: CurrentAccount, db: DbSession):
    try:
        item = await CampusRecruitmentService(db).associate_opportunity(organization_id, account.id, drive_id, payload.opportunity_id)
        return {"drive_id": item.drive_id, "opportunity_id": item.opportunity_id, "added_by_account_id": item.added_by_account_id}
    except EmployerError as exc:
        raise _error(exc) from None


@router.get("/students/recruitment-drives")
async def student_drives(account: CurrentAccount, db: DbSession,
    limit: int = Query(default=50, ge=1, le=100), offset: int = Query(default=0, ge=0)):
    await require_role(db, account, "STUDENT")
    try:
        items = await CampusRecruitmentService(db).student_drives(account.id, limit, offset)
        return {"items": items, "limit": limit, "offset": offset}
    except EmployerError as exc:
        raise _error(exc) from None


@router.get("/students/recruitment-drives/{drive_id}/eligibility")
async def drive_eligibility(drive_id: str, account: CurrentAccount, db: DbSession):
    await require_role(db, account, "STUDENT")
    try:
        return await CampusRecruitmentService(db).eligibility(account.id, drive_id)
    except EmployerError as exc:
        raise _error(exc) from None


@router.get("/students/opportunities/{opportunity_id}/eligibility")
async def opportunity_eligibility(opportunity_id: str, account: CurrentAccount, db: DbSession):
    await require_role(db, account, "STUDENT")
    try:
        return await CampusRecruitmentService(db).student_application_eligibility(account.id, opportunity_id)
    except EmployerError as exc:
        raise _error(exc) from None

@router.delete("/recruitment-drives/{drive_id}/employers/{organization_id}")
async def revoke_employer_participation(drive_id: str, organization_id: str, account: CurrentAccount, db: DbSession):
    try:
        item = await CampusRecruitmentService(db).revoke_participation(drive_id, account.id, organization_id)
        return _participation(item)
    except EmployerError as exc:
        raise _error(exc) from None


@router.delete("/employers/organizations/{organization_id}/recruitment-drives/{drive_id}/opportunities/{opportunity_id}", status_code=204)
async def remove_opportunity_association(organization_id: str, drive_id: str, opportunity_id: str, account: CurrentAccount, db: DbSession):
    try:
        await CampusRecruitmentService(db).remove_opportunity_association(organization_id, account.id, drive_id, opportunity_id)
        return None
    except EmployerError as exc:
        raise _error(exc) from None


@router.get("/students/recruitment-drives/{drive_id}/opportunities")
async def student_opportunities(drive_id: str, account: CurrentAccount, db: DbSession,
    limit: int = Query(default=50, ge=1, le=100), offset: int = Query(default=0, ge=0)):
    await require_role(db, account, "STUDENT")
    try:
        items = await CampusRecruitmentService(db).student_opportunities(account.id, drive_id, limit, offset)
        return {"items": items, "limit": limit, "offset": offset}
    except EmployerError as exc:
        raise _error(exc) from None
