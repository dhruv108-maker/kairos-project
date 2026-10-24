"""New modular internship API, mounted at /api/v1/modules/internships."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.dependencies import CurrentAccount, DbSession, account_roles, require_role
from app.models.internship import InternshipOpportunity, InternshipProvider
from app.modules.shared.exceptions import KairosDomainError
from app.modules.internships.schemas import ApplicationStatusUpdate, OpportunityCreate, PlacementCreate, ProviderCreate
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
