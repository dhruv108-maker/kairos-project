from fastapi import APIRouter, HTTPException
from sqlalchemy.exc import IntegrityError

from app.api.dependencies import CurrentAccount, DbSession, require_role
from app.modules.institutions.service import InstitutionAccessError
from app.modules.reports.schemas import (
    ReportCreate, ReportReviewUpdate, ReportTitleUpdate, ReportVersionCreate,
    ReportRequirementCreate, ReportRequirementActiveUpdate,
)
from app.modules.reports.service import ReportRequirementService, ReportService, ReportWorkflowError

router = APIRouter(prefix="/reports", tags=["reports and submissions"])
requirement_router = APIRouter(prefix="/institutions/{institution_id}/report-requirements", tags=["report requirements"])


async def _call(operation, db):
    try:
        return await operation
    except (ReportWorkflowError, InstitutionAccessError) as exc:
        raise HTTPException(status_code=exc.status_code, detail=getattr(exc, "message", str(exc))) from None
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail="The report operation conflicts with existing data") from None


def _submission(item):
    return {"id": item.id, "placement_id": item.placement_id, "requirement_id": item.requirement_id,
            "title": item.title, "latest_version_number": item.latest_version_number, "status": item.status,
            "review_feedback": item.review_feedback, "reviewed_by_account_id": item.reviewed_by_account_id, "reviewed_at": item.reviewed_at,
            "created_at": item.created_at, "updated_at": item.updated_at}


def _version(item):
    return {"id": item.id, "submission_id": item.submission_id, "version_number": item.version_number,
            "file_id": item.file_id, "submission_notes": item.submission_notes, "submitted_at": item.submitted_at}


def _requirement(item):
    return {"id": item.id, "institution_id": item.institution_id, "title": item.title,
            "description": item.description, "due_date": item.due_date, "is_required": item.is_required,
            "is_active": item.is_active, "created_by_account_id": item.created_by_account_id,
            "created_at": item.created_at, "updated_at": item.updated_at}


@router.post("", status_code=201)
async def create_report(payload: ReportCreate, account: CurrentAccount, db: DbSession):
    item = await _call(ReportService(db).create(account.id, payload.placement_id, payload.title, payload.file_id,
        payload.submission_notes, payload.requirement_id), db)
    return _submission(item)


@router.get("/me")
async def list_my_reports(account: CurrentAccount, db: DbSession):
    items = await _call(ReportService(db).list_mine(account.id), db)
    return {"items": [_submission(item) for item in items]}


@router.get("/requirements/me")
async def list_my_report_requirements(account: CurrentAccount, db: DbSession):
    items = await _call(ReportRequirementService(db).list_for_student(account.id), db)
    return {"items": [{"requirement": _requirement(item["requirement"]), "submission_status": item["submission_status"]} for item in items]}


@router.get("/{submission_id}")
async def get_report(submission_id: str, account: CurrentAccount, db: DbSession):
    item = await _call(ReportService(db).get(submission_id, account.id), db)
    return _submission(item)


@router.get("/{submission_id}/versions")
async def list_report_versions(submission_id: str, account: CurrentAccount, db: DbSession):
    items = await _call(ReportService(db).versions(submission_id, account.id), db)
    return {"items": [_version(item) for item in items]}


@router.patch("/{submission_id}")
async def rename_report(submission_id: str, payload: ReportTitleUpdate, account: CurrentAccount, db: DbSession):
    item = await _call(ReportService(db).rename_draft(submission_id, account.id, payload.title), db)
    return _submission(item)


@router.post("/{submission_id}/versions", status_code=201)
async def add_report_version(submission_id: str, payload: ReportVersionCreate, account: CurrentAccount, db: DbSession):
    item = await _call(ReportService(db).add_version(submission_id, account.id, payload.file_id, payload.submission_notes), db)
    return _version(item)


@router.post("/{submission_id}/submit")
async def submit_report(submission_id: str, account: CurrentAccount, db: DbSession):
    item = await _call(ReportService(db).submit(submission_id, account.id), db)
    return _submission(item)


@router.patch("/{submission_id}/status")
async def review_report(submission_id: str, payload: ReportReviewUpdate, account: CurrentAccount, db: DbSession):
    item = await _call(ReportService(db).review(submission_id, account.id, payload.status, payload.feedback_comments), db)
    return _submission(item)


@requirement_router.post("", status_code=201)
async def create_report_requirement(institution_id: str, payload: ReportRequirementCreate, account: CurrentAccount, db: DbSession):
    item = await _call(ReportRequirementService(db).create(institution_id, account.id, payload.title,
        payload.description, payload.due_date, payload.is_required), db)
    return _requirement(item)


@requirement_router.get("")
async def list_report_requirements(institution_id: str, account: CurrentAccount, db: DbSession):
    items = await _call(ReportRequirementService(db).list_for_institution(institution_id, account.id), db)
    return {"items": [_requirement(item) for item in items]}


@requirement_router.patch("/{requirement_id}/status")
async def set_report_requirement_active(institution_id: str, requirement_id: str, payload: ReportRequirementActiveUpdate,
                                        account: CurrentAccount, db: DbSession):
    item = await _call(ReportRequirementService(db).set_active(institution_id, account.id, requirement_id, payload.is_active), db)
    return _requirement(item)

@router.get("/faculty/me")
async def list_faculty_reports(account: CurrentAccount, db: DbSession):
    await require_role(db, account, "FACULTY")
    # Listing is restricted to placements explicitly assigned to this faculty account.
    from sqlalchemy import select
    from app.models.academic import FacultyProfile
    from app.models.internship import InternshipPlacement
    from app.models.evaluation import ReportSubmission
    faculty = await db.scalar(select(FacultyProfile).where(FacultyProfile.account_id == account.id))
    if faculty is None:
        raise HTTPException(status_code=403, detail="Faculty account required")
    rows = await db.execute(
        select(ReportSubmission)
        .join(InternshipPlacement, InternshipPlacement.id == ReportSubmission.placement_id)
        .where(InternshipPlacement.faculty_supervisor_id == faculty.id)
        .order_by(ReportSubmission.updated_at.desc())
    )
    return {"items": [_submission(item) for item in rows.scalars().all()]}
