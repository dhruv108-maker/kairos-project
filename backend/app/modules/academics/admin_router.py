from fastapi import APIRouter, HTTPException, Query
from sqlalchemy.exc import IntegrityError

from app.api.dependencies import CurrentAccount, DbSession
from app.modules.academics.admin_schemas import CohortAssignment, FacultyUpdate, MentorshipCreate, VerificationUpdate
from app.modules.academics.admin_service import AcademicAdminError, AcademicAdminService
from app.modules.institutions.service import InstitutionAccessError
from app.modules.student_portfolio.service import StudentPortfolioService

router = APIRouter(prefix="/institutions/{institution_id}", tags=["student and faculty administration"])


async def _call(operation, db):
    try:
        return await operation
    except (AcademicAdminError, InstitutionAccessError) as exc:
        raise HTTPException(status_code=exc.status_code, detail=getattr(exc, "message", str(exc))) from None
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail="The operation conflicts with existing data") from None


def _student(row):
    student, account, cohort, programme, department, school = row
    return {
        "id": student.id, "account_id": account.id, "email": account.email,
        "full_name": account.full_name, "is_active": account.is_active,
        "is_verified": account.is_verified, "enrollment_number": student.enrollment_number,
        "current_semester": student.current_semester, "cgpa": str(student.cgpa) if student.cgpa is not None else None,
        "cohort": {"id": cohort.id, "name": cohort.name, "graduation_year": cohort.graduation_year},
        "programme": {"id": programme.id, "name": programme.name, "degree_level": programme.degree_level},
        "department": {"id": department.id, "name": department.name},
        "school": {"id": school.id, "name": school.name},
    }


def _faculty(row):
    faculty, account, department, school = row
    return {"id": faculty.id, "account_id": account.id, "email": account.email,
            "full_name": account.full_name, "is_active": account.is_active,
            "is_verified": account.is_verified, "employee_code": faculty.employee_code,
            "designation": faculty.designation, "department": {"id": department.id, "name": department.name},
            "school": {"id": school.id, "name": school.name}}


def _columns(item):
    return {column.name: getattr(item, column.name) for column in item.__table__.columns}


@router.get("/students")
async def list_students(institution_id: str, account: CurrentAccount, db: DbSession,
                        search: str | None = Query(default=None, max_length=100),
                        limit: int = Query(default=50, ge=1, le=100), offset: int = Query(default=0, ge=0)):
    rows = await _call(AcademicAdminService(db).list_students(institution_id, account.id, search, limit, offset), db)
    return {"items": [_student(row) for row in rows], "limit": limit, "offset": offset}


@router.get("/students/{student_id}")
async def get_student(institution_id: str, student_id: str, account: CurrentAccount, db: DbSession):
    row = await _call(AcademicAdminService(db).get_student(institution_id, account.id, student_id), db)
    summary = await StudentPortfolioService(db).summary(row[0], row[1])
    return {**_student(row), "portfolio_summary": summary}


@router.patch("/students/{student_id}/cohort")
async def assign_student_cohort(institution_id: str, student_id: str, payload: CohortAssignment,
                                account: CurrentAccount, db: DbSession):
    item = await _call(AcademicAdminService(db).change_student_cohort(
        institution_id, account.id, student_id, payload.cohort_id, payload.current_semester
    ), db)
    return {"id": item.id, "cohort_id": item.cohort_id, "current_semester": item.current_semester}


@router.patch("/students/{student_id}/academic-records/{record_id}/verification")
async def verify_academic_record(institution_id: str, student_id: str, record_id: str,
                                 payload: VerificationUpdate, account: CurrentAccount, db: DbSession):
    item = await _call(AcademicAdminService(db).verify_academic_record(
        institution_id, account.id, student_id, record_id, payload.is_verified
    ), db)
    return _columns(item)


@router.patch("/students/{student_id}/portfolio/{entry_id}/verification")
async def verify_portfolio_entry(institution_id: str, student_id: str, entry_id: str,
                                 payload: VerificationUpdate, account: CurrentAccount, db: DbSession):
    item = await _call(AcademicAdminService(db).verify_portfolio_entry(
        institution_id, account.id, student_id, entry_id, payload.is_verified
    ), db)
    return _columns(item)


@router.get("/faculty")
async def list_faculty(institution_id: str, account: CurrentAccount, db: DbSession,
                       search: str | None = Query(default=None, max_length=100),
                       limit: int = Query(default=50, ge=1, le=100), offset: int = Query(default=0, ge=0)):
    rows = await _call(AcademicAdminService(db).list_faculty(institution_id, account.id, search, limit, offset), db)
    return {"items": [_faculty(row) for row in rows], "limit": limit, "offset": offset}


@router.patch("/faculty/{faculty_id}")
async def update_faculty(institution_id: str, faculty_id: str, payload: FacultyUpdate,
                         account: CurrentAccount, db: DbSession):
    data = payload.model_dump(exclude_unset=True)
    item = await _call(AcademicAdminService(db).update_faculty(
        institution_id, account.id, faculty_id, data.get("department_id"),
        data.get("designation"), data.get("is_active")
    ), db)
    faculty_row = await _call(AcademicAdminService(db).list_faculty(institution_id, account.id, None, 100, 0), db)
    for row in faculty_row:
        if row[0].id == item.id:
            return _faculty(row)
    raise HTTPException(status_code=404, detail="Faculty member not found")


@router.post("/mentorships", status_code=201)
async def create_mentorship(institution_id: str, payload: MentorshipCreate,
                            account: CurrentAccount, db: DbSession):
    item = await _call(AcademicAdminService(db).create_mentorship(
        institution_id, account.id, payload.faculty_id, payload.student_id
    ), db)
    return _columns(item)


@router.get("/mentorships")
async def list_mentorships(institution_id: str, account: CurrentAccount, db: DbSession,
                           student_id: str | None = None, faculty_id: str | None = None):
    items = await _call(AcademicAdminService(db).list_mentorships(
        institution_id, account.id, student_id, faculty_id
    ), db)
    return {"items": [_columns(item) for item in items]}


@router.patch("/mentorships/{mentorship_id}/end")
async def end_mentorship(institution_id: str, mentorship_id: str, account: CurrentAccount, db: DbSession):
    item = await _call(AcademicAdminService(db).end_mentorship(institution_id, account.id, mentorship_id), db)
    return _columns(item)
