from __future__ import annotations

from datetime import date
from decimal import Decimal
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.api.dependencies import CurrentAccount, DbSession, require_role
from app.models.academic import FacultyProfile, StudentProfile
from app.modules.shared.exceptions import KairosDomainError
from app.modules.internships.repository import InternshipRepository
from app.modules.internships.service import InternshipService, APPLICATION_TRANSITIONS as SERVICE_APPLICATION_TRANSITIONS
from app.models.internship import (
    InternshipApplication,
    InternshipOpportunity,
    InternshipPlacement,
    InternshipProvider,
)

router = APIRouter(prefix="/internships", tags=["internships"])

ADMIN_ROLES = ("SYSTEM_ADMIN", "DEAN", "DEPT_HEAD")
OPPORTUNITY_MANAGER_ROLES = (*ADMIN_ROLES, "FACULTY")
# The modular service is the canonical state machine for both API surfaces.
APPLICATION_TRANSITIONS = {state: set(targets) for state, targets in SERVICE_APPLICATION_TRANSITIONS.items()}


class ProviderCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    company_name: str = Field(min_length=1, max_length=255)
    website: str | None = Field(default=None, max_length=255)
    industry_sector: str | None = Field(default=None, max_length=100)
    contact_person_name: str | None = Field(default=None, max_length=150)
    contact_email: str | None = Field(default=None, max_length=255)

    @field_validator("company_name")
    @classmethod
    def clean_company_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Company name cannot be blank")
        return value


class OpportunityCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    provider_id: str = Field(min_length=1, max_length=36)
    title: str = Field(min_length=1, max_length=255)
    description: str = Field(min_length=1)
    location: str = Field(min_length=1, max_length=150)
    stipend_amount: Decimal = Field(default=Decimal("0.00"), ge=0, max_digits=10, decimal_places=2)
    application_deadline: date

    @field_validator("title", "description", "location")
    @classmethod
    def trim_required_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("This field cannot be blank")
        return value


class ApplicationStatusUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: str

    @field_validator("status")
    @classmethod
    def valid_status(cls, value: str) -> str:
        value = value.strip().upper()
        if value not in {"SHORTLISTED", "OFFERED", "REJECTED"}:
            raise ValueError("Status must be SHORTLISTED, OFFERED, or REJECTED")
        return value


class PlacementCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    start_date: date
    end_date: date
    faculty_supervisor_id: str | None = Field(default=None, max_length=36)

    @field_validator("end_date")
    @classmethod
    def validate_dates(cls, value: date, info) -> date:
        start = info.data.get("start_date")
        if start is not None and value < start:
            raise ValueError("end_date must be on or after start_date")
        return value


async def _service_call(operation, conflict_message: str = "Request conflicts with existing data"):
    try:
        return await operation
    except KairosDomainError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from None
    except IntegrityError:
        raise HTTPException(status_code=409, detail=conflict_message) from None


def _opportunity_json(opportunity: InternshipOpportunity, provider: InternshipProvider | None = None) -> dict:
    return {
        "id": opportunity.id,
        "provider_id": opportunity.provider_id,
        "company_name": provider.company_name if provider else None,
        "title": opportunity.title,
        "description": opportunity.description,
        "location": opportunity.location,
        "stipend_amount": str(opportunity.stipend_amount),
        "application_deadline": opportunity.application_deadline.isoformat(),
        "is_active": opportunity.is_active,
        "created_at": opportunity.created_at.isoformat() if opportunity.created_at else None,
    }


async def _require_any_role(db: DbSession, account: CurrentAccount, roles: tuple[str, ...]) -> None:
    for role in roles:
        try:
            await require_role(db, account, role)
            return
        except HTTPException as exc:
            if exc.status_code != 403:
                raise
    raise HTTPException(status_code=403, detail="Insufficient role")


@router.get("/opportunities")
async def list_opportunities(
    account: CurrentAccount,
    db: DbSession,
    q: str | None = Query(default=None, max_length=100),
    location: str | None = Query(default=None, max_length=150),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> dict:
    rows = await InternshipRepository(db).list_active_opportunities(
        query=q, location=location, limit=limit, offset=offset
    )
    return {"items": [_opportunity_json(item, provider) for item, provider in rows],
            "limit": limit, "offset": offset}

@router.get("/opportunities/{opportunity_id}")
async def get_opportunity(opportunity_id: str, account: CurrentAccount, db: DbSession) -> dict:
    row = (
        await db.execute(
            select(InternshipOpportunity, InternshipProvider)
            .join(InternshipProvider, InternshipProvider.id == InternshipOpportunity.provider_id)
            .where(InternshipOpportunity.id == opportunity_id)
        )
    ).first()
    if row is None or (not row[0].is_active and account.is_active):
        raise HTTPException(status_code=404, detail="Internship opportunity not found")
    return _opportunity_json(row[0], row[1])


@router.post("/providers", status_code=status.HTTP_201_CREATED)
async def create_provider(payload: ProviderCreate, account: CurrentAccount, db: DbSession) -> dict:
    await _require_any_role(db, account, ADMIN_ROLES)
    provider = await _service_call(InternshipService(db).create_provider(payload.model_dump()))
    return {
        "id": provider.id,
        "company_name": provider.company_name,
        "website": provider.website,
        "industry_sector": provider.industry_sector,
        "contact_person_name": provider.contact_person_name,
        "contact_email": provider.contact_email,
        "created_at": provider.created_at.isoformat() if provider.created_at else None,
    }

@router.post("/opportunities", status_code=status.HTTP_201_CREATED)
async def create_opportunity(payload: OpportunityCreate, account: CurrentAccount, db: DbSession) -> dict:
    await _require_any_role(db, account, OPPORTUNITY_MANAGER_ROLES)
    opportunity, provider = await _service_call(InternshipService(db).create_opportunity(payload.model_dump()))
    return _opportunity_json(opportunity, provider)

@router.post("/opportunities/{opportunity_id}/applications", status_code=status.HTTP_201_CREATED)
async def apply_to_opportunity(opportunity_id: str, account: CurrentAccount, db: DbSession) -> dict:
    await require_role(db, account, "STUDENT")
    application = await _service_call(InternshipService(db).apply(account.id, opportunity_id))
    return {
        "id": application.id,
        "opportunity_id": application.opportunity_id,
        "student_id": application.student_id,
        "status": application.status,
        "applied_at": application.applied_at.isoformat() if application.applied_at else None,
    }

@router.get("/applications/me")
async def list_my_applications(account: CurrentAccount, db: DbSession) -> dict:
    await require_role(db, account, "STUDENT")
    repository = InternshipRepository(db)
    student = await repository.get_student_by_account(account.id)
    if student is None:
        raise HTTPException(status_code=404, detail="Student profile not found")
    rows = await repository.list_applications_for_student(student.id)
    return {
        "items": [
            {
                "id": application.id,
                "status": application.status,
                "applied_at": application.applied_at.isoformat() if application.applied_at else None,
                "opportunity": _opportunity_json(opportunity, provider),
            }
            for application, opportunity, provider in rows
        ]
    }

@router.post("/applications/{application_id}/withdraw")
async def withdraw_application(application_id: str, account: CurrentAccount, db: DbSession) -> dict:
    await require_role(db, account, "STUDENT")
    application = await _service_call(InternshipService(db).withdraw(account.id, application_id))
    return {"id": application.id, "status": application.status}

@router.patch("/applications/{application_id}/status")
async def update_application_status(
    application_id: str, payload: ApplicationStatusUpdate, account: CurrentAccount, db: DbSession
) -> dict:
    await _require_any_role(db, account, OPPORTUNITY_MANAGER_ROLES)
    application = await _service_call(InternshipService(db).transition_application(application_id, payload.status))
    return {"id": application.id, "status": application.status}

@router.post("/applications/{application_id}/placement", status_code=status.HTTP_201_CREATED)
async def create_placement(
    application_id: str, payload: PlacementCreate, account: CurrentAccount, db: DbSession
) -> dict:
    await _require_any_role(db, account, OPPORTUNITY_MANAGER_ROLES)
    placement = await _service_call(InternshipService(db).create_placement(application_id, payload.model_dump()))
    return {
        "id": placement.id,
        "application_id": placement.application_id,
        "student_id": placement.student_id,
        "faculty_supervisor_id": placement.faculty_supervisor_id,
        "start_date": placement.start_date.isoformat(),
        "end_date": placement.end_date.isoformat(),
        "status": placement.status,
    }

