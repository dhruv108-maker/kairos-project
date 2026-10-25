"""New modular internship API, mounted at /api/v1/modules/internships."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.dependencies import CurrentAccount, DbSession, account_roles, require_role
from app.models.internship import InternshipOpportunity, InternshipProvider, InternshipWorkLog, InternshipWorkLogReview, InternshipPlacement
from app.models.academic import FacultyProfile
from app.modules.shared.exceptions import KairosDomainError
from app.modules.internships.schemas import ApplicationStatusUpdate, OpportunityCreate, PlacementCreate, ProviderCreate, WorkLogCreate, WorkLogReviewCreate
from app.modules.internships.repository import InternshipRepository
from app.modules.internships.service import InternshipService

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
    return {"id": item.id, "application_id": item.application_id, "student_id": item.student_id, "faculty_supervisor_id": item.faculty_supervisor_id, "start_date": item.start_date.isoformat(), "end_date": item.end_date.isoformat(), "status": item.status}

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


@router.get("/placements/me")
async def my_placements(account: CurrentAccount, db: DbSession) -> dict:
    await require_role(db, account, "STUDENT")
    repo = InternshipRepository(db)
    student = await repo.get_student_by_account(account.id)
    if student is None:
        raise HTTPException(status_code=404, detail="Student profile not found")
    rows = await repo.list_placements_for_student(student.id)
    return {"items": [{"id": p.id, "application_id": p.application_id, "student_id": p.student_id,
        "faculty_supervisor_id": p.faculty_supervisor_id, "start_date": p.start_date.isoformat(),
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
    latest_by_log = {}
    for review in reviews:
        latest_by_log.setdefault(review.work_log_id, review)
    return {"items": [{**_work_log(item), "latest_review": ({
        "decision": latest_by_log[item.id].decision, "feedback": latest_by_log[item.id].feedback,
        "reviewer_role": latest_by_log[item.id].reviewer_role,
        "created_at": latest_by_log[item.id].created_at.isoformat() if latest_by_log[item.id].created_at else None
    } if item.id in latest_by_log else None)} for item in logs]}


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
    from datetime import date as date_type
    from uuid import uuid4
    if payload.work_date > date_type.today():
        raise HTTPException(status_code=422, detail="work_date cannot be in the future")
    row = InternshipWorkLog(id=str(uuid4()), placement_id=placement.id, student_id=student.id,
        work_date=payload.work_date, summary=payload.summary, tasks_completed=payload.tasks_completed,
        skills_used=payload.skills_used, challenges=payload.challenges, learning_outcomes=payload.learning_outcomes,
        next_steps=payload.next_steps, status=payload.status)
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
    for field in ("work_date", "summary", "tasks_completed", "skills_used", "challenges", "learning_outcomes", "next_steps", "status"):
        setattr(row, field, getattr(payload, field))
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
    row.status = "SUBMITTED"
    await db.commit()
    await db.refresh(row)
    return _work_log(row)


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
    return {"items": [{"id": r.id, "decision": r.decision, "feedback": r.feedback,
        "reviewer_role": r.reviewer_role, "created_at": r.created_at.isoformat() if r.created_at else None} for r in reviews]}


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
    if row.status != "SUBMITTED":
        raise HTTPException(status_code=409, detail="Only submitted work logs can be reviewed")
    review = InternshipWorkLogReview(id=str(uuid4()), work_log_id=row.id, reviewer_account_id=account.id,
        reviewer_role="FACULTY", decision=payload.decision, feedback=payload.feedback.strip())
    db.add(review)
    row.status = "REVIEWED" if payload.decision == "ACKNOWLEDGED" else "DRAFT"
    await db.commit()
    await db.refresh(row)
    await db.refresh(review)
    return {"work_log": _work_log(row), "review": {"id": review.id, "decision": review.decision,
        "feedback": review.feedback, "reviewer_role": review.reviewer_role,
        "created_at": review.created_at.isoformat() if review.created_at else None}}
