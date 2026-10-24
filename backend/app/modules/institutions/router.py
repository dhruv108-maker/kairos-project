import re
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.api.dependencies import CurrentAccount, DbSession, require_role
from app.modules.institutions.schemas import (
    AcademicYearCreate, AcademicYearUpdate, CohortCreate, CohortUpdate, DepartmentCreate, DepartmentUpdate, InstitutionCreate, InstitutionDomainCreate, InstitutionRegistrationCreate,
    InstitutionStatusUpdate, MembershipUpsert, ProgrammeCreate, ProgrammeUpdate, SchoolCreate, SchoolUpdate,
)
from app.modules.institutions.service import InstitutionAccessError, InstitutionService
from app.models.institutions import Institution
from app.models.institution_domains import InstitutionDomain
from app.models.academic import AcademicYear, Cohort, Department, Programme, School

router = APIRouter(prefix="/institutions", tags=["institutions", "academic administration"])


async def _call(operation, db):
    try:
        return await operation
    except InstitutionAccessError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from None
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail="The operation conflicts with existing data") from None


def _institution(item):
    return {key: getattr(item, key) for key in ("id", "name", "slug", "status", "contact_email", "website_url", "institution_type", "registration_number", "description", "address", "country", "state", "city", "postal_code", "created_by_account_id", "created_at", "updated_at")}


@router.get("/public")
async def public_institutions(db: DbSession, q: str | None = Query(default=None, max_length=120)):
    """Minimal public institution directory for registration fallback."""
    statement = select(Institution).where(func.upper(Institution.status) == "ACTIVE").order_by(Institution.name.asc()).limit(200)
    if q and q.strip():
        term = q.strip().replace("%", "\\%").replace("_", "\\_")
        statement = select(Institution).where(
            func.upper(Institution.status) == "ACTIVE",
            Institution.name.ilike(f"%{term}%", escape="\\"),
        ).order_by(Institution.name.asc()).limit(200)
    items = (await db.scalars(statement)).all()
    return {"items": [{"id": item.id, "name": item.name} for item in items]}


@router.get("/resolve")
async def resolve_institution_domain(
    db: DbSession,
    email_domain: str = Query(min_length=3, max_length=253),
):
    """Resolve only exact, verified domains; never infer from suffixes."""
    domain = email_domain.strip().lower().rstrip(".")
    if not re.fullmatch(r"(?=.{1,253}$)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}", domain):
        raise HTTPException(status_code=422, detail="Enter a valid email domain")
    rows = (await db.execute(
        select(Institution.id, Institution.name)
        .join(InstitutionDomain, InstitutionDomain.institution_id == Institution.id)
        .where(
            InstitutionDomain.normalized_domain == domain,
            InstitutionDomain.is_verified.is_(True),
            func.upper(Institution.status) == "ACTIVE",
        )
        .limit(2)
    )).all()
    if len(rows) == 1:
        return {"status": "matched", "institution": {"id": rows[0].id, "name": rows[0].name}}
    if len(rows) > 1:
        return {"status": "ambiguous", "institution": None}
    return {"status": "not_found", "institution": None}

@router.get("/public/{institution_id}/academic-options")
async def public_academic_options(institution_id: str, db: DbSession):
    """Expose only the active academic choices needed by public registration."""
    institution = await db.get(Institution, institution_id)
    if institution is None or (institution.status or "").upper() != "ACTIVE":
        raise HTTPException(status_code=404, detail="Active institution not found")
    departments = (await db.execute(
        select(Department.id, Department.name, Department.code)
        .join(School, School.id == Department.school_id)
        .where(School.institution_id == institution_id, School.is_active.is_(True), Department.is_active.is_(True))
        .order_by(Department.name.asc())
    )).all()
    cohorts = (await db.execute(
        select(Cohort.id, Cohort.name, Programme.name, Department.name, AcademicYear.year_label, Cohort.graduation_year)
        .join(Programme, Programme.id == Cohort.programme_id)
        .join(Department, Department.id == Programme.department_id)
        .join(School, School.id == Department.school_id)
        .join(AcademicYear, AcademicYear.id == Cohort.academic_year_id)
        .where(
            School.institution_id == institution_id,
            School.is_active.is_(True),
            Department.is_active.is_(True),
            Programme.is_active.is_(True),
            AcademicYear.is_current.is_(True),
            AcademicYear.institution_id == institution_id,
        )
        .order_by(Cohort.graduation_year.desc(), Cohort.name.asc())
    )).all()
    return {
        "departments": [{"id": row.id, "name": row.name, "code": row.code} for row in departments],
        "cohorts": [{"id": row[0], "name": row[1], "programme_name": row[2], "department_name": row[3], "academic_year": row[4], "graduation_year": row[5]} for row in cohorts],
    }

@router.get("/{institution_id}/domains")
async def list_institution_domains(institution_id: str, account: CurrentAccount, db: DbSession):
    await require_role(db, account, "PLATFORM_ADMIN")
    institution = await db.get(Institution, institution_id)
    if institution is None:
        raise HTTPException(status_code=404, detail="Institution not found")
    items = (await db.scalars(
        select(InstitutionDomain).where(InstitutionDomain.institution_id == institution_id).order_by(InstitutionDomain.normalized_domain.asc())
    )).all()
    return {"items": [{"id": item.id, "domain": item.normalized_domain, "verified": item.is_verified} for item in items]}


@router.post("/{institution_id}/domains", status_code=status.HTTP_201_CREATED)
async def register_institution_domain(institution_id: str, payload: InstitutionDomainCreate, account: CurrentAccount, db: DbSession):
    """Register a domain as verified only through an authenticated platform administrator."""
    await require_role(db, account, "PLATFORM_ADMIN")
    institution = await db.get(Institution, institution_id)
    if institution is None or (institution.status or "").upper() != "ACTIVE":
        raise HTTPException(status_code=404, detail="Active institution not found")
    existing = await db.scalar(select(InstitutionDomain.id).where(InstitutionDomain.normalized_domain == payload.domain))
    if existing is not None:
        raise HTTPException(status_code=409, detail="This domain is already registered")
    item = InstitutionDomain(id=str(uuid4()), institution_id=institution.id, normalized_domain=payload.domain, is_verified=True)
    db.add(item)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail="This domain is already registered") from None
    return {"id": item.id, "domain": item.normalized_domain, "verified": item.is_verified}


def _membership(item):
    return {key: getattr(item, key) for key in ("institution_id", "account_id", "role", "status", "invited_by_account_id", "created_at", "updated_at")}


def _school(item):
    return {"id": item.id, "institution_id": item.institution_id, "code": item.code, "name": item.name, "is_active": item.is_active}


def _department(item):
    return {"id": item.id, "school_id": item.school_id, "code": item.code, "name": item.name, "is_active": item.is_active}


def _programme(item):
    return {"id": item.id, "department_id": item.department_id, "code": item.code, "name": item.name, "degree_level": item.degree_level, "duration_years": item.duration_years, "is_active": item.is_active}


def _year(item):
    return {"id": item.id, "institution_id": item.institution_id, "year_label": item.year_label, "start_date": item.start_date, "end_date": item.end_date, "is_current": item.is_current}


def _cohort(item):
    return {"id": item.id, "programme_id": item.programme_id, "academic_year_id": item.academic_year_id, "name": item.name, "graduation_year": item.graduation_year}



@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register_institution(payload: InstitutionRegistrationCreate, account: CurrentAccount, db: DbSession):
    data = payload.model_dump()
    if data.get("website_url") is not None:
        data["website_url"] = str(data["website_url"])
    try:
        item = await InstitutionService(db).register_institution(account.id, data)
    except InstitutionAccessError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from None
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Institution slug or registration number is already registered") from None
    return {"institution": _institution(item), "next_step": "await_platform_review"}


@router.get("/{institution_id}/registration-status")
async def institution_registration_status(institution_id: str, account: CurrentAccount, db: DbSession):
    try:
        return await InstitutionService(db).registration_status(institution_id, account.id)
    except InstitutionAccessError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from None


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_institution(payload: InstitutionCreate, account: CurrentAccount, db: DbSession):
    data = payload.model_dump()
    if data.get("website_url") is not None:
        data["website_url"] = str(data["website_url"])
    return _institution(await _call(InstitutionService(db).create_institution(account.id, data), db))


@router.get("")
async def list_institutions(account: CurrentAccount, db: DbSession):
    items = await _call(InstitutionService(db).list_institutions(account.id), db)
    return {"items": [_institution(item) for item in items]}


@router.get("/{institution_id}")
async def get_institution(institution_id: str, account: CurrentAccount, db: DbSession):
    return _institution(await _call(InstitutionService(db).get_institution(institution_id, account.id), db))


@router.patch("/{institution_id}/status")
async def set_institution_status(institution_id: str, payload: InstitutionStatusUpdate, account: CurrentAccount, db: DbSession):
    return _institution(await _call(InstitutionService(db).set_status(institution_id, account.id, payload.status), db))


@router.put("/{institution_id}/members/{target_account_id}")
async def assign_member(institution_id: str, target_account_id: str, payload: MembershipUpsert, account: CurrentAccount, db: DbSession):
    if payload.account_id != target_account_id:
        raise HTTPException(status_code=422, detail="Path account_id and body account_id must match")
    item = await _call(InstitutionService(db).assign_member(institution_id, account.id, target_account_id, payload.role), db)
    return _membership(item)


@router.get("/{institution_id}/members")
async def list_members(institution_id: str, account: CurrentAccount, db: DbSession):
    items = await _call(InstitutionService(db).list_members(institution_id, account.id), db)
    return {"items": [_membership(item) for item in items]}


@router.delete("/{institution_id}/members/{target_account_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_member(institution_id: str, target_account_id: str, account: CurrentAccount, db: DbSession):
    await _call(InstitutionService(db).revoke_member(institution_id, account.id, target_account_id), db)
    return None


@router.post("/{institution_id}/schools", status_code=201)
async def create_school(institution_id: str, payload: SchoolCreate, account: CurrentAccount, db: DbSession):
    item = await _call(InstitutionService(db).create_school(institution_id, account.id, payload.code, payload.name), db)
    return _school(item)


@router.get("/{institution_id}/schools")
async def list_schools(institution_id: str, account: CurrentAccount, db: DbSession):
    items = await _call(InstitutionService(db).list_schools(institution_id, account.id), db)
    return {"items": [_school(item) for item in items]}


@router.post("/{institution_id}/departments", status_code=201)
async def create_department(institution_id: str, payload: DepartmentCreate, account: CurrentAccount, db: DbSession):
    item = await _call(InstitutionService(db).create_department(institution_id, account.id, payload.school_id, payload.code, payload.name), db)
    return _department(item)


@router.get("/{institution_id}/departments")
async def list_departments(institution_id: str, account: CurrentAccount, db: DbSession, school_id: str | None = Query(default=None)):
    items = await _call(InstitutionService(db).list_departments(institution_id, account.id, school_id), db)
    return {"items": [_department(item) for item in items]}


@router.post("/{institution_id}/programmes", status_code=201)
async def create_programme(institution_id: str, payload: ProgrammeCreate, account: CurrentAccount, db: DbSession):
    item = await _call(InstitutionService(db).create_programme(institution_id, account.id, payload.department_id, payload.code, payload.name, payload.degree_level, payload.duration_years), db)
    return _programme(item)


@router.get("/{institution_id}/programmes")
async def list_programmes(institution_id: str, account: CurrentAccount, db: DbSession, department_id: str | None = Query(default=None)):
    items = await _call(InstitutionService(db).list_programmes(institution_id, account.id, department_id), db)
    return {"items": [_programme(item) for item in items]}


@router.post("/{institution_id}/academic-years", status_code=201)
async def create_academic_year(institution_id: str, payload: AcademicYearCreate, account: CurrentAccount, db: DbSession):
    item = await _call(InstitutionService(db).create_academic_year(institution_id, account.id, payload.year_label, payload.start_date, payload.end_date, payload.is_current), db)
    return _year(item)


@router.get("/{institution_id}/academic-years")
async def list_academic_years(institution_id: str, account: CurrentAccount, db: DbSession):
    items = await _call(InstitutionService(db).list_academic_years(institution_id, account.id), db)
    return {"items": [_year(item) for item in items]}


@router.post("/{institution_id}/cohorts", status_code=201)
async def create_cohort(institution_id: str, payload: CohortCreate, account: CurrentAccount, db: DbSession):
    item = await _call(InstitutionService(db).create_cohort(institution_id, account.id, payload.programme_id, payload.academic_year_id, payload.name, payload.graduation_year), db)
    return _cohort(item)


@router.get("/{institution_id}/cohorts")
async def list_cohorts(institution_id: str, account: CurrentAccount, db: DbSession, programme_id: str | None = Query(default=None)):
    items = await _call(InstitutionService(db).list_cohorts(institution_id, account.id, programme_id), db)
    return {"items": [_cohort(item) for item in items]}


@router.patch("/{institution_id}/schools/{school_id}")
async def update_school(institution_id: str, school_id: str, payload: SchoolUpdate, account: CurrentAccount, db: DbSession):
    data = payload.model_dump(exclude_unset=True)
    item = await _call(InstitutionService(db).update_school(institution_id, account.id, school_id,
        data.get("code"), data.get("name"), data.get("is_active")), db)
    return _school(item)


@router.delete("/{institution_id}/schools/{school_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_school(institution_id: str, school_id: str, account: CurrentAccount, db: DbSession):
    await _call(InstitutionService(db).delete_school(institution_id, account.id, school_id), db)
    return None


@router.patch("/{institution_id}/departments/{department_id}")
async def update_department(institution_id: str, department_id: str, payload: DepartmentUpdate, account: CurrentAccount, db: DbSession):
    data = payload.model_dump(exclude_unset=True)
    item = await _call(InstitutionService(db).update_department(institution_id, account.id, department_id,
        data.get("code"), data.get("name"), data.get("is_active")), db)
    return _department(item)


@router.delete("/{institution_id}/departments/{department_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_department(institution_id: str, department_id: str, account: CurrentAccount, db: DbSession):
    await _call(InstitutionService(db).delete_department(institution_id, account.id, department_id), db)
    return None


@router.patch("/{institution_id}/programmes/{programme_id}")
async def update_programme(institution_id: str, programme_id: str, payload: ProgrammeUpdate, account: CurrentAccount, db: DbSession):
    data = payload.model_dump(exclude_unset=True)
    item = await _call(InstitutionService(db).update_programme(institution_id, account.id, programme_id,
        data.get("code"), data.get("name"), data.get("degree_level"), data.get("duration_years"), data.get("is_active")), db)
    return _programme(item)


@router.delete("/{institution_id}/programmes/{programme_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_programme(institution_id: str, programme_id: str, account: CurrentAccount, db: DbSession):
    await _call(InstitutionService(db).delete_programme(institution_id, account.id, programme_id), db)
    return None


@router.patch("/{institution_id}/academic-years/{year_id}")
async def update_academic_year(institution_id: str, year_id: str, payload: AcademicYearUpdate, account: CurrentAccount, db: DbSession):
    data = payload.model_dump(exclude_unset=True)
    item = await _call(InstitutionService(db).update_academic_year(institution_id, account.id, year_id,
        data.get("year_label"), data.get("start_date"), data.get("end_date"), data.get("is_current")), db)
    return _year(item)


@router.delete("/{institution_id}/academic-years/{year_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_academic_year(institution_id: str, year_id: str, account: CurrentAccount, db: DbSession):
    await _call(InstitutionService(db).delete_academic_year(institution_id, account.id, year_id), db)
    return None


@router.patch("/{institution_id}/cohorts/{cohort_id}")
async def update_cohort(institution_id: str, cohort_id: str, payload: CohortUpdate, account: CurrentAccount, db: DbSession):
    data = payload.model_dump(exclude_unset=True)
    item = await _call(InstitutionService(db).update_cohort(institution_id, account.id, cohort_id,
        data.get("name"), data.get("graduation_year"), data.get("programme_id"), data.get("academic_year_id")), db)
    return _cohort(item)


@router.delete("/{institution_id}/cohorts/{cohort_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_cohort(institution_id: str, cohort_id: str, account: CurrentAccount, db: DbSession):
    await _call(InstitutionService(db).delete_cohort(institution_id, account.id, cohort_id), db)
    return None
