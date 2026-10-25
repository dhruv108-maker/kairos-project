"""New modular internship API, mounted at /api/v1/modules/internships."""
import logging
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, text
from datetime import date
from uuid import uuid4
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.dependencies import CurrentAccount, DbSession, account_roles, require_role
from app.models.internship import InternshipApplication, InternshipOpportunity, InternshipProvider, InternshipWorkLog, InternshipWorkLogReview, InternshipPlacement
from app.models.academic import Account, Department, FacultyProfile, Programme, School, StudentProfile
from app.models.employers import EmployerMembership
from app.models.institutions import Institution
from app.services.email import send_work_log_notification
from app.core.config import settings
from app.modules.shared.exceptions import KairosDomainError
from app.modules.internships.schemas import ApplicationStatusUpdate, OpportunityCreate, PlacementCreate, ProviderCreate, WorkLogCreate, WorkLogReviewCreate
from app.modules.internships.repository import InternshipRepository
from app.modules.internships.service import InternshipService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/internships", tags=["internships-modular"])
ADMIN_ROLES = ("SYSTEM_ADMIN", "DEAN", "DEPT_HEAD")
MANAGER_ROLES = (*ADMIN_ROLES, "FACULTY")

async def _require_any_role(db: AsyncSession, account, allowed: tuple[str, ...]) -> None:
    roles = await account_roles(db, account.id)
    if not set(roles).intersection(allowed): raise HTTPException(status_code=403, detail="Insufficient role")

def _error(exc: KairosDomainError) -> HTTPException:
    return HTTPException(status_code=exc.status_code, detail={"code": exc.code, "message": str(exc)})

def _opp(item: InternshipOpportunity, provider: InternshipProvider | None = None) -> dict:
    return {"id": item.id, "provider_id": item.provider_id, "company_name": provider.company_name if provider else None, "title": item.title, "description": item.description, "location": item.location, "stipend_amount": str(item.stipend_amount), "application_deadline": item.application_deadline.isoformat(), "is_active": item.is_active, "created_at": item.created_at.isoformat() if item.created_at else None}
def _app(item) -> dict:
    return {"id": item.id, "opportunity_id": item.opportunity_id, "student_id": item.student_id, "status": item.status, "applied_at": item.applied_at.isoformat() if item.applied_at else None}
def _placement(item) -> dict:
    return {"id": item.id, "application_id": item.application_id, "student_id": item.student_id, "faculty_supervisor_id": item.faculty_supervisor_id, "industry_mentor_account_id": item.industry_mentor_account_id, "start_date": item.start_date.isoformat(), "end_date": item.end_date.isoformat(), "status": item.status}

def _review_payload(item: InternshipWorkLogReview) -> dict:
    role = {"faculty_mentor": "FACULTY", "industry_mentor": "INDUSTRY_MENTOR"}.get(item.reviewer_role, item.reviewer_role)
    return {
        "id": item.id,
        "decision": item.decision.upper(),
        "feedback": item.feedback,
        "reviewer_role": role,
        "created_at": item.created_at.isoformat() if item.created_at else None,
    }


async def _legacy_reviewer_profile_id(db: AsyncSession, role: str, account_id: str) -> int:
    if role == "FACULTY":
        profile_id = await db.scalar(
            text("SELECT id FROM faculty WHERE account_id = :account_id"),
            {"account_id": account_id},
        )
    else:
        profile_id = await db.scalar(
            text("SELECT id FROM industry_mentors WHERE account_id = :account_id"),
            {"account_id": account_id},
        )
    if profile_id is None:
        label = "Faculty" if role == "FACULTY" else "Industry mentor"
        raise HTTPException(status_code=404, detail=f"{label} record not found")
    return int(profile_id)

@router.get("/opportunities")
async def list_opportunities(account: CurrentAccount, db: DbSession, q: str | None = Query(default=None, max_length=100), location: str | None = Query(default=None, max_length=150), limit: int = Query(default=50, ge=1, le=100), offset: int = Query(default=0, ge=0)) -> dict:
    rows = await InternshipRepository(db).list_active_opportunities(query=q, location=location, limit=limit, offset=offset)
    return {"items": [_opp(item, provider) for item, provider in rows], "limit": limit, "offset": offset}

@router.post("/providers", status_code=201)
async def create_provider(payload: ProviderCreate, account: CurrentAccount, db: DbSession) -> dict:
    await _require_any_role(db, account, ADMIN_ROLES)
    item = await InternshipService(db).create_provider(payload.model_dump())
    return {"id": item.id, "company_name": item.company_name, "website": item.website, "industry_sector": item.industry_sector, "contact_person_name": item.contact_person_name, "contact_email": item.contact_email, "created_at": item.created_at.isoformat() if item.created_at else None}

@router.post("/opportunities", status_code=201)
async def create_opportunity(payload: OpportunityCreate, account: CurrentAccount, db: DbSession) -> dict:
    await _require_any_role(db, account, MANAGER_ROLES)
    try: item, provider = await InternshipService(db).create_opportunity(payload.model_dump())
    except KairosDomainError as exc: raise _error(exc) from None
    return _opp(item, provider)

@router.post("/opportunities/{opportunity_id}/applications", status_code=201)
async def apply(opportunity_id: str, account: CurrentAccount, db: DbSession) -> dict:
    await require_role(db, account, "STUDENT")
    try: item = await InternshipService(db).apply(account.id, opportunity_id)
    except KairosDomainError as exc: raise _error(exc) from None
    return _app(item)

@router.get("/applications/me")
async def my_applications(account: CurrentAccount, db: DbSession) -> dict:
    await require_role(db, account, "STUDENT")
    repository = InternshipRepository(db)
    student = await repository.get_student_by_account(account.id)
    if student is None: raise HTTPException(status_code=404, detail="Student profile not found")
    rows = await repository.list_applications_for_student(student.id)
    return {"items": [{"id": item.id, "status": item.status, "applied_at": item.applied_at.isoformat() if item.applied_at else None, "opportunity": _opp(opp, provider)} for item, opp, provider in rows]}

@router.post("/applications/{application_id}/withdraw")
async def withdraw(application_id: str, account: CurrentAccount, db: DbSession) -> dict:
    await require_role(db, account, "STUDENT")
    try: item = await InternshipService(db).withdraw(account.id, application_id)
    except KairosDomainError as exc: raise _error(exc) from None
    return {"id": item.id, "status": item.status}

@router.patch("/applications/{application_id}/status")
async def update_status(application_id: str, payload: ApplicationStatusUpdate, account: CurrentAccount, db: DbSession) -> dict:
    await _require_any_role(db, account, MANAGER_ROLES)
    try: item = await InternshipService(db).transition_application(application_id, payload.status)
    except KairosDomainError as exc: raise _error(exc) from None
    return {"id": item.id, "status": item.status}

@router.post("/applications/{application_id}/placement", status_code=201)
async def create_placement(application_id: str, payload: PlacementCreate, account: CurrentAccount, db: DbSession) -> dict:
    await _require_any_role(db, account, MANAGER_ROLES)
    try: item = await InternshipService(db).create_placement(application_id, payload.model_dump())
    except KairosDomainError as exc: raise _error(exc) from None
    return _placement(item)


def _work_log(item: InternshipWorkLog) -> dict:
    return {"id": item.id, "placement_id": item.placement_id, "work_date": item.work_date.isoformat(),
            "summary": item.summary, "tasks_completed": item.tasks_completed, "skills_used": item.skills_used,
            "challenges": item.challenges, "learning_outcomes": item.learning_outcomes, "next_steps": item.next_steps,
            "status": item.status, "created_at": item.created_at.isoformat() if item.created_at else None,
            "updated_at": item.updated_at.isoformat() if item.updated_at else None}



async def _academic_email_context(db: AsyncSession, student: StudentProfile) -> tuple[str, str, str]:
    department_name = ""
    programme_name = ""
    institution_name = ""
    if student.department_id:
        department = await db.get(Department, student.department_id)
        if department is not None:
            department_name = department.name
            school = await db.get(School, department.school_id)
            if school is not None and school.institution_id:
                institution = await db.get(Institution, school.institution_id)
                if institution is not None:
                    institution_name = institution.name
    if student.programme_id:
        programme = await db.get(Programme, student.programme_id)
        if programme is not None:
            programme_name = programme.name
    return institution_name, programme_name, department_name


async def _notify_progress_log_mentors(
    db: AsyncSession,
    *,
    student: StudentProfile,
    student_account: Account,
    placement: InternshipPlacement,
    log: InternshipWorkLog,
) -> dict:
    """Best-effort email after commit; the work-log transaction is never rolled back."""
    institution_name, programme_name, department_name = await _academic_email_context(db, student)
    application = await db.get(InternshipApplication, placement.application_id)
    opportunity = await db.get(InternshipOpportunity, application.opportunity_id) if application else None
    provider = await db.get(InternshipProvider, opportunity.provider_id) if opportunity else None
    recipients: list[tuple[str, Account, str]] = []

    if placement.faculty_supervisor_id:
        faculty = await db.get(FacultyProfile, placement.faculty_supervisor_id)
        faculty_account = await db.get(Account, faculty.account_id) if faculty else None
        if faculty_account and faculty_account.is_active and faculty_account.is_verified and faculty_account.email:
            recipients.append(("faculty", faculty_account, faculty_account.email))

    if placement.industry_mentor_account_id:
        industry_account = await db.get(Account, placement.industry_mentor_account_id)
        if (
            industry_account
            and industry_account.is_active
            and industry_account.is_verified
            and industry_account.email
            and await _is_active_assigned_industry_mentor(db, placement, industry_account.id)
        ):
            recipients.append(("industry", industry_account, industry_account.email))

    # Never send the same log twice to one address if assignments happen to converge.
    unique_recipients: dict[str, tuple[str, Account, str]] = {}
    for role, recipient, email in recipients:
        unique_recipients.setdefault(email.strip().lower(), (role, recipient, email))
    if not unique_recipients:
        return {"status": "NO_ELIGIBLE_MENTORS", "accepted_by_provider": 0, "failed": 0}

    submitted_at = log.updated_at or log.created_at
    readable_timestamp = submitted_at.isoformat() if submitted_at else "Not recorded"
    view_url = f"{settings.FRONTEND_URL.rstrip('/')}/internships/during?log={log.id}"
    fields = {
        "Student": student_account.full_name,
        "ERN / Enrollment Number": student.enrollment_number,
        "Institution": institution_name or "Not recorded in academic profile",
        "Programme": programme_name,
        "Department": department_name,
        "Internship / Placement": opportunity.title if opportunity else (provider.company_name if provider else placement.id),
        "Submitted at (UTC)": readable_timestamp,
        "Progress log reference": log.id,
        "Progress update": log.summary,
        "Work completed": log.tasks_completed,
        "Challenges and blockers": log.challenges or "",
        "Learning outcomes": log.learning_outcomes or log.skills_used or "",
        "Next steps": log.next_steps or "",
    }
    accepted = 0
    failed = 0
    for role, recipient, email in unique_recipients.values():
        try:
            await send_work_log_notification(
                to=email,
                subject=f"[Kairos] Student Progress Update — {student_account.full_name} — {student.enrollment_number}",
                heading="Student Progress Update",
                fields=fields,
                message=log.summary,
                view_url=view_url,
                idempotency_key=f"progress-log:{log.id}:{role}:{recipient.id}",
            )
            accepted += 1
        except Exception as exc:
            # The log is already committed. Do not leak provider responses or student text.
            failed += 1
            logger.warning("Progress-log notification failed; log_id=%s recipient_role=%s error_type=%s",
                           log.id, role, type(exc).__name__)
    return {
        "status": "ACCEPTED_BY_PROVIDER" if failed == 0 else ("PARTIALLY_ACCEPTED" if accepted else "FAILED"),
        "accepted_by_provider": accepted,
        "failed": failed,
    }


async def _notify_student_feedback(
    db: AsyncSession,
    *,
    log: InternshipWorkLog,
    reviewer_role: str,
    decision: str,
    feedback: str,
    review_id: str,
) -> str:
    student_account = await db.scalar(
        select(Account).join(StudentProfile, Account.id == StudentProfile.account_id)
        .where(StudentProfile.id == log.student_id)
    )
    if student_account is None or not student_account.email or not student_account.is_active:
        return "STUDENT_ACCOUNT_UNAVAILABLE"
    try:
        await send_work_log_notification(
            to=student_account.email,
            subject=f"[Kairos] Mentor feedback on your progress log — {log.summary}",
            heading="Mentor feedback on your progress log",
            fields={
                "Progress log reference": log.id,
                "Progress update": log.summary,
                "Reviewer type": reviewer_role,
                "Review decision": decision.replace("_", " ").title(),
                "Feedback": feedback,
            },
            message="Your mentor has recorded feedback in Kairos. Sign in to review the complete history and plan your next steps.",
            view_url=f"{settings.FRONTEND_URL.rstrip('/')}/internships/during?log={log.id}",
            idempotency_key=f"progress-feedback:{log.id}:{review_id}",
        )
        return "ACCEPTED_BY_PROVIDER"
    except Exception as exc:
        logger.warning("Progress feedback notification failed; log_id=%s reviewer_role=%s error_type=%s",
                       log.id, reviewer_role, type(exc).__name__)
        return "FAILED"




@router.get("/placements/me")
async def my_placements(account: CurrentAccount, db: DbSession) -> dict:
    await require_role(db, account, "STUDENT")
    repo = InternshipRepository(db)
    student = await repo.get_student_by_account(account.id)
    if student is None:
        raise HTTPException(status_code=404, detail="Student profile not found")
    rows = await repo.list_placements_for_student(student.id)
    return {"items": [{"id": p.id, "application_id": p.application_id, "student_id": p.student_id,
        "faculty_supervisor_id": p.faculty_supervisor_id, "industry_mentor_account_id": p.industry_mentor_account_id, "start_date": p.start_date.isoformat(),
        "end_date": p.end_date.isoformat(), "status": p.status} for p in rows]}


@router.get("/placements/supervised")
async def supervised_placements(account: CurrentAccount, db: DbSession) -> dict:
    await require_role(db, account, "FACULTY")
    faculty = await db.scalar(select(FacultyProfile).where(FacultyProfile.account_id == account.id))
    if faculty is None:
        raise HTTPException(status_code=404, detail="Faculty profile not found")
    rows = (await db.execute(
        select(InternshipPlacement).where(InternshipPlacement.faculty_supervisor_id == faculty.id)
        .order_by(InternshipPlacement.start_date.desc())
    )).scalars().all()
    return {"items": [{"id": p.id, "application_id": p.application_id, "student_id": p.student_id,
        "faculty_supervisor_id": p.faculty_supervisor_id, "start_date": p.start_date.isoformat(),
        "end_date": p.end_date.isoformat(), "status": p.status} for p in rows]}


@router.get("/work-logs/supervised")
async def supervised_work_logs(account: CurrentAccount, db: DbSession, placement_id: str | None = None) -> dict:
    await require_role(db, account, "FACULTY")
    faculty = await db.scalar(select(FacultyProfile).where(FacultyProfile.account_id == account.id))
    if faculty is None:
        raise HTTPException(status_code=404, detail="Faculty profile not found")
    stmt = select(InternshipWorkLog).join(
        InternshipPlacement, InternshipPlacement.id == InternshipWorkLog.placement_id
    ).where(InternshipPlacement.faculty_supervisor_id == faculty.id)
    if placement_id:
        stmt = stmt.where(InternshipPlacement.id == placement_id)
    logs = (await db.execute(stmt.order_by(InternshipWorkLog.work_date.desc(), InternshipWorkLog.created_at.desc()))).scalars().all()
    return {"items": [_work_log(item) for item in logs]}




async def _is_active_assigned_industry_mentor(db: AsyncSession, placement: InternshipPlacement, account_id: str) -> bool:
    if placement.industry_mentor_account_id != account_id:
        return False
    application = await db.get(InternshipApplication, placement.application_id)
    if application is None:
        return False
    opportunity = await db.get(InternshipOpportunity, application.opportunity_id)
    if opportunity is None:
        return False
    provider = await db.get(InternshipProvider, opportunity.provider_id)
    if provider is None or not provider.employer_organization_id:
        return False
    membership = await db.scalar(select(EmployerMembership).where(
        EmployerMembership.organization_id == provider.employer_organization_id,
        EmployerMembership.account_id == account_id,
        EmployerMembership.status == "ACTIVE",
    ))
    return membership is not None


@router.get("/placements/mentor/me")
async def industry_mentor_placements(account: CurrentAccount, db: DbSession) -> dict:
    rows = (await db.execute(
        select(InternshipPlacement, InternshipOpportunity, InternshipProvider, StudentProfile, Account)
        .join(InternshipApplication, InternshipApplication.id == InternshipPlacement.application_id)
        .join(InternshipOpportunity, InternshipOpportunity.id == InternshipApplication.opportunity_id)
        .join(InternshipProvider, InternshipProvider.id == InternshipOpportunity.provider_id)
        .join(EmployerMembership, (EmployerMembership.organization_id == InternshipProvider.employer_organization_id)
              & (EmployerMembership.account_id == account.id) & (EmployerMembership.status == "ACTIVE"))
        .join(StudentProfile, StudentProfile.id == InternshipPlacement.student_id)
        .join(Account, Account.id == StudentProfile.account_id)
        .where(InternshipPlacement.industry_mentor_account_id == account.id)
        .order_by(InternshipPlacement.start_date.desc())
    )).all()
    items = []
    for placement, opportunity, provider, student, student_account in rows:
        latest_log = await db.scalar(select(InternshipWorkLog).where(
            InternshipWorkLog.placement_id == placement.id
        ).order_by(InternshipWorkLog.work_date.desc(), InternshipWorkLog.created_at.desc()).limit(1))
        items.append({
            "id": placement.id, "application_id": placement.application_id, "student_id": placement.student_id,
            "student_name": student_account.full_name, "student_enrollment_number": student.enrollment_number,
            "opportunity_title": opportunity.title, "company_name": provider.company_name,
            "start_date": placement.start_date.isoformat(), "end_date": placement.end_date.isoformat(),
            "status": placement.status, "latest_work_log_at": latest_log.work_date.isoformat() if latest_log else None,
        })
    return {"items": items}


@router.get("/work-logs/mentor/me")
async def industry_mentor_work_logs(account: CurrentAccount, db: DbSession) -> dict:
    rows = (await db.execute(
        select(InternshipWorkLog, InternshipPlacement, InternshipOpportunity, InternshipProvider, Account)
        .join(InternshipPlacement, InternshipPlacement.id == InternshipWorkLog.placement_id)
        .join(InternshipApplication, InternshipApplication.id == InternshipPlacement.application_id)
        .join(InternshipOpportunity, InternshipOpportunity.id == InternshipApplication.opportunity_id)
        .join(InternshipProvider, InternshipProvider.id == InternshipOpportunity.provider_id)
        .join(EmployerMembership, (EmployerMembership.organization_id == InternshipProvider.employer_organization_id)
              & (EmployerMembership.account_id == account.id) & (EmployerMembership.status == "ACTIVE"))
        .join(StudentProfile, StudentProfile.id == InternshipPlacement.student_id)
        .join(Account, Account.id == StudentProfile.account_id)
        .where(InternshipPlacement.industry_mentor_account_id == account.id)
        .order_by(InternshipWorkLog.work_date.desc(), InternshipWorkLog.created_at.desc())
    )).all()
    items = []
    for log, placement, opportunity, provider, student_account in rows:
        latest_review = await db.scalar(select(InternshipWorkLogReview).where(
            InternshipWorkLogReview.work_log_id == log.id
        ).order_by(InternshipWorkLogReview.created_at.desc()).limit(1))
        items.append({
            **_work_log(log), "student_name": student_account.full_name,
            "opportunity_title": opportunity.title, "company_name": provider.company_name,
            "latest_review": _review_payload(latest_review) if latest_review else None,
        })
    return {"items": items}


@router.post("/work-logs/{work_log_id}/mentor-review")
async def industry_mentor_review_work_log(work_log_id: str, payload: WorkLogReviewCreate, account: CurrentAccount, db: DbSession) -> dict:
    row = await db.get(InternshipWorkLog, work_log_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Work log not found")
    placement = await db.get(InternshipPlacement, row.placement_id)
    if placement is None or not await _is_active_assigned_industry_mentor(db, placement, account.id):
        raise HTTPException(status_code=404, detail="Work log not found")
    if row.status not in {"SUBMITTED", "INDUSTRY_REVIEWED", "REVIEWED"}:
        raise HTTPException(status_code=409, detail="Only submitted work logs can be reviewed")
    mentor_id = await _legacy_reviewer_profile_id(db, "INDUSTRY_MENTOR", account.id)
    review = InternshipWorkLogReview(
        work_log_id=row.id, reviewer_account_id=account.id,
        reviewer_role="industry_mentor", decision=payload.decision.lower(),
        feedback=payload.feedback.strip(), industry_mentor_id=mentor_id,
    )
    db.add(review)
    # Industry review is a separate gate; faculty review still follows acknowledgement.
    # Keep each mentor's decision independent. A revision request is feedback,
    # not permission to mutate a submitted log or erase the other mentor's review.
    if payload.decision == "ACKNOWLEDGED" and row.status != "REVIEWED":
        faculty_ack = await db.scalar(select(InternshipWorkLogReview.id).where(
            InternshipWorkLogReview.work_log_id == row.id,
            InternshipWorkLogReview.reviewer_role == "faculty_mentor",
            InternshipWorkLogReview.decision == "acknowledged",
        ).limit(1))
        row.status = "REVIEWED" if faculty_ack or not placement.faculty_supervisor_id else "INDUSTRY_REVIEWED"
    await db.commit()
    await db.refresh(row)
    await db.refresh(review)
    notification_status = await _notify_student_feedback(
        db, log=row, reviewer_role="industry mentor",
        decision=review.decision, feedback=review.feedback, review_id=str(review.id),
    )
    return {"work_log": _work_log(row), "review": _review_payload(review),
            "student_notification_status": notification_status}


@router.get("/work-logs/me")
async def my_work_logs(account: CurrentAccount, db: DbSession, placement_id: str | None = None) -> dict:
    await require_role(db, account, "STUDENT")
    repo = InternshipRepository(db)
    student = await repo.get_student_by_account(account.id)
    if student is None:
        raise HTTPException(status_code=404, detail="Student profile not found")
    if placement_id:
        placement = await db.get(InternshipPlacement, placement_id)
        if placement is None or placement.student_id != student.id:
            raise HTTPException(status_code=404, detail="Placement not found")
    logs = await repo.list_work_logs_for_student(student.id, placement_id)
    review_rows = await db.execute(select(InternshipWorkLogReview).where(
        InternshipWorkLogReview.work_log_id.in_([item.id for item in logs] or ["__none__"])
    ).order_by(InternshipWorkLogReview.created_at.desc()))
    reviews = list(review_rows.scalars().all())
    latest_by_log: dict[str, InternshipWorkLogReview] = {}
    reviews_by_log: dict[str, list[dict]] = {}
    for review in reviews:
        review_log_id = str(review.work_log_id)
        latest_by_log.setdefault(review_log_id, review)
        reviews_by_log.setdefault(review_log_id, []).append(_review_payload(review))
    institution_name, programme_name, department_name = await _academic_email_context(db, student)
    return {
        "student_identity": {
            "name": account.full_name,
            "enrollment_number": student.enrollment_number,
            "institution_name": institution_name or None,
            "programme_name": programme_name or None,
            "department_name": department_name or None,
        },
        "items": [{**_work_log(item),
                   "latest_review": _review_payload(latest_by_log[str(item.id)]) if str(item.id) in latest_by_log else None,
                   "reviews": reviews_by_log.get(str(item.id), [])}
                  for item in logs],
    }


@router.post("/work-logs", status_code=201)
async def create_work_log(payload: WorkLogCreate, account: CurrentAccount, db: DbSession) -> dict:
    await require_role(db, account, "STUDENT")
    repo = InternshipRepository(db)
    student = await repo.get_student_by_account(account.id)
    if student is None:
        raise HTTPException(status_code=404, detail="Student profile not found")
    placement = await db.get(InternshipPlacement, payload.placement_id)
    if placement is None or placement.student_id != student.id:
        raise HTTPException(status_code=404, detail="Placement not found")
    if placement.status != "ONGOING":
        raise HTTPException(status_code=409, detail="Work logs require an ongoing placement")
    if payload.work_date > date.today():
        raise HTTPException(status_code=422, detail="work_date cannot be in the future")
    row = InternshipWorkLog(id=str(uuid4()), placement_id=placement.id, student_id=student.id,
        work_date=payload.work_date, summary=payload.summary, tasks_completed=payload.tasks_completed,
        skills_used=payload.skills_used, challenges=payload.challenges, learning_outcomes=payload.learning_outcomes,
        next_steps=payload.next_steps, status="DRAFT")
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return _work_log(row)


@router.patch("/work-logs/{work_log_id}")
async def update_work_log(work_log_id: str, payload: WorkLogCreate, account: CurrentAccount, db: DbSession) -> dict:
    await require_role(db, account, "STUDENT")
    repo = InternshipRepository(db)
    student = await repo.get_student_by_account(account.id)
    if student is None:
        raise HTTPException(status_code=404, detail="Student profile not found")
    row = await db.get(InternshipWorkLog, work_log_id)
    if row is None or row.student_id != student.id:
        raise HTTPException(status_code=404, detail="Work log not found")
    if row.status != "DRAFT":
        raise HTTPException(status_code=409, detail="Only draft work logs can be edited")
    if payload.placement_id != row.placement_id:
        raise HTTPException(status_code=409, detail="Work log placement cannot be changed")
    placement = await db.get(InternshipPlacement, row.placement_id)
    if placement is None or placement.status != "ONGOING":
        raise HTTPException(status_code=409, detail="Work logs require an ongoing placement")
    if payload.work_date > date.today():
        raise HTTPException(status_code=422, detail="work_date cannot be in the future")
    for field in ("work_date", "summary", "tasks_completed", "skills_used", "challenges", "learning_outcomes", "next_steps"):
        setattr(row, field, getattr(payload, field))
    row.status = "DRAFT"
    await db.commit()
    await db.refresh(row)
    return _work_log(row)


@router.post("/work-logs/{work_log_id}/submit")
async def submit_work_log(work_log_id: str, account: CurrentAccount, db: DbSession) -> dict:
    await require_role(db, account, "STUDENT")
    repo = InternshipRepository(db)
    student = await repo.get_student_by_account(account.id)
    row = await db.get(InternshipWorkLog, work_log_id)
    if student is None or row is None or row.student_id != student.id:
        raise HTTPException(status_code=404, detail="Work log not found")
    if row.status != "DRAFT":
        raise HTTPException(status_code=409, detail="Only a draft work log can be submitted")
    placement = await db.get(InternshipPlacement, row.placement_id)
    if placement is None or placement.status != "ONGOING":
        raise HTTPException(status_code=409, detail="Work logs require an ongoing placement")
    row.status = "SUBMITTED"
    await db.commit()
    await db.refresh(row)
    notification_status = await _notify_progress_log_mentors(
        db, student=student, student_account=account, placement=placement, log=row,
    )
    return {**_work_log(row), "notification_status": notification_status}


@router.get("/work-logs/{work_log_id}/reviews")
async def list_work_log_reviews(work_log_id: str, account: CurrentAccount, db: DbSession) -> dict:
    await require_role(db, account, "STUDENT")
    repo = InternshipRepository(db)
    student = await repo.get_student_by_account(account.id)
    row = await db.get(InternshipWorkLog, work_log_id)
    if student is None or row is None or row.student_id != student.id:
        raise HTTPException(status_code=404, detail="Work log not found")
    reviews = (await db.execute(select(InternshipWorkLogReview).where(
        InternshipWorkLogReview.work_log_id == row.id
    ).order_by(InternshipWorkLogReview.created_at.desc()))).scalars().all()
    return {"items": [_review_payload(review) for review in reviews]}


@router.post("/work-logs/{work_log_id}/review")
async def review_work_log(work_log_id: str, payload: WorkLogReviewCreate, account: CurrentAccount, db: DbSession) -> dict:
    await require_role(db, account, "FACULTY")
    faculty = await db.scalar(select(FacultyProfile).where(FacultyProfile.account_id == account.id))
    if faculty is None:
        raise HTTPException(status_code=404, detail="Faculty profile not found")
    row = await db.get(InternshipWorkLog, work_log_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Work log not found")
    placement = await db.get(InternshipPlacement, row.placement_id)
    if placement is None or placement.faculty_supervisor_id != faculty.id:
        raise HTTPException(status_code=404, detail="Work log not found")
    if row.status not in {"SUBMITTED", "INDUSTRY_REVIEWED", "REVIEWED"}:
        raise HTTPException(status_code=409, detail="Only submitted work logs can be reviewed")
    faculty_id = await _legacy_reviewer_profile_id(db, "FACULTY", account.id)
    review = InternshipWorkLogReview(
        work_log_id=row.id, reviewer_account_id=account.id,
        reviewer_role="faculty_mentor", decision=payload.decision.lower(),
        feedback=payload.feedback.strip(), faculty_id=faculty_id,
    )
    db.add(review)
    if payload.decision == "ACKNOWLEDGED":
        industry_ack = await db.scalar(select(InternshipWorkLogReview.id).where(
            InternshipWorkLogReview.work_log_id == row.id,
            InternshipWorkLogReview.reviewer_role == "industry_mentor",
            InternshipWorkLogReview.decision == "acknowledged",
        ).limit(1))
        row.status = "REVIEWED" if industry_ack or not placement.industry_mentor_account_id else "SUBMITTED"
    await db.commit()
    await db.refresh(row)
    await db.refresh(review)
    notification_status = await _notify_student_feedback(
        db, log=row, reviewer_role="faculty mentor",
        decision=review.decision, feedback=review.feedback, review_id=str(review.id),
    )
    return {"work_log": _work_log(row), "review": {"id": review.id, "decision": review.decision,
        "feedback": review.feedback, "reviewer_role": review.reviewer_role,
        "created_at": review.created_at.isoformat() if review.created_at else None},
        "student_notification_status": notification_status}


@router.get("/work-logs/{work_log_id}")
async def get_work_log(work_log_id: str, account: CurrentAccount, db: DbSession) -> dict:
    roles = await account_roles(db, account.id)
    row = await db.get(InternshipWorkLog, work_log_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Work log not found")
    if "STUDENT" in roles:
        repo = InternshipRepository(db)
        student = await repo.get_student_by_account(account.id)
        if student is None or row.student_id != student.id:
            raise HTTPException(status_code=404, detail="Work log not found")
    elif "FACULTY" in roles:
        faculty = await db.scalar(select(FacultyProfile).where(FacultyProfile.account_id == account.id))
        placement = await db.get(InternshipPlacement, row.placement_id)
        if faculty is None or placement is None or placement.faculty_supervisor_id != faculty.id:
            raise HTTPException(status_code=404, detail="Work log not found")
    else:
        raise HTTPException(status_code=403, detail="Work-log access is not available for this role")
    reviews = (await db.execute(select(InternshipWorkLogReview).where(
        InternshipWorkLogReview.work_log_id == row.id
    ).order_by(InternshipWorkLogReview.created_at.desc()))).scalars().all()
    return {**_work_log(row), "reviews": [_review_payload(item) for item in reviews]}
