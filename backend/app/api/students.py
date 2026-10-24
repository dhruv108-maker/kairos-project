from __future__ import annotations

from datetime import date
from typing import Any
from urllib.parse import urlsplit
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.api.auth import _account_public
from app.api.dependencies import CurrentAccount, DbSession, require_role
from app.api.schemas import ProfileUpdate, StudentProfileResponse
from app.models.academic import AcademicYear, Cohort, Department, Programme, School, StudentProfile
from app.models.portfolio import StudentAcademicRecord, StudentPortfolioEntry, StudentResume
from app.models.internship import InternshipApplication, InternshipOpportunity, InternshipPlacement, InternshipProvider
from app.models.storage import StorageFile
from app.modules.academics.service import AcademicService
from app.modules.shared.exceptions import KairosDomainError
from app.modules.student_portfolio.service import StudentPortfolioService

router = APIRouter(prefix="/students", tags=["students"])

COLLECTION_KIND = {
    "skills": "skill", "projects": "project", "certifications": "certification",
    "experience": "experience", "research": "research", "awards": "award",
    "achievements": "achievement", "activities": "activity",
}
ENTRY_FIELDS = {
    "title", "description", "organization", "url", "credential_id",
    "proficiency", "start_date", "end_date", "issued_date",
}
ACADEMIC_FIELDS = {
    "institution_name", "qualification", "field_of_study", "start_date",
    "end_date", "semester", "grade_value", "grade_max", "grading_scale", "description",
}


class PortfolioPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=10000)
    organization: str | None = Field(default=None, max_length=255)
    url: str | None = Field(default=None, max_length=2048)
    credential_id: str | None = Field(default=None, max_length=255)
    proficiency: str | None = Field(default=None, max_length=64)
    start_date: date | None = None
    end_date: date | None = None
    issued_date: date | None = None

    @field_validator("title")
    @classmethod
    def validate_title(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("title cannot be blank")
        return value

    @field_validator("url")
    @classmethod
    def validate_http_url(cls, value: str | None) -> str | None:
        if value is None:
            return None
        parsed = urlsplit(value)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("url must be an absolute HTTP or HTTPS URL")
        return value

    @model_validator(mode="after")
    def validate_dates(self):
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValueError("end_date cannot precede start_date")
        return self


class AcademicPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    institution_name: str = Field(min_length=1, max_length=255)
    qualification: str = Field(min_length=1, max_length=255)
    field_of_study: str | None = Field(default=None, max_length=255)
    start_date: date | None = None
    end_date: date | None = None
    semester: str | None = Field(default=None, max_length=32)
    grade_value: float | None = Field(default=None, ge=0)
    grade_max: float | None = Field(default=None, gt=0)
    grading_scale: str | None = Field(default=None, max_length=100)
    description: str | None = Field(default=None, max_length=10000)

    @field_validator("institution_name", "qualification")
    @classmethod
    def validate_required_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("value cannot be blank")
        return value

    @model_validator(mode="after")
    def validate_record(self):
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValueError("end_date cannot precede start_date")
        if self.grade_value is not None and self.grade_max is not None and self.grade_value > self.grade_max:
            raise ValueError("grade_value cannot exceed grade_max")
        return self


class ResumePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    storage_file_id: str = Field(min_length=1, max_length=36)
    label: str = Field(min_length=1, max_length=255)
    is_primary: bool = False


async def _commit_or_conflict(db: Any, detail: str = "Request conflicts with existing data") -> None:
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail=detail) from None


async def _student(account: Any, db: Any) -> StudentProfile:
    await require_role(db, account, "STUDENT")
    profile = await AcademicService(db).student_profile_for_account(account.id)
    if profile is None:
        raise HTTPException(status_code=404, detail="Student profile not found")
    return profile


async def _service_call(operation):
    try:
        return await operation
    except KairosDomainError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from None


def _row(row: Any, exclude: set[str] | None = None) -> dict[str, Any]:
    excluded = exclude or set()
    return {column.name: getattr(row, column.name) for column in row.__table__.columns if column.name not in excluded}


@router.get("/me", response_model=StudentProfileResponse)
async def get_my_student_profile(account: CurrentAccount, db: DbSession) -> StudentProfileResponse:
    profile = await _student(account, db)
    department = await db.get(Department, profile.department_id) if profile.department_id else None
    return StudentProfileResponse(
        account=await _account_public(db, account),
        student={"id": profile.id, "enrollment_number": profile.enrollment_number,
                 "school_id": department.school_id if department else None,
                 "department_id": profile.department_id, "programme_id": profile.programme_id, "cohort_id": profile.cohort_id,
                 "current_semester": profile.current_semester,
                 "cgpa": str(profile.cgpa) if profile.cgpa is not None else None},
    )


@router.patch("/me", response_model=StudentProfileResponse)
async def update_my_student_profile(payload: ProfileUpdate, account: CurrentAccount, db: DbSession) -> StudentProfileResponse:
    await _student(account, db)
    changes = payload.model_dump(exclude_unset=True)
    if not changes:
        raise HTTPException(status_code=422, detail="No profile fields supplied")
    for key, value in changes.items():
        setattr(account, key, value)
    await _commit_or_conflict(db)
    await db.refresh(account)
    return await get_my_student_profile(account, db)


@router.get("/me/enrollments")
async def get_my_enrollment_context(account: CurrentAccount, db: DbSession) -> dict[str, Any]:
    await _student(account, db)
    context = await AcademicService(db).enrollment_context(account.id)
    if context is None:
        raise HTTPException(status_code=404, detail="Student academic context not found")
    return context

@router.get("/me/completeness")
async def profile_completeness(account: CurrentAccount, db: DbSession) -> dict[str, Any]:
    profile = await _student(account, db)
    return await StudentPortfolioService(db).completeness(profile, account)

@router.get("/me/summary")
async def profile_summary(account: CurrentAccount, db: DbSession) -> dict[str, Any]:
    profile = await _student(account, db)
    return await StudentPortfolioService(db).summary(profile, account)

@router.get("/me/academics")
@router.get("/me/academic-records")
async def list_academic_records(account: CurrentAccount, db: DbSession, limit: int = Query(50, ge=1, le=100), offset: int = Query(0, ge=0)) -> dict[str, Any]:
    profile = await _student(account, db)
    rows = await StudentPortfolioService(db).list_academic_records(profile.id, limit, offset)
    return {"items": [_row(row) for row in rows], "limit": limit, "offset": offset}

@router.post("/me/academic-records", status_code=201)
async def create_academic_record(payload: AcademicPayload, account: CurrentAccount, db: DbSession) -> dict[str, Any]:
    profile = await _student(account, db)
    row = await _service_call(StudentPortfolioService(db).create_academic_record(profile.id, payload.model_dump()))
    return _row(row)

@router.get("/me/academic-records/{record_id}")
async def get_academic_record(record_id: str, account: CurrentAccount, db: DbSession) -> dict[str, Any]:
    profile = await _student(account, db)
    row = await _service_call(StudentPortfolioService(db).get_academic_record(profile.id, record_id))
    return _row(row)

@router.patch("/me/academic-records/{record_id}")
async def update_academic_record(record_id: str, payload: dict[str, Any], account: CurrentAccount, db: DbSession) -> dict[str, Any]:
    profile = await _student(account, db)
    if not payload or set(payload) - ACADEMIC_FIELDS:
        raise HTTPException(status_code=422, detail="Invalid or empty academic record update")
    current = await _service_call(StudentPortfolioService(db).get_academic_record(profile.id, record_id))
    try:
        validated = AcademicPayload.model_validate({key: value for key, value in {**_row(current), **payload}.items() if key in ACADEMIC_FIELDS})
    except ValidationError:
        raise HTTPException(status_code=422, detail="Invalid request fields") from None
    row = await _service_call(StudentPortfolioService(db).update_academic_record(profile.id, record_id, validated.model_dump()))
    return _row(row)

@router.delete("/me/academic-records/{record_id}", status_code=204)
async def delete_academic_record(record_id: str, account: CurrentAccount, db: DbSession) -> None:
    profile = await _student(account, db)
    await _service_call(StudentPortfolioService(db).delete_academic_record(profile.id, record_id))

@router.get("/me/cv")
async def get_cv(account: CurrentAccount, db: DbSession) -> dict[str, Any]:
    profile = await _student(account, db)
    return await StudentPortfolioService(db).cv(profile, account)

@router.patch("/me/cv")
async def patch_cv(account: CurrentAccount, db: DbSession, payload: dict[str, Any]) -> dict[str, Any]:
    await _student(account, db)
    allowed = {"full_name", "phone_number"}
    if not payload or set(payload) - allowed:
        raise HTTPException(status_code=422, detail="CV profile updates may only include full_name and phone_number")
    try:
        validated = ProfileUpdate.model_validate(payload)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail="Invalid request fields") from None
    for key, value in validated.model_dump(exclude_unset=True).items():
        setattr(account, key, value)
    await _commit_or_conflict(db)
    await db.refresh(account)
    return await get_cv(account, db)


@router.post("/me/cv/preview")
async def cv_preview(account: CurrentAccount, db: DbSession, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    cv = await get_cv(account, db)
    if payload:
        allowed = {"full_name", "phone_number"}
        if set(payload) - allowed:
            raise HTTPException(status_code=422, detail="Only full_name and phone_number preview overrides are supported")
        cv["profile"].update(payload)
    return {"preview": cv, "persisted": False}


@router.get("/me/cv/completeness")
async def cv_completeness(account: CurrentAccount, db: DbSession) -> dict[str, Any]:
    return await profile_completeness(account, db)


@router.get("/me/resumes")
async def list_resumes(account: CurrentAccount, db: DbSession) -> dict[str, Any]:
    profile = await _student(account, db)
    rows = await StudentPortfolioService(db).list_resumes(profile.id)
    return {"items": [_row(row, {"student_profile_id"}) for row in rows]}

@router.post("/me/resumes", status_code=201)
async def create_resume(payload: ResumePayload, account: CurrentAccount, db: DbSession) -> dict[str, Any]:
    profile = await _student(account, db)
    row = await _service_call(StudentPortfolioService(db).create_resume(profile.id, account.id, payload.model_dump()))
    return _row(row, {"student_profile_id"})

@router.get("/me/resumes/{resume_id}")
async def get_resume(resume_id: str, account: CurrentAccount, db: DbSession) -> dict[str, Any]:
    profile = await _student(account, db)
    row = await _service_call(StudentPortfolioService(db).get_resume(profile.id, resume_id))
    return _row(row, {"student_profile_id"})

@router.delete("/me/resumes/{resume_id}", status_code=204)
async def delete_resume(resume_id: str, account: CurrentAccount, db: DbSession) -> None:
    profile = await _student(account, db)
    await _service_call(StudentPortfolioService(db).delete_resume(profile.id, resume_id))

@router.get("/me/internships")
async def internship_history(account: CurrentAccount, db: DbSession) -> dict[str, Any]:
    profile = await _student(account, db)
    rows = (await db.execute(
        select(InternshipPlacement, InternshipOpportunity.title, InternshipProvider.company_name)
        .join(InternshipApplication, InternshipApplication.id == InternshipPlacement.application_id)
        .join(InternshipOpportunity, InternshipOpportunity.id == InternshipApplication.opportunity_id)
        .join(InternshipProvider, InternshipProvider.id == InternshipOpportunity.provider_id)
        .where(InternshipPlacement.student_id == profile.id)
        .order_by(InternshipPlacement.start_date.desc())
    )).all()
    return {"items": [
        {"id": placement.id, "title": title, "organization": company, "start_date": placement.start_date,
         "end_date": placement.end_date, "status": placement.status}
        for placement, title, company in rows
    ]}


@router.get("/me/timeline")
async def timeline(account: CurrentAccount, db: DbSession, limit: int = Query(100, ge=1, le=200)) -> dict[str, Any]:
    profile = await _student(account, db)
    return await StudentPortfolioService(db).timeline(profile, limit)

@router.get("/me/{collection}")
async def list_portfolio_collection(collection: str, account: CurrentAccount, db: DbSession, limit: int = Query(50, ge=1, le=100), offset: int = Query(0, ge=0)) -> dict[str, Any]:
    if collection not in COLLECTION_KIND:
        raise HTTPException(status_code=404, detail="Portfolio collection not found")
    profile = await _student(account, db)
    rows = await StudentPortfolioService(db).list_entries(profile.id, COLLECTION_KIND[collection], limit, offset)
    return {"items": [_row(row, {"student_profile_id", "kind", "verified_by_account_id"}) for row in rows], "limit": limit, "offset": offset}

@router.post("/me/{collection}", status_code=201)
async def create_portfolio_entry(collection: str, payload: PortfolioPayload, account: CurrentAccount, db: DbSession) -> dict[str, Any]:
    if collection not in COLLECTION_KIND:
        raise HTTPException(status_code=404, detail="Portfolio collection not found")
    profile = await _student(account, db)
    row = await _service_call(StudentPortfolioService(db).create_entry(profile.id, COLLECTION_KIND[collection], payload.model_dump()))
    return _row(row, {"student_profile_id", "kind", "verified_by_account_id"})

@router.get("/me/{collection}/{record_id}")
async def get_portfolio_entry(collection: str, record_id: str, account: CurrentAccount, db: DbSession) -> dict[str, Any]:
    if collection not in COLLECTION_KIND:
        raise HTTPException(status_code=404, detail="Portfolio collection not found")
    profile = await _student(account, db)
    row = await _service_call(StudentPortfolioService(db).get_entry(profile.id, COLLECTION_KIND[collection], record_id))
    return _row(row, {"student_profile_id", "kind", "verified_by_account_id"})

@router.patch("/me/{collection}/{record_id}")
async def update_portfolio_entry(collection: str, record_id: str, payload: dict[str, Any], account: CurrentAccount, db: DbSession) -> dict[str, Any]:
    if collection not in COLLECTION_KIND:
        raise HTTPException(status_code=404, detail="Portfolio collection not found")
    if not payload or set(payload) - ENTRY_FIELDS:
        raise HTTPException(status_code=422, detail="Invalid or empty portfolio update")
    profile = await _student(account, db)
    current = await _service_call(StudentPortfolioService(db).get_entry(profile.id, COLLECTION_KIND[collection], record_id))
    try:
        validated = PortfolioPayload.model_validate({key: value for key, value in {**_row(current), **payload}.items() if key in ENTRY_FIELDS})
    except ValidationError:
        raise HTTPException(status_code=422, detail="Invalid request fields") from None
    row = await _service_call(StudentPortfolioService(db).update_entry(profile.id, COLLECTION_KIND[collection], record_id, validated.model_dump()))
    return _row(row, {"student_profile_id", "kind", "verified_by_account_id"})

@router.delete("/me/{collection}/{record_id}", status_code=204)
async def delete_portfolio_entry(collection: str, record_id: str, account: CurrentAccount, db: DbSession) -> None:
    if collection not in COLLECTION_KIND:
        raise HTTPException(status_code=404, detail="Portfolio collection not found")
    profile = await _student(account, db)
    await _service_call(StudentPortfolioService(db).delete_entry(profile.id, COLLECTION_KIND[collection], record_id))

