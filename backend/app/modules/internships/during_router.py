"""During-internship placements, work logs, and role-scoped reviews."""
from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import CurrentAccount, DbSession, account_roles, require_role
from app.models.academic import Account, Department, FacultyProfile, School, StudentProfile
from app.models.employers import EmployerMembership
from app.modules.audit.service import AuditService
from app.models.internship import (
    InternshipApplication,
    InternshipOpportunity,
    InternshipPlacement,
    InternshipProvider,
    InternshipWorkLog,
    InternshipWorkLogReview,
)

router = APIRouter(prefix="/internships", tags=["during-internship"])
INDUSTRY_ROLES = {"EMPLOYER", "RECRUITER", "EMPLOYER_ADMIN", "EMPLOYER_MEMBER"}
REVIEW_DECISIONS = {"COMMENTED", "APPROVED", "REVISION_REQUIRED"}


class WorkLogCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    work_date: date
    work_summary: str = Field(min_length=3, max_length=10000)
    duration_minutes: int | None = Field(default=None, ge=1, le=1440)
    tasks_completed: str | None = Field(default=None, max_length=12000)
    skills_used: list[str] = Field(default_factory=list, max_length=100)
    challenges: str | None = Field(default=None, max_length=12000)
    learning_outcomes: str | None = Field(default=None, max_length=12000)
    next_steps: str | None = Field(default=None, max_length=12000)

    @field_validator("work_summary")
    @classmethod
    def clean_summary(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 3:
            raise ValueError("Work summary must contain at least 3 characters")
        return value

    @field_validator("skills_used")
    @classmethod
    def clean_skills(cls, values: list[str]) -> list[str]:
        cleaned = [value.strip() for value in values if value and value.strip()]
        if len(cleaned) > 100:
            raise ValueError("A maximum of 100 skills can be recorded")
        return cleaned


class WorkLogPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    work_date: date | None = None
    work_summary: str | None = Field(default=None, min_length=3, max_length=10000)
    duration_minutes: int | None = Field(default=None, ge=1, le=1440)
    tasks_completed: str | None = Field(default=None, max_length=12000)
    skills_used: list[str] | None = Field(default=None, max_length=100)
    challenges: str | None = Field(default=None, max_length=12000)
    learning_outcomes: str | None = Field(default=None, max_length=12000)
    next_steps: str | None = Field(default=None, max_length=12000)

    @field_validator("work_summary")
    @classmethod
    def clean_summary(cls, value: str | None) -> str | None:
        if value is None:
            return value
        value = value.strip()
        if len(value) < 3:
            raise ValueError("Work summary must contain at least 3 characters")
        return value

    @field_validator("skills_used")
    @classmethod
    def clean_skills(cls, values: list[str] | None) -> list[str] | None:
        if values is None:
            return None
        return [value.strip() for value in values if value and value.strip()][:100]


class WorkLogReviewCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    decision: str = Field(min_length=1, max_length=30)
    feedback: str = Field(min_length=1, max_length=5000)

    @field_validator("decision")
    @classmethod
    def normalize_decision(cls, value: str) -> str:
        value = value.strip().upper()
        if value not in REVIEW_DECISIONS:
            raise ValueError("decision must be COMMENTED, APPROVED, or REVISION_REQUIRED")
        return value

    @field_validator("feedback")
    @classmethod
    def clean_feedback(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Feedback cannot be blank")
        return value


class IndustryMentorAssignment(BaseModel):
    model_config = ConfigDict(extra="forbid")
    account_id: str = Field(min_length=1, max_length=36)


def _placements_query():
    return (
        select(InternshipPlacement, InternshipApplication, InternshipOpportunity,
               InternshipProvider, StudentProfile, Account)
        .join(InternshipApplication, InternshipApplication.id == InternshipPlacement.application_id)
        .join(InternshipOpportunity, InternshipOpportunity.id == InternshipApplication.opportunity_id)
        .outerjoin(InternshipProvider, InternshipProvider.id == InternshipOpportunity.provider_id)
        .join(StudentProfile, StudentProfile.id == InternshipPlacement.student_id)
        .join(Account, Account.id == StudentProfile.account_id)
    )


async def _institution_for_placement(db: AsyncSession, placement: InternshipPlacement) -> str | None:
    return await db.scalar(
        select(School.institution_id)
        .join(Department, Department.school_id == School.id)
        .join(StudentProfile, StudentProfile.department_id == Department.id)
        .where(StudentProfile.id == placement.student_id)
    )


async def _active_employer_member(db: AsyncSession, placement: InternshipPlacement, account_id: str) -> bool:
    application = await db.get(InternshipApplication, placement.application_id)
    if application is None:
        return False
    opportunity = await db.get(InternshipOpportunity, application.opportunity_id)
    if opportunity is None:
        return False
    provider = await db.get(InternshipProvider, opportunity.provider_id)
    if provider is None or not provider.employer_organization_id:
        return False
    roles = set(await account_roles(db, account_id))
    if not roles.intersection(INDUSTRY_ROLES):
        return False
    membership_id = await db.scalar(
        select(EmployerMembership.id).where(
            EmployerMembership.organization_id == provider.employer_organization_id,
            EmployerMembership.account_id == account_id,
            func.upper(EmployerMembership.status) == "ACTIVE",
        )
    )
    return membership_id is not None


async def _authorized_placement(db: AsyncSession, account: Account, placement_id: str) -> tuple[InternshipPlacement, str]:
    placement = await db.get(InternshipPlacement, placement_id)
    if placement is None:
        raise HTTPException(status_code=404, detail="Placement not found")

    roles = set(await account_roles(db, account.id))
    student = await db.scalar(select(StudentProfile).where(StudentProfile.account_id == account.id))
    if student is not None and "STUDENT" in roles and student.id == placement.student_id:
        return placement, "STUDENT"

    faculty = await db.scalar(select(FacultyProfile).where(FacultyProfile.account_id == account.id))
    if faculty is not None and "FACULTY" in roles and faculty.id == placement.faculty_supervisor_id:
        return placement, "FACULTY"

    if (
        placement.industry_mentor_account_id == account.id
        and roles.intersection(INDUSTRY_ROLES)
        and await _active_employer_member(db, placement, account.id)
    ):
        return placement, "INDUSTRY_MENTOR"

    # Hide cross-user placement identifiers rather than confirming they exist.
    raise HTTPException(status_code=404, detail="Placement not found")


async def _placement_payload(db: AsyncSession, row: tuple[Any, ...]) -> dict[str, Any]:
    placement, application, opportunity, provider, student, student_account = row
    faculty_name = None
    if placement.faculty_supervisor_id:
        faculty = await db.get(FacultyProfile, placement.faculty_supervisor_id)
        if faculty is not None:
            faculty_account = await db.get(Account, faculty.account_id)
            faculty_name = faculty_account.full_name if faculty_account else None
    industry_mentor_name = None
    if placement.industry_mentor_account_id:
        mentor_account = await db.get(Account, placement.industry_mentor_account_id)
        industry_mentor_name = mentor_account.full_name if mentor_account else None
    return {
        "id": placement.id,
        "application_id": application.id,
        "student": {
            "id": str(student.id),
            "name": student_account.full_name,
            "enrollment_number": student.enrollment_number,
        },
        "opportunity": {
            "id": opportunity.id,
            "title": opportunity.title,
            "company_name": provider.company_name if provider else None,
            "location": opportunity.location,
        },
        "faculty_supervisor_id": placement.faculty_supervisor_id,
        "faculty_supervisor_name": faculty_name,
        "industry_mentor_account_id": placement.industry_mentor_account_id,
        "industry_mentor_name": industry_mentor_name,
        "start_date": placement.start_date.isoformat(),
        "end_date": placement.end_date.isoformat(),
        "status": placement.status,
        "created_at": placement.created_at.isoformat() if placement.created_at else None,
        "updated_at": placement.updated_at.isoformat() if placement.updated_at else None,
    }


async def _reviews_for_logs(db: AsyncSession, log_ids: list[str]) -> dict[str, list[dict[str, Any]]]:
    if not log_ids:
        return {}
    rows = (await db.execute(
        select(InternshipWorkLogReview, Account)
        .join(Account, Account.id == InternshipWorkLogReview.reviewer_account_id)
        .where(InternshipWorkLogReview.work_log_id.in_(log_ids))
        .order_by(InternshipWorkLogReview.created_at.desc())
    )).all()
    grouped: dict[str, list[dict[str, Any]]] = {}
    for review, reviewer in rows:
        grouped.setdefault(review.work_log_id, []).append({
            "id": review.id,
            "reviewer_account_id": review.reviewer_account_id,
            "reviewer_name": reviewer.full_name,
            "reviewer_role": review.reviewer_role,
            "decision": review.decision,
            "feedback": review.feedback,
            "created_at": review.created_at.isoformat() if review.created_at else None,
        })
    return grouped


def _work_log_payload(item: InternshipWorkLog, reviews: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    review_items = reviews or []
    latest_by_role: dict[str, dict[str, Any]] = {}
    for review in review_items:
        latest_by_role.setdefault(review["reviewer_role"], review)
    return {
        "id": item.id,
        "placement_id": item.placement_id,
        "student_id": str(item.student_id),
        "work_date": item.work_date.isoformat(),
        "duration_minutes": item.duration_minutes,
        "work_summary": item.work_summary,
        "tasks_completed": item.tasks_completed,
        "skills_used": item.skills_used or [],
        "challenges": item.challenges,
        "learning_outcomes": item.learning_outcomes,
        "next_steps": item.next_steps,
        "status": item.status,
        "submitted_at": item.submitted_at.isoformat() if item.submitted_at else None,
        "created_at": item.created_at.isoformat() if item.created_at else None,
        "updated_at": item.updated_at.isoformat() if item.updated_at else None,
        "latest_reviews": list(latest_by_role.values()),
        "reviews": review_items,
    }


async def _logs_payload(db: AsyncSession, items: list[InternshipWorkLog]) -> list[dict[str, Any]]:
    reviews = await _reviews_for_logs(db, [item.id for item in items])
    return [_work_log_payload(item, reviews.get(item.id, [])) for item in items]


@router.get("/placements/me")
async def my_placements(account: CurrentAccount, db: DbSession) -> dict:
    await require_role(db, account, "STUDENT")
    student = await db.scalar(select(StudentProfile).where(StudentProfile.account_id == account.id))
    if student is None:
        raise HTTPException(status_code=404, detail="Student profile not found")
    rows = (await db.execute(
        _placements_query().where(InternshipPlacement.student_id == student.id)
        .order_by(InternshipPlacement.start_date.desc())
    )).all()
    return {"items": [await _placement_payload(db, row) for row in rows]}


@router.get("/placements/supervised")
async def supervised_placements(account: CurrentAccount, db: DbSession) -> dict:
    await require_role(db, account, "FACULTY")
    faculty = await db.scalar(select(FacultyProfile).where(FacultyProfile.account_id == account.id))
    if faculty is None:
        raise HTTPException(status_code=404, detail="Faculty profile not found")
    rows = (await db.execute(
        _placements_query().where(InternshipPlacement.faculty_supervisor_id == faculty.id)
        .order_by(InternshipPlacement.start_date.desc())
    )).all()
    return {"items": [await _placement_payload(db, row) for row in rows]}


@router.get("/placements/industry-mentor")
async def industry_mentor_placements(account: CurrentAccount, db: DbSession) -> dict:
    roles = set(await account_roles(db, account.id))
    if not roles.intersection(INDUSTRY_ROLES):
        raise HTTPException(status_code=403, detail="Industry mentor account required")
    rows = (await db.execute(
        _placements_query().where(InternshipPlacement.industry_mentor_account_id == account.id)
        .order_by(InternshipPlacement.start_date.desc())
    )).all()
    items = []
    for row in rows:
        if await _active_employer_member(db, row[0], account.id):
            items.append(await _placement_payload(db, row))
    return {"items": items}


@router.post("/placements/{placement_id}/industry-mentor")
async def assign_industry_mentor(
    placement_id: str, payload: IndustryMentorAssignment, account: CurrentAccount, db: DbSession
) -> dict:
    await require_role(db, account, "FACULTY")
    faculty = await db.scalar(select(FacultyProfile).where(FacultyProfile.account_id == account.id))
    placement = await db.get(InternshipPlacement, placement_id)
    if faculty is None or placement is None or placement.faculty_supervisor_id != faculty.id:
        raise HTTPException(status_code=404, detail="Supervised placement not found")
    target = await db.get(Account, payload.account_id)
    if target is None or not target.is_active or not target.is_verified:
        raise HTTPException(status_code=422, detail="Mentor account must be active and verified")
    if not await _active_employer_member(db, placement, target.id):
        raise HTTPException(status_code=422, detail="Mentor must be an active member of the internship provider's employer organization")
    placement.industry_mentor_account_id = target.id
    AuditService(db).record(
        account.id, await _institution_for_placement(db, placement),
        "internship.industry_mentor_assigned", "internship_placement", placement.id,
        {"industry_mentor_account_id": target.id},
    )
    await db.commit()
    await db.refresh(placement)
    return {"placement_id": placement.id, "industry_mentor_account_id": target.id, "industry_mentor_name": target.full_name}


@router.get("/work-logs/me")
async def my_work_logs(account: CurrentAccount, db: DbSession) -> dict:
    await require_role(db, account, "STUDENT")
    student = await db.scalar(select(StudentProfile).where(StudentProfile.account_id == account.id))
    if student is None:
        raise HTTPException(status_code=404, detail="Student profile not found")
    items = list((await db.execute(
        select(InternshipWorkLog).where(InternshipWorkLog.student_id == student.id)
        .order_by(InternshipWorkLog.work_date.desc(), InternshipWorkLog.created_at.desc())
    )).scalars().all())
    return {"items": await _logs_payload(db, items)}


@router.get("/placements/{placement_id}/work-logs")
async def placement_work_logs(placement_id: str, account: CurrentAccount, db: DbSession) -> dict:
    await _authorized_placement(db, account, placement_id)
    items = list((await db.execute(
        select(InternshipWorkLog).where(InternshipWorkLog.placement_id == placement_id)
        .order_by(InternshipWorkLog.work_date.desc(), InternshipWorkLog.created_at.desc())
    )).scalars().all())
    return {"items": await _logs_payload(db, items)}


@router.post("/placements/{placement_id}/work-logs", status_code=201)
async def create_work_log(
    placement_id: str, payload: WorkLogCreate, account: CurrentAccount, db: DbSession
) -> dict:
    placement, actor_role = await _authorized_placement(db, account, placement_id)
    if actor_role != "STUDENT":
        raise HTTPException(status_code=403, detail="Only the placement student can create a work log")
    if placement.status != "ONGOING":
        raise HTTPException(status_code=409, detail="Work logs can only be created for an ongoing placement")
    if payload.work_date < placement.start_date or payload.work_date > placement.end_date:
        raise HTTPException(status_code=422, detail="Work date must fall within the placement dates")
    item = InternshipWorkLog(
        id=str(uuid4()), placement_id=placement.id, student_id=placement.student_id,
        work_date=payload.work_date, duration_minutes=payload.duration_minutes,
        work_summary=payload.work_summary, tasks_completed=payload.tasks_completed,
        skills_used=payload.skills_used, challenges=payload.challenges,
        learning_outcomes=payload.learning_outcomes, next_steps=payload.next_steps, status="DRAFT",
    )
    db.add(item)
    AuditService(db).record(
        account.id, await _institution_for_placement(db, placement),
        "internship.work_log_created", "internship_work_log", item.id,
        {"placement_id": placement.id, "work_date": payload.work_date.isoformat()},
    )
    await db.commit()
    await db.refresh(item)
    return _work_log_payload(item)


async def _can_edit_work_log(db: AsyncSession, item: InternshipWorkLog) -> bool:
    if item.status == "DRAFT":
        return True
    if item.status != "SUBMITTED" or item.submitted_at is None:
        return False
    reviews = (await db.execute(
        select(InternshipWorkLogReview).where(
            InternshipWorkLogReview.work_log_id == item.id,
            InternshipWorkLogReview.created_at >= item.submitted_at,
        ).order_by(InternshipWorkLogReview.created_at.desc())
    )).scalars().all()
    latest_by_role: dict[str, InternshipWorkLogReview] = {}
    for review in reviews:
        latest_by_role.setdefault(review.reviewer_role, review)
    return any(review.decision == "REVISION_REQUIRED" for review in latest_by_role.values())


@router.patch("/work-logs/{work_log_id}")
async def update_work_log(
    work_log_id: str, payload: WorkLogPatch, account: CurrentAccount, db: DbSession
) -> dict:
    item = await db.get(InternshipWorkLog, work_log_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Work log not found")
    placement, actor_role = await _authorized_placement(db, account, item.placement_id)
    if actor_role != "STUDENT":
        raise HTTPException(status_code=403, detail="Only the placement student can edit a work log")
    if not await _can_edit_work_log(db, item):
        raise HTTPException(status_code=409, detail="This work log cannot be edited until a mentor requests revision")
    changes = payload.model_dump(exclude_unset=True)
    if not changes:
        raise HTTPException(status_code=422, detail="At least one field must be updated")
    if "work_date" in changes and changes["work_date"] is None:
        raise HTTPException(status_code=422, detail="work_date cannot be null")
    if "work_summary" in changes and changes["work_summary"] is None:
        raise HTTPException(status_code=422, detail="work_summary cannot be null")
    work_date = changes.get("work_date", item.work_date)
    if work_date is not None and (work_date < placement.start_date or work_date > placement.end_date):
        raise HTTPException(status_code=422, detail="Work date must fall within the placement dates")
    for key, value in changes.items():
        setattr(item, key, value)
    item.status = "DRAFT"
    AuditService(db).record(
        account.id, await _institution_for_placement(db, placement),
        "internship.work_log_updated", "internship_work_log", item.id,
        {"placement_id": placement.id},
    )
    await db.commit()
    await db.refresh(item)
    reviews = await _reviews_for_logs(db, [item.id])
    return _work_log_payload(item, reviews.get(item.id, []))


@router.post("/work-logs/{work_log_id}/submit")
async def submit_work_log(work_log_id: str, account: CurrentAccount, db: DbSession) -> dict:
    item = await db.get(InternshipWorkLog, work_log_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Work log not found")
    placement, actor_role = await _authorized_placement(db, account, item.placement_id)
    if actor_role != "STUDENT":
        raise HTTPException(status_code=403, detail="Only the placement student can submit a work log")
    if item.status != "DRAFT":
        raise HTTPException(status_code=409, detail="Only a draft work log can be submitted")
    if not item.work_summary.strip():
        raise HTTPException(status_code=422, detail="Work summary is required")
    if item.work_date < placement.start_date or item.work_date > placement.end_date:
        raise HTTPException(status_code=422, detail="Work date must fall within the placement dates")
    item.status = "SUBMITTED"
    item.submitted_at = datetime.now(UTC).replace(tzinfo=None, microsecond=0)
    AuditService(db).record(
        account.id, await _institution_for_placement(db, placement),
        "internship.work_log_submitted", "internship_work_log", item.id,
        {"placement_id": placement.id},
    )
    await db.commit()
    await db.refresh(item)
    reviews = await _reviews_for_logs(db, [item.id])
    return _work_log_payload(item, reviews.get(item.id, []))


@router.get("/work-logs/{work_log_id}/reviews")
async def work_log_reviews(work_log_id: str, account: CurrentAccount, db: DbSession) -> dict:
    item = await db.get(InternshipWorkLog, work_log_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Work log not found")
    await _authorized_placement(db, account, item.placement_id)
    reviews = await _reviews_for_logs(db, [item.id])
    return {"items": reviews.get(item.id, [])}


@router.post("/work-logs/{work_log_id}/reviews", status_code=201)
async def review_work_log(
    work_log_id: str, payload: WorkLogReviewCreate, account: CurrentAccount, db: DbSession
) -> dict:
    item = await db.get(InternshipWorkLog, work_log_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Work log not found")
    placement, actor_role = await _authorized_placement(db, account, item.placement_id)
    if actor_role not in {"FACULTY", "INDUSTRY_MENTOR"}:
        raise HTTPException(status_code=403, detail="Only an assigned mentor can review a work log")
    if item.status != "SUBMITTED":
        raise HTTPException(status_code=409, detail="Only submitted work logs can be reviewed")
    review = InternshipWorkLogReview(
        id=str(uuid4()), work_log_id=item.id, reviewer_account_id=account.id,
        reviewer_role=actor_role, decision=payload.decision, feedback=payload.feedback,
    )
    db.add(review)
    AuditService(db).record(
        account.id, await _institution_for_placement(db, placement),
        "internship.work_log_reviewed", "internship_work_log_review", review.id,
        {"placement_id": placement.id, "work_log_id": item.id, "reviewer_role": actor_role, "decision": payload.decision},
    )
    await db.commit()
    await db.refresh(review)
    reviewer = await db.get(Account, account.id)
    return {
        "id": review.id, "work_log_id": review.work_log_id,
        "reviewer_account_id": review.reviewer_account_id,
        "reviewer_name": reviewer.full_name if reviewer else None,
        "reviewer_role": review.reviewer_role, "decision": review.decision,
        "feedback": review.feedback,
        "created_at": review.created_at.isoformat() if review.created_at else None,
    }
