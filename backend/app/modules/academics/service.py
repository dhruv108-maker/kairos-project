"""Academic-owned lookups for the existing school-to-student hierarchy."""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.academic import (
    AcademicYear, Cohort, Department, Programme, School, StudentProfile,
)


class AcademicService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def student_profile_for_account(self, account_id: str) -> StudentProfile | None:
        return await self.session.scalar(
            select(StudentProfile).where(StudentProfile.account_id == account_id)
        )

    async def enrollment_context(self, account_id: str) -> dict | None:
        row = (await self.session.execute(
            select(
                Cohort.id, Cohort.name, Cohort.graduation_year, AcademicYear.year_label,
                Programme.id, Programme.name, Department.id, Department.name,
                School.id, School.name, StudentProfile.current_semester,
            )
            .join(StudentProfile, StudentProfile.cohort_id == Cohort.id)
            .join(AcademicYear, AcademicYear.id == Cohort.academic_year_id)
            .join(Programme, Programme.id == Cohort.programme_id)
            .join(Department, Department.id == Programme.department_id)
            .join(School, School.id == Department.school_id)
            .where(StudentProfile.account_id == account_id)
        )).first()
        if row is None:
            return None
        return {
            "items": [{
                "cohort": {"id": row[0], "name": row[1], "graduation_year": row[2]},
                "academic_year": {"label": row[3]},
                "programme": {"id": row[4], "name": row[5]},
                "department": {"id": row[6], "name": row[7]},
                "school": {"id": row[8], "name": row[9]},
                "current_semester": row[10],
            }],
            "note": "Derived from the existing cohort relationship; no separate student_enrollments table exists.",
        }
