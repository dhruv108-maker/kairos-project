"""Institution-authorized student/faculty administration and mentorship workflows."""
from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.academic import Account, AcademicYear, Cohort, Department, FacultyProfile, Programme, School, StudentProfile
from app.models.institutions import InstitutionMembership
from app.models.mentorship import FacultyStudentMentorship
from app.modules.audit.service import AuditService
from app.models.portfolio import StudentAcademicRecord, StudentPortfolioEntry
from app.modules.institutions.service import InstitutionAccessError, InstitutionService


class AcademicAdminError(Exception):
    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        self.message = message
        super().__init__(message)


class AcademicAdminService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.institutions = InstitutionService(db)

    def _student_scope(self, institution_id: str):
        return select(StudentProfile).join(Cohort, Cohort.id == StudentProfile.cohort_id).join(
            Programme, Programme.id == Cohort.programme_id
        ).join(Department, Department.id == Programme.department_id).join(
            School, School.id == Department.school_id
        ).where(School.institution_id == institution_id)

    def _faculty_scope(self, institution_id: str):
        return select(FacultyProfile).join(Department, Department.id == FacultyProfile.department_id).join(
            School, School.id == Department.school_id
        ).where(School.institution_id == institution_id)

    async def list_students(self, institution_id: str, actor_id: str, search: str | None, limit: int, offset: int):
        await self.institutions.require_admin(institution_id, actor_id)
        query = select(StudentProfile, Account, Cohort, Programme, Department, School).join(
            Account, Account.id == StudentProfile.account_id
        ).join(Cohort, Cohort.id == StudentProfile.cohort_id).join(
            Programme, Programme.id == Cohort.programme_id
        ).join(Department, Department.id == Programme.department_id).join(
            School, School.id == Department.school_id
        ).where(School.institution_id == institution_id)
        if search:
            term = "%" + search.strip() + "%"
            query = query.where(or_(Account.full_name.ilike(term), Account.email.ilike(term), StudentProfile.enrollment_number.ilike(term)))
        result = await self.db.execute(query.order_by(Account.full_name).limit(limit).offset(offset))
        return list(result.all())

    async def get_student(self, institution_id: str, actor_id: str, student_id: str):
        await self.institutions.require_admin(institution_id, actor_id)
        query = select(StudentProfile, Account, Cohort, Programme, Department, School).join(
            Account, Account.id == StudentProfile.account_id
        ).join(Cohort, Cohort.id == StudentProfile.cohort_id).join(
            Programme, Programme.id == Cohort.programme_id
        ).join(Department, Department.id == Programme.department_id).join(
            School, School.id == Department.school_id
        ).where(School.institution_id == institution_id, StudentProfile.id == student_id)
        row = (await self.db.execute(query)).first()
        if row is None:
            raise AcademicAdminError(404, "Student not found in this institution")
        return row

    async def change_student_cohort(self, institution_id: str, actor_id: str, student_id: str, cohort_id: str, current_semester: int | None):
        await self.institutions.require_admin(institution_id, actor_id)
        await self.get_student(institution_id, actor_id, student_id)
        query = select(Cohort).join(Programme, Programme.id == Cohort.programme_id).join(
            Department, Department.id == Programme.department_id
        ).join(School, School.id == Department.school_id).where(
            Cohort.id == cohort_id, School.institution_id == institution_id
        )
        cohort = await self.db.scalar(query)
        if cohort is None:
            raise AcademicAdminError(422, "Target cohort must belong to this institution")
        student = await self.db.get(StudentProfile, student_id)
        student.cohort_id = cohort_id
        if current_semester is not None:
            student.current_semester = current_semester
        AuditService(self.db).record(actor_id, institution_id, "student.cohort_changed", "student_profile", student.id, {"cohort_id": cohort_id, "current_semester": student.current_semester})
        await self.db.commit()
        await self.db.refresh(student)
        return student

    async def verify_academic_record(self, institution_id: str, actor_id: str, student_id: str, record_id: str, is_verified: bool):
        await self.institutions.require_admin(institution_id, actor_id)
        await self.get_student(institution_id, actor_id, student_id)
        item = await self.db.scalar(select(StudentAcademicRecord).where(
            StudentAcademicRecord.id == record_id, StudentAcademicRecord.student_profile_id == student_id
        ))
        if item is None:
            raise AcademicAdminError(404, "Academic record not found for this student")
        item.is_verified = is_verified
        item.verified_by_account_id = actor_id if is_verified else None
        item.verified_at = datetime.now(UTC).replace(tzinfo=None) if is_verified else None
        AuditService(self.db).record(actor_id, institution_id, "student.academic_record_verification_changed", "student_academic_record", item.id, {"is_verified": is_verified, "student_profile_id": student_id})
        await self.db.commit()
        await self.db.refresh(item)
        return item

    async def verify_portfolio_entry(self, institution_id: str, actor_id: str, student_id: str, entry_id: str, is_verified: bool):
        await self.institutions.require_admin(institution_id, actor_id)
        await self.get_student(institution_id, actor_id, student_id)
        item = await self.db.scalar(select(StudentPortfolioEntry).where(
            StudentPortfolioEntry.id == entry_id, StudentPortfolioEntry.student_profile_id == student_id
        ))
        if item is None:
            raise AcademicAdminError(404, "Portfolio entry not found for this student")
        item.is_verified = is_verified
        item.verified_by_account_id = actor_id if is_verified else None
        item.verified_at = datetime.now(UTC).replace(tzinfo=None) if is_verified else None
        AuditService(self.db).record(actor_id, institution_id, "student.portfolio_verification_changed", "student_portfolio_entry", item.id, {"is_verified": is_verified, "student_profile_id": student_id})
        await self.db.commit()
        await self.db.refresh(item)
        return item

    async def list_faculty(self, institution_id: str, actor_id: str, search: str | None, limit: int, offset: int):
        await self.institutions.require_admin(institution_id, actor_id)
        query = select(FacultyProfile, Account, Department, School).join(
            Account, Account.id == FacultyProfile.account_id
        ).join(Department, Department.id == FacultyProfile.department_id).join(
            School, School.id == Department.school_id
        ).where(School.institution_id == institution_id)
        if search:
            term = "%" + search.strip() + "%"
            query = query.where(or_(Account.full_name.ilike(term), Account.email.ilike(term), FacultyProfile.employee_code.ilike(term)))
        result = await self.db.execute(query.order_by(Account.full_name).limit(limit).offset(offset))
        return list(result.all())

    async def update_faculty(self, institution_id: str, actor_id: str, faculty_id: str, department_id: str | None, designation: str | None, is_active: bool | None):
        await self.institutions.require_admin(institution_id, actor_id)
        faculty = await self.db.scalar(self._faculty_scope(institution_id).where(FacultyProfile.id == faculty_id))
        if faculty is None:
            raise AcademicAdminError(404, "Faculty member not found in this institution")
        if department_id is not None:
            department = await self.db.scalar(select(Department).join(School, School.id == Department.school_id).where(
                Department.id == department_id, School.institution_id == institution_id
            ))
            if department is None:
                raise AcademicAdminError(422, "Department must belong to this institution")
            faculty.department_id = department_id
        if designation is not None:
            faculty.designation = designation.strip()
        if is_active is not None:
            account = await self.db.get(Account, faculty.account_id)
            account.is_active = is_active
        AuditService(self.db).record(actor_id, institution_id, "faculty.profile_updated", "faculty_profile", faculty.id, {"department_id": faculty.department_id, "designation": faculty.designation, "is_active": is_active})
        await self.db.commit()
        await self.db.refresh(faculty)
        return faculty

    async def create_mentorship(self, institution_id: str, actor_id: str, faculty_id: str, student_id: str):
        await self.institutions.require_admin(institution_id, actor_id)
        faculty = await self.db.scalar(self._faculty_scope(institution_id).where(FacultyProfile.id == faculty_id))
        student = await self.db.scalar(self._student_scope(institution_id).where(StudentProfile.id == student_id))
        if faculty is None or student is None:
            raise AcademicAdminError(422, "Faculty and student must both belong to this institution")
        active = await self.db.scalar(select(FacultyStudentMentorship.id).where(
            FacultyStudentMentorship.institution_id == institution_id,
            FacultyStudentMentorship.student_profile_id == student_id,
            FacultyStudentMentorship.status == "ACTIVE",
        ))
        if active is not None:
            raise AcademicAdminError(409, "Student already has an active faculty mentor")
        item = await self.db.scalar(select(FacultyStudentMentorship).where(
            FacultyStudentMentorship.institution_id == institution_id,
            FacultyStudentMentorship.faculty_profile_id == faculty_id,
            FacultyStudentMentorship.student_profile_id == student_id,
        ))
        if item is None:
            item = FacultyStudentMentorship(id=str(uuid4()), institution_id=institution_id,
                faculty_profile_id=faculty_id, student_profile_id=student_id,
                assigned_by_account_id=actor_id, status="ACTIVE")
            self.db.add(item)
        else:
            item.status = "ACTIVE"
            item.assigned_by_account_id = actor_id
        AuditService(self.db).record(actor_id, institution_id, "faculty.mentorship_assigned", "faculty_student_mentorship", item.id, {"faculty_profile_id": faculty_id, "student_profile_id": student_id})
        await self.db.commit()
        await self.db.refresh(item)
        return item

    async def end_mentorship(self, institution_id: str, actor_id: str, mentorship_id: str):
        await self.institutions.require_admin(institution_id, actor_id)
        item = await self.db.get(FacultyStudentMentorship, mentorship_id)
        if item is None or item.institution_id != institution_id:
            raise AcademicAdminError(404, "Mentorship not found in this institution")
        item.status = "ENDED"
        AuditService(self.db).record(actor_id, institution_id, "faculty.mentorship_ended", "faculty_student_mentorship", item.id, {"student_profile_id": item.student_profile_id, "faculty_profile_id": item.faculty_profile_id})
        await self.db.commit()
        await self.db.refresh(item)
        return item

    async def list_mentorships(self, institution_id: str, actor_id: str, student_id: str | None = None, faculty_id: str | None = None):
        await self.institutions.require_admin(institution_id, actor_id)
        query = select(FacultyStudentMentorship).where(FacultyStudentMentorship.institution_id == institution_id)
        if student_id:
            query = query.where(FacultyStudentMentorship.student_profile_id == student_id)
        if faculty_id:
            query = query.where(FacultyStudentMentorship.faculty_profile_id == faculty_id)
        result = await self.db.execute(query.order_by(FacultyStudentMentorship.created_at.desc()))
        return list(result.scalars().all())
