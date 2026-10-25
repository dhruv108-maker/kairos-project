"""Aggregate dashboards built from persisted workflow data."""
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.academic import Account, Cohort, Department, FacultyProfile, Programme, School, StudentProfile
from app.models.evaluation import GriffinEvaluation, ReportSubmission, ReportVersion
from app.models.internship import InternshipApplication, InternshipPlacement
from app.models.mentorship import FacultyStudentMentorship
from app.models.organizations import AssessmentCampaign, FacultyAssessmentAssignment
from app.modules.institutions.service import InstitutionService, InstitutionAccessError
from app.modules.student_portfolio.service import StudentPortfolioService


class AnalyticsAccessError(Exception):
    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        self.message = message
        super().__init__(message)


class AnalyticsService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.institutions = InstitutionService(db)

    async def _count(self, query) -> int:
        return int((await self.db.scalar(query)) or 0)

    async def student_dashboard(self, account_id: str) -> dict:
        account = await self.db.get(Account, account_id)
        profile = await self.db.scalar(select(StudentProfile).where(StudentProfile.account_id == account_id))
        if account is None or profile is None:
            raise AnalyticsAccessError(403, "Student account required")
        # The deployed schema stores student-facing internship activity against students.id.
        # Reports belong to internship_participations (not internship_placements), and
        # report_submissions uses workflow_status rather than status.
        from sqlalchemy import text

        student_id = profile.student_id
        applications = int((await self.db.scalar(text(
            "SELECT COUNT(*) FROM internship_applications WHERE student_id = :student_id"
        ), {"student_id": student_id})) or 0)
        placements = int((await self.db.scalar(text(
            "SELECT COUNT(*) FROM internship_placements WHERE student_id = :student_id"
        ), {"student_id": student_id})) or 0)
        reports = int((await self.db.scalar(text(
            "SELECT COUNT(*) FROM report_submissions rs "
            "JOIN internship_participations ip ON ip.id = rs.participation_id "
            "WHERE ip.student_id = :student_id"
        ), {"student_id": student_id})) or 0)
        pending_reports = int((await self.db.scalar(text(
            "SELECT COUNT(*) FROM report_submissions rs "
            "JOIN internship_participations ip ON ip.id = rs.participation_id "
            "WHERE ip.student_id = :student_id "
            "AND rs.workflow_status IN ('awaiting_submission', 'submitted', 'under_evaluation', 'changes_requested')"
        ), {"student_id": student_id})) or 0)
        # The deployed schema's Griffin evaluation table/relationship differs from the
        # newer ORM model; do not query nonexistent placement_id/report_version_id links.
        completed_evaluations = 0
        portfolio = await StudentPortfolioService(self.db).summary(profile, account)
        completeness = await StudentPortfolioService(self.db).completeness(profile, account)
        return {"student": portfolio["student"], "portfolio": {"counts": portfolio["counts"], "completeness": completeness},
                "internships": {"applications": applications, "placements": placements},
                "reports": {"total": reports, "pending_review": pending_reports, "completed_evaluations": completed_evaluations}}

    async def faculty_dashboard(self, account_id: str) -> dict:
        faculty = await self.db.scalar(select(FacultyProfile).where(FacultyProfile.account_id == account_id))
        if faculty is None:
            raise AnalyticsAccessError(403, "Faculty account required")
        placements = await self._count(select(func.count(InternshipPlacement.id)).where(InternshipPlacement.faculty_supervisor_id == faculty.id))
        pending_reports = await self._count(select(func.count(ReportSubmission.id)).join(
            InternshipPlacement, InternshipPlacement.id == ReportSubmission.placement_id
        ).where(InternshipPlacement.faculty_supervisor_id == faculty.id, ReportSubmission.status.in_(("SUBMITTED", "UNDER_EVALUATION"))))
        # The deployed MySQL schema uses faculty_mentorships.faculty_id and
        # lowercase lifecycle values; it does not have faculty_profile_id.
        from sqlalchemy import text

        mentorships = int((await self.db.scalar(
            text("""
                SELECT COUNT(*)
                FROM faculty_mentorships
                WHERE faculty_id = :faculty_id
                  AND status = 'active'
                  AND (ends_on IS NULL OR ends_on >= CURRENT_DATE())
            """),
            {"faculty_id": faculty.id},
        )) or 0)
        pending_assessments = await self._count(select(func.count(FacultyAssessmentAssignment.id)).where(
            FacultyAssessmentAssignment.faculty_id == faculty.id, FacultyAssessmentAssignment.status.in_(("PENDING", "IN_PROGRESS"))))
        return {"faculty_id": faculty.id, "placements_supervised": placements, "reports_pending_review": pending_reports,
                "active_mentorships": mentorships, "pending_assessment_assignments": pending_assessments}

    async def institution_dashboard(self, institution_id: str, account_id: str) -> dict:
        await self.institutions.require_admin(institution_id, account_id)
        student_count = await self._count(select(func.count(StudentProfile.id)).join(Cohort, Cohort.id == StudentProfile.cohort_id)
            .join(Programme, Programme.id == Cohort.programme_id).join(Department, Department.id == Programme.department_id)
            .join(School, School.id == Department.school_id).where(School.institution_id == institution_id))
        faculty_count = await self._count(select(func.count(FacultyProfile.id)).join(Department, Department.id == FacultyProfile.department_id)
            .join(School, School.id == Department.school_id).where(School.institution_id == institution_id))
        school_count = await self._count(select(func.count(School.id)).where(School.institution_id == institution_id))
        department_count = await self._count(select(func.count(Department.id)).join(School, School.id == Department.school_id)
            .where(School.institution_id == institution_id))
        placement_count = await self._count(select(func.count(InternshipPlacement.id)).join(
            StudentProfile, StudentProfile.id == InternshipPlacement.student_id).join(Cohort, Cohort.id == StudentProfile.cohort_id)
            .join(Programme, Programme.id == Cohort.programme_id).join(Department, Department.id == Programme.department_id)
            .join(School, School.id == Department.school_id).where(School.institution_id == institution_id))
        pending_reports = await self._count(select(func.count(ReportSubmission.id)).join(
            InternshipPlacement, InternshipPlacement.id == ReportSubmission.placement_id).join(
            StudentProfile, StudentProfile.id == InternshipPlacement.student_id).join(Cohort, Cohort.id == StudentProfile.cohort_id)
            .join(Programme, Programme.id == Cohort.programme_id).join(Department, Department.id == Programme.department_id)
            .join(School, School.id == Department.school_id).where(
                School.institution_id == institution_id, ReportSubmission.status.in_(("SUBMITTED", "UNDER_EVALUATION", "REVISION_REQUIRED"))))
        active_campaigns = await self._count(select(func.count(AssessmentCampaign.id)).where(
            AssessmentCampaign.institution_id == institution_id, AssessmentCampaign.is_active.is_(True)))
        return {"institution_id": institution_id, "students": student_count, "faculty": faculty_count,
                "schools": school_count, "departments": department_count, "placements": placement_count,
                "reports_pending_review": pending_reports, "active_assessment_campaigns": active_campaigns}
