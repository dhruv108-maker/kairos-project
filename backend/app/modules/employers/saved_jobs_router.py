from uuid import uuid4

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.api.dependencies import CurrentAccount, DbSession
from app.models.employers import EmployerOrganization
from app.models.internship import InternshipOpportunity, InternshipProvider
from app.models.saved_job import SavedJob
from app.modules.identity.service import IdentityService

router = APIRouter(prefix="/students/saved-jobs", tags=["student-saved-jobs"])


async def _require_student(db: DbSession, account_id: str) -> None:
    roles = {role.upper() for role in await IdentityService(db).roles_for(account_id)}
    if "STUDENT" not in roles:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Student account required")


def _job(item: InternshipOpportunity, provider: InternshipProvider, saved: SavedJob) -> dict:
    compensation_visible = bool(item.compensation_visible)
    return {
        "id": item.id,
        "saved_job_id": saved.id,
        "saved_at": saved.created_at,
        "title": item.title,
        "summary": item.summary,
        "description": item.description,
        "location": item.location,
        "application_deadline": item.application_deadline,
        "starts_on": item.starts_on,
        "ends_on": item.ends_on,
        "lifecycle_status": item.lifecycle_status,
        "opportunity_type": item.opportunity_type,
        "employment_type": item.employment_type,
        "work_mode": item.work_mode,
        "department": item.department,
        "experience_min_years": item.experience_min_years,
        "experience_max_years": item.experience_max_years,
        "compensation_min": item.compensation_min if compensation_visible else None,
        "compensation_max": item.compensation_max if compensation_visible else None,
        "compensation_currency": item.compensation_currency,
        "compensation_period": item.compensation_period,
        "compensation_visible": compensation_visible,
        "required_skills": item.required_skills,
        "preferred_skills": item.preferred_skills,
        "education_requirements": item.education_requirements,
        "public_application_url": item.public_application_url,
        "created_at": item.created_at,
        "company": {
            "id": provider.employer_organization_id,
            "name": provider.company_name,
            "website": provider.website,
        },
    }


@router.get("")
async def list_saved_jobs(account: CurrentAccount, db: DbSession):
    await _require_student(db, account.id)
    rows = await db.execute(
        select(SavedJob, InternshipOpportunity, InternshipProvider)
        .join(InternshipOpportunity, SavedJob.opportunity_id == InternshipOpportunity.id)
        .join(InternshipProvider, InternshipOpportunity.provider_id == InternshipProvider.id)
        .join(EmployerOrganization, InternshipProvider.employer_organization_id == EmployerOrganization.id)
        .where(
            SavedJob.account_id == account.id,
            InternshipOpportunity.lifecycle_status == "PUBLISHED",
            InternshipOpportunity.is_active.is_(True),
            InternshipOpportunity.application_deadline >= __import__("datetime").date.today(),
            EmployerOrganization.status == "ACTIVE",
        )
        .order_by(SavedJob.created_at.desc(), SavedJob.id)
    )
    return {"items": [_job(job, provider, saved) for saved, job, provider in rows.all()]}


@router.post("/{opportunity_id}", status_code=status.HTTP_201_CREATED)
async def save_job(opportunity_id: str, account: CurrentAccount, db: DbSession):
    await _require_student(db, account.id)
    row = await db.execute(
        select(InternshipOpportunity.id)
        .join(InternshipProvider, InternshipOpportunity.provider_id == InternshipProvider.id)
        .join(EmployerOrganization, InternshipProvider.employer_organization_id == EmployerOrganization.id)
        .where(
            InternshipOpportunity.id == opportunity_id,
            InternshipOpportunity.lifecycle_status == "PUBLISHED",
            InternshipOpportunity.is_active.is_(True),
            InternshipOpportunity.application_deadline >= __import__("datetime").date.today(),
            EmployerOrganization.status == "ACTIVE",
        )
    )
    if row.scalar_one_or_none() is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Active opportunity not found")
    existing = await db.scalar(select(SavedJob).where(
        SavedJob.account_id == account.id,
        SavedJob.opportunity_id == opportunity_id,
    ))
    if existing is not None:
        return {"id": existing.id, "opportunity_id": existing.opportunity_id, "saved": True}
    item = SavedJob(id=str(uuid4()), account_id=account.id, opportunity_id=opportunity_id)
    db.add(item)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        existing = await db.scalar(select(SavedJob).where(
            SavedJob.account_id == account.id,
            SavedJob.opportunity_id == opportunity_id,
        ))
        if existing is None:
            raise HTTPException(status_code=409, detail="Could not save this opportunity; please retry") from None
        item = existing
    return {"id": item.id, "opportunity_id": item.opportunity_id, "saved": True}


@router.delete("/{opportunity_id}", status_code=status.HTTP_204_NO_CONTENT)
async def unsave_job(opportunity_id: str, account: CurrentAccount, db: DbSession):
    await _require_student(db, account.id)
    item = await db.scalar(select(SavedJob).where(
        SavedJob.account_id == account.id,
        SavedJob.opportunity_id == opportunity_id,
    ))
    if item is not None:
        await db.delete(item)
        await db.commit()
