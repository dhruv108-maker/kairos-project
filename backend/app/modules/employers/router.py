from fastapi import APIRouter, HTTPException, Query, Response, status
from sqlalchemy.exc import IntegrityError

from app.api.dependencies import CurrentAccount, DbSession
from app.models.employers import EmployerOrganization
from app.modules.employers.schemas import EmployerRegister, EmployerProfileUpdate, JobCreate, JobPatch, EmployerInviteCreate, EmployerInviteAccept, EmployerRoleUpdate, RecruitmentStageUpdate, RecruitmentNoteCreate, EmployerStatusUpdate
from app.modules.employers.service import EmployerError, EmployerService

router = APIRouter(tags=["employers", "recruitment"])
public_router = APIRouter(tags=["public-jobs"])


def _error(exc: EmployerError) -> HTTPException:
    return HTTPException(status_code=exc.status_code, detail=exc.message)


def _org(item: EmployerOrganization, include_private: bool = True) -> dict:
    result = {key: getattr(item, key) for key in (
        "id", "legal_name", "display_name", "organization_type", "industry", "description",
        "website_url", "country", "state", "city", "postal_code",
        "company_size", "founded_year",
        "careers_url", "status", "created_at", "updated_at", "reviewed_at"
    )}
    if include_private:
        result.update({key: getattr(item, key) for key in ("business_email", "phone", "registration_identifier", "headquarters_address", "review_notes")})
    return result


def _job(item, company=None) -> dict:
    result = {key: getattr(item, key) for key in (
        "id", "provider_id", "title", "summary", "description", "location", "application_deadline",
        "starts_on", "ends_on", "is_active", "lifecycle_status", "opportunity_type", "employment_type",
        "work_mode", "department", "experience_min_years", "experience_max_years", "compensation_min",
        "compensation_max", "compensation_currency", "compensation_period", "compensation_visible",
        "openings", "required_skills", "preferred_skills", "education_requirements", "public_application_url",
        "created_at", "updated_at"
    )}
    if not result["compensation_visible"]:
        result["compensation_min"] = result["compensation_max"] = None
    result["company"] = company
    return result


@router.post("/employers/register", status_code=status.HTTP_201_CREATED)
async def register_employer(payload: EmployerRegister, account: CurrentAccount, db: DbSession):
    try:
        item = await EmployerService(db).register(account.id, payload.model_dump())
    except EmployerError as exc:
        raise _error(exc) from None
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Employer registration conflicts with existing data") from None
    return {"organization": _org(item), "next_step": "submit_for_verification"}


@router.get("/employers/me/organizations")
async def my_employer_organizations(account: CurrentAccount, db: DbSession):
    items = await EmployerService(db).my_organizations(account.id)
    return {"items": [_org(item) for item in items]}


@router.get("/employers/organizations/{organization_id}")
async def get_employer(organization_id: str, account: CurrentAccount, db: DbSession):
    try:
        org, member = await EmployerService(db).membership(organization_id, account.id)
        return _org(org, include_private=member.role in {"OWNER", "ADMIN"})
    except EmployerError as exc:
        raise _error(exc) from None


@router.patch("/employers/organizations/{organization_id}")
async def update_employer(organization_id: str, payload: EmployerProfileUpdate, account: CurrentAccount, db: DbSession):
    try:
        item = await EmployerService(db).update_profile(organization_id, account.id, payload.model_dump(exclude_unset=True))
        return _org(item)
    except EmployerError as exc:
        raise _error(exc) from None


@router.get("/employers/organizations/{organization_id}/registration-status")
async def registration_status(organization_id: str, account: CurrentAccount, db: DbSession):
    try:
        org, member = await EmployerService(db).membership(organization_id, account.id, {"OWNER", "ADMIN"})
        return {"organization_id": org.id, "status": org.status, "reviewed_at": org.reviewed_at, "review_notes": org.review_notes}
    except EmployerError as exc:
        raise _error(exc) from None


@router.post("/employers/organizations/{organization_id}/submit-for-verification")
async def submit_verification(organization_id: str, account: CurrentAccount, db: DbSession):
    try:
        return _org(await EmployerService(db).submit_verification(organization_id, account.id))
    except EmployerError as exc:
        raise _error(exc) from None


@router.post("/employers/organizations/{organization_id}/verification-decision")
async def verification_decision(organization_id: str, account: CurrentAccount, db: DbSession, decision: str = Query(..., pattern="^(ACTIVE|REJECTED)$"), notes: str | None = Query(default=None, max_length=2000)):
    try:
        return _org(await EmployerService(db).review_verification(organization_id, account.id, decision, notes))
    except EmployerError as exc:
        raise _error(exc) from None


@router.patch("/employers/organizations/{organization_id}/status")
async def set_employer_status(organization_id: str, payload: EmployerStatusUpdate, account: CurrentAccount, db: DbSession):
    try:
        return _org(await EmployerService(db).set_organization_status(organization_id, account.id, payload.status, payload.notes))
    except EmployerError as exc:
        raise _error(exc) from None


@router.post("/employers/organizations/{organization_id}/jobs", status_code=201)
async def create_job(organization_id: str, payload: JobCreate, account: CurrentAccount, db: DbSession):
    try:
        return _job(await EmployerService(db).create_job(organization_id, account.id, payload.model_dump()))
    except EmployerError as exc:
        raise _error(exc) from None


@router.get("/employers/organizations/{organization_id}/jobs")
async def list_jobs(organization_id: str, account: CurrentAccount, db: DbSession, limit: int = Query(50, ge=1, le=100), offset: int = Query(0, ge=0)):
    try:
        items = await EmployerService(db).list_jobs(organization_id, account.id, limit, offset)
        return {"items": [_job(item) for item in items], "limit": limit, "offset": offset}
    except EmployerError as exc:
        raise _error(exc) from None


@router.get("/employers/organizations/{organization_id}/jobs/{job_id}")
async def get_job(organization_id: str, job_id: str, account: CurrentAccount, db: DbSession):
    try:
        return _job(await EmployerService(db).get_owned_job(organization_id, account.id, job_id))
    except EmployerError as exc:
        raise _error(exc) from None


@router.patch("/employers/organizations/{organization_id}/jobs/{job_id}")
async def update_job(organization_id: str, job_id: str, payload: JobPatch, account: CurrentAccount, db: DbSession):
    try:
        return _job(await EmployerService(db).update_job(organization_id, account.id, job_id, payload.model_dump(exclude_unset=True)))
    except EmployerError as exc:
        raise _error(exc) from None


@router.delete("/employers/organizations/{organization_id}/jobs/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
async def archive_job(organization_id: str, job_id: str, account: CurrentAccount, db: DbSession):
    service = EmployerService(db)
    try:
        item = await service.get_owned_job(organization_id, account.id, job_id, write=True)
        if item.lifecycle_status == "PUBLISHED":
            await service.transition_job(organization_id, account.id, job_id, "pause")
        current = await service.get_owned_job(organization_id, account.id, job_id, write=True)
        if current.lifecycle_status in {"DRAFT", "PAUSED", "CLOSED"}:
            await service.transition_job(organization_id, account.id, job_id, "archive")
        elif current.lifecycle_status != "ARCHIVED":
            raise EmployerError(409, f"Cannot archive a job in {current.lifecycle_status} state")
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except EmployerError as exc:
        raise _error(exc) from None


@router.post("/employers/organizations/{organization_id}/jobs/{job_id}/{action}")
async def job_action(organization_id: str, job_id: str, action: str, account: CurrentAccount, db: DbSession):
    if action not in {"publish", "pause", "resume", "close", "reopen", "archive"}:
        raise HTTPException(status_code=404, detail="Unknown job action")
    try:
        return _job(await EmployerService(db).transition_job(organization_id, account.id, job_id, action))
    except EmployerError as exc:
        raise _error(exc) from None


@router.get("/employers/organizations/{organization_id}/dashboard")
async def employer_dashboard(organization_id: str, account: CurrentAccount, db: DbSession):
    try:
        return await EmployerService(db).dashboard(organization_id, account.id)
    except EmployerError as exc:
        raise _error(exc) from None


@router.get("/employers/organizations/{organization_id}/members")
async def list_employer_members(organization_id: str, account: CurrentAccount, db: DbSession):
    try:
        items = await EmployerService(db).list_members(organization_id, account.id)
        return {"items": [{"id": item.id, "account_id": item.account_id, "role": item.role, "status": item.status, "created_at": item.created_at} for item in items]}
    except EmployerError as exc:
        raise _error(exc) from None


@router.post("/employers/organizations/{organization_id}/invitations", status_code=201)
async def invite_employer_member(organization_id: str, payload: EmployerInviteCreate, account: CurrentAccount, db: DbSession):
    try:
        item, delivery_sent = await EmployerService(db).invite_member(organization_id, account.id, payload.email, payload.role)
        return {"id": item.id, "organization_id": item.organization_id, "email": item.email, "role": item.role, "expires_at": item.expires_at, "delivery_sent": delivery_sent, "status": "sent" if delivery_sent else "delivery_failed_and_revoked"}
    except EmployerError as exc:
        raise _error(exc) from None


@router.get("/employers/organizations/{organization_id}/invitations")
async def list_employer_invitations(organization_id: str, account: CurrentAccount, db: DbSession):
    try:
        items = await EmployerService(db).list_invitations(organization_id, account.id)
        return {"items": [{"id": item.id, "email": item.email, "role": item.role, "expires_at": item.expires_at, "accepted_at": item.accepted_at, "revoked_at": item.revoked_at, "created_at": item.created_at} for item in items]}
    except EmployerError as exc:
        raise _error(exc) from None


@router.delete("/employers/organizations/{organization_id}/invitations/{invitation_id}", status_code=204)
async def revoke_employer_invitation(organization_id: str, invitation_id: str, account: CurrentAccount, db: DbSession):
    try:
        await EmployerService(db).revoke_invitation(organization_id, account.id, invitation_id)
        return None
    except EmployerError as exc:
        raise _error(exc) from None


@router.post("/employer-invitations/accept")
async def accept_employer_invitation(payload: EmployerInviteAccept, account: CurrentAccount, db: DbSession):
    try:
        item = await EmployerService(db).accept_invitation(account.id, payload.token)
        return {"organization_id": item.organization_id, "account_id": item.account_id, "role": item.role, "status": item.status}
    except EmployerError as exc:
        raise _error(exc) from None


@router.patch("/employers/organizations/{organization_id}/members/{target_account_id}/role")
async def change_employer_member_role(organization_id: str, target_account_id: str, payload: EmployerRoleUpdate, account: CurrentAccount, db: DbSession):
    try:
        item = await EmployerService(db).change_member_role(organization_id, account.id, target_account_id, payload.role)
        return {"id": item.id, "account_id": item.account_id, "role": item.role, "status": item.status}
    except EmployerError as exc:
        raise _error(exc) from None


@router.delete("/employers/organizations/{organization_id}/members/{target_account_id}", status_code=204)
async def remove_employer_member(organization_id: str, target_account_id: str, account: CurrentAccount, db: DbSession):
    try:
        await EmployerService(db).remove_member(organization_id, account.id, target_account_id)
        return None
    except EmployerError as exc:
        raise _error(exc) from None


@router.get("/employers/organizations/{organization_id}/applications")
async def list_employer_applications(organization_id: str, account: CurrentAccount, db: DbSession, job_id: str | None = None, stage: str | None = Query(default=None, pattern="^(SUBMITTED|UNDER_REVIEW|SHORTLISTED|INTERVIEW|OFFER|HIRED|REJECTED|WITHDRAWN|submitted|under_review|shortlisted|interview|offer|hired|rejected|withdrawn)$"), limit: int = Query(50, ge=1, le=100), offset: int = Query(0, ge=0)):
    try:
        rows = await EmployerService(db).list_applications(organization_id, account.id, job_id, stage, limit, offset)
        return {"items": [{"id": app.id, "opportunity_id": job.id, "job_title": job.title, "student_id": app.student_id, "applicant_name": account_row.full_name, "applicant_email": account_row.email, "legacy_status": app.status, "stage": app.recruitment_stage, "applied_at": app.applied_at} for app, job, account_row in rows], "limit": limit, "offset": offset}
    except EmployerError as exc:
        raise _error(exc) from None


@router.get("/employers/organizations/{organization_id}/applications/{application_id}")
async def get_employer_application(organization_id: str, application_id: str, account: CurrentAccount, db: DbSession):
    try:
        app, job, student, applicant, history = await EmployerService(db).get_application_detail(organization_id, account.id, application_id)
        return {"id": app.id, "opportunity_id": job.id, "job_title": job.title, "student_id": app.student_id, "applicant": {"name": applicant.full_name, "email": applicant.email} if applicant else None, "legacy_status": app.status, "stage": app.recruitment_stage, "applied_at": app.applied_at, "stage_history": [{"from_stage": h.from_stage, "to_stage": h.to_stage, "note": h.note, "actor_account_id": h.actor_account_id, "created_at": h.created_at} for h in history]}
    except EmployerError as exc:
        raise _error(exc) from None


@router.post("/employers/organizations/{organization_id}/applications/{application_id}/stage")
async def update_application_stage(organization_id: str, application_id: str, payload: RecruitmentStageUpdate, account: CurrentAccount, db: DbSession):
    try:
        app = await EmployerService(db).transition_application_stage(organization_id, account.id, application_id, payload.stage, payload.note)
        return {"id": app.id, "legacy_status": app.status, "stage": app.recruitment_stage}
    except EmployerError as exc:
        raise _error(exc) from None


@router.get("/employers/organizations/{organization_id}/applications/{application_id}/notes")
async def list_application_notes(organization_id: str, application_id: str, account: CurrentAccount, db: DbSession):
    try:
        items = await EmployerService(db).list_application_notes(organization_id, account.id, application_id)
        return {"items": [{"id": item.id, "author_account_id": item.author_account_id, "body": item.body, "created_at": item.created_at} for item in items]}
    except EmployerError as exc:
        raise _error(exc) from None


@router.post("/employers/organizations/{organization_id}/applications/{application_id}/notes", status_code=201)
async def add_application_note(organization_id: str, application_id: str, payload: RecruitmentNoteCreate, account: CurrentAccount, db: DbSession):
    try:
        item = await EmployerService(db).add_application_note(organization_id, account.id, application_id, payload.body)
        return {"id": item.id, "application_id": item.application_id, "author_account_id": item.author_account_id, "body": item.body, "created_at": item.created_at}
    except EmployerError as exc:
        raise _error(exc) from None


@public_router.get("/companies/{organization_id}")
async def public_company_profile(organization_id: str, db: DbSession):
    try:
        org = await EmployerService(db).public_company(organization_id)
        return {"id": org.id, "name": org.display_name, "industry": org.industry, "description": org.description, "website_url": org.website_url, "careers_url": org.careers_url, "country": org.country, "state": org.state, "city": org.city, "company_size": org.company_size, "founded_year": org.founded_year}
    except EmployerError as exc:
        raise _error(exc) from None


@public_router.get("/companies/{organization_id}/jobs")
async def public_company_job_list(organization_id: str, db: DbSession, limit: int = Query(50, ge=1, le=100), offset: int = Query(0, ge=0)):
    try:
        rows = await EmployerService(db).public_company_jobs(organization_id, limit, offset)
        return {"items": [_job(item, {"id": provider.employer_organization_id, "name": provider.company_name, "website": provider.website}) for item, provider in rows], "limit": limit, "offset": offset}
    except EmployerError as exc:
        raise _error(exc) from None


@public_router.get("/jobs")
async def discover_jobs(db: DbSession, q: str | None = Query(default=None, max_length=100), location: str | None = Query(default=None, max_length=150), opportunity_type: str | None = Query(default=None, pattern="^(job|internship|JOB|INTERNSHIP)$"), work_mode: str | None = Query(default=None, pattern="^(onsite|hybrid|remote|ONSITE|HYBRID|REMOTE)$"), limit: int = Query(50, ge=1, le=100), offset: int = Query(0, ge=0)):
    items = await EmployerService(db).public_jobs(q, location, opportunity_type, work_mode, limit, offset)
    return {"items": [_job(item, {"id": provider.employer_organization_id, "name": provider.company_name, "website": provider.website}) for item, provider in items], "limit": limit, "offset": offset}


@public_router.get("/jobs/{job_id}")
async def public_job_detail(job_id: str, db: DbSession):
    try:
        item, provider = await EmployerService(db).public_job(job_id)
        return _job(item, {"id": provider.employer_organization_id, "name": provider.company_name, "website": provider.website})
    except EmployerError as exc:
        raise _error(exc) from None
