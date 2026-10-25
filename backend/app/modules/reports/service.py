"""Report submission, immutable version history, and review state transitions."""
from __future__ import annotations

from datetime import UTC, date, datetime
from uuid import uuid4
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.academic import Account, Cohort, Department, FacultyProfile, Programme, School, StudentProfile
from app.models.evaluation import ReportRequirement, ReportSubmission, ReportVersion
from app.models.internship import InternshipPlacement
from app.models.storage import StorageFile
from app.services.email import send_workflow_notification
from app.modules.audit.service import AuditService
from app.modules.institutions.service import InstitutionService


class ReportWorkflowError(Exception):
    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        self.message = message
        super().__init__(message)


class ReportService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def _student_for_account(self, account_id: str) -> StudentProfile:
        result = await self.db.execute(select(StudentProfile).where(StudentProfile.account_id == account_id))
        student = result.scalar_one_or_none()
        if student is None:
            raise ReportWorkflowError(403, "Student account required")
        return student

    async def _institution_for_student(self, student_id: str) -> str | None:
        return await self.db.scalar(select(School.institution_id).join(Department, Department.school_id == School.id)
            .join(Programme, Programme.department_id == Department.id).join(Cohort, Cohort.programme_id == Programme.id)
            .join(StudentProfile, StudentProfile.cohort_id == Cohort.id).where(StudentProfile.id == student_id))

    async def _placement(self, placement_id: str) -> InternshipPlacement:
        placement = await self.db.get(InternshipPlacement, placement_id)
        if placement is None:
            raise ReportWorkflowError(404, "Placement not found")
        return placement

    async def _owned_submission(self, submission_id: str, account_id: str) -> tuple[ReportSubmission, InternshipPlacement]:
        submission = await self.db.get(ReportSubmission, submission_id)
        if submission is None:
            raise ReportWorkflowError(404, "Report submission not found")
        student = await self._student_for_account(account_id)
        placement = await self._placement(submission.placement_id)
        if placement.student_id != student.id:
            raise ReportWorkflowError(404, "Report submission not found")
        return submission, placement

    async def _notify_account(self, account_id: str, subject: str, message: str) -> None:
        account = await self.db.get(Account, account_id)
        if account is not None and account.email:
            try:
                await send_workflow_notification(account.email, subject, message)
            except Exception:
                # Delivery failure never rolls back a committed workflow transition.
                pass

    async def _owned_file(self, file_id: str, account_id: str) -> StorageFile:
        file = await self.db.get(StorageFile, file_id)
        if file is None or file.uploaded_by_account_id != account_id:
            raise ReportWorkflowError(422, "File must exist and belong to the authenticated account")
        return file

    async def create(
        self, account_id: str, placement_id: str, title: str, file_id: str,
        notes: str | None, requirement_id: str | None = None,
        presentation_file_id: str | None = None,
    ) -> ReportSubmission:
        student = await self._student_for_account(account_id)
        placement = await self._placement(placement_id)
        if placement.student_id != student.id:
            raise ReportWorkflowError(404, "Placement not found")
        await self._owned_file(file_id, account_id)
        if presentation_file_id is not None:
            await self._owned_file(presentation_file_id, account_id)
            if presentation_file_id == file_id:
                raise ReportWorkflowError(422, "The presentation must be a separate uploaded file")
        if placement.status != "ONGOING":
            raise ReportWorkflowError(409, "Reports can only be created for ongoing placements")
        if requirement_id is not None:
            requirement = await self.db.get(ReportRequirement, requirement_id)
            institution_id = await self._institution_for_student(student.id)
            if requirement is None or not requirement.is_active or requirement.institution_id != institution_id:
                raise ReportWorkflowError(422, "Report requirement must be active and belong to the student institution")
            if requirement.due_date is not None and requirement.due_date < date.today():
                raise ReportWorkflowError(409, "The report requirement deadline has passed")
            existing = await self.db.scalar(select(ReportSubmission.id).where(
                ReportSubmission.placement_id == placement_id, ReportSubmission.requirement_id == requirement_id
            ))
            if existing is not None:
                raise ReportWorkflowError(409, "A submission already exists for this requirement and placement")
        institution_id = await self._institution_for_student(student.id)
        if institution_id is None and student.department_id:
            institution_id = await self.db.scalar(
                select(School.institution_id).join(Department, Department.school_id == School.id)
                .where(Department.id == student.department_id)
            )
        if institution_id is None and student.programme_id:
            institution_id = await self.db.scalar(
                select(School.institution_id).join(Department, Department.school_id == School.id)
                .join(Programme, Programme.department_id == Department.id)
                .where(Programme.id == student.programme_id)
            )
        cohort = await self.db.get(Cohort, student.cohort_id) if student.cohort_id else None
        programme_id = student.programme_id or (cohort.programme_id if cohort else None)
        academic_year_id = cohort.academic_year_id if cohort else None
        submission = ReportSubmission(
            id=str(uuid4()), placement_id=placement_id, requirement_id=requirement_id,
            institution_id=institution_id, programme_id=programme_id, cohort_id=student.cohort_id,
            academic_year_id=academic_year_id, academic_semester=student.current_semester,
            title=title.strip(), latest_version_number=1, status="DRAFT",
        )
        self.db.add(submission)
        await self.db.flush()
        self.db.add(ReportVersion(
            id=str(uuid4()), submission_id=submission.id, version_number=1, file_id=file_id,
            presentation_file_id=presentation_file_id, submission_notes=notes,
        ))
        AuditService(self.db).record(account_id, institution_id, "report.created", "report_submission", submission.id, {"placement_id": placement_id, "requirement_id": requirement_id})
        await self.db.commit()
        await self.db.refresh(submission)
        return submission

    async def list_for_faculty(self, account_id: str) -> list[ReportSubmission]:
        faculty = await self.db.scalar(select(FacultyProfile).where(FacultyProfile.account_id == account_id))
        if faculty is None:
            raise ReportWorkflowError(403, "Faculty account required")
        result = await self.db.execute(
            select(ReportSubmission)
            .join(InternshipPlacement, InternshipPlacement.id == ReportSubmission.placement_id)
            .where(InternshipPlacement.faculty_supervisor_id == faculty.id)
            .order_by(ReportSubmission.updated_at.desc())
        )
        return list(result.scalars().all())

    async def list_mine(self, account_id: str) -> list[ReportSubmission]:
        student = await self._student_for_account(account_id)
        result = await self.db.execute(
            select(ReportSubmission).join(InternshipPlacement, InternshipPlacement.id == ReportSubmission.placement_id)
            .where(InternshipPlacement.student_id == student.id)
            .order_by(ReportSubmission.updated_at.desc())
        )
        return list(result.scalars().all())

    async def get(self, submission_id: str, account_id: str) -> ReportSubmission:
        submission = await self.db.get(ReportSubmission, submission_id)
        if submission is None:
            raise ReportWorkflowError(404, "Report submission not found")
        student_result = await self.db.execute(select(StudentProfile).where(StudentProfile.account_id == account_id))
        student = student_result.scalar_one_or_none()
        if student is not None:
            placement = await self._placement(submission.placement_id)
            if placement.student_id == student.id:
                return submission
        faculty_result = await self.db.execute(select(FacultyProfile).where(FacultyProfile.account_id == account_id))
        faculty = faculty_result.scalar_one_or_none()
        if faculty is not None:
            placement = await self._placement(submission.placement_id)
            if placement.faculty_supervisor_id == faculty.id:
                return submission
        raise ReportWorkflowError(404, "Report submission not found")

    async def versions(self, submission_id: str, account_id: str) -> list[ReportVersion]:
        await self.get(submission_id, account_id)
        result = await self.db.execute(select(ReportVersion).where(
            ReportVersion.submission_id == submission_id
        ).order_by(ReportVersion.version_number.desc()))
        return list(result.scalars().all())

    async def rename_draft(self, submission_id: str, account_id: str, title: str) -> ReportSubmission:
        submission, _ = await self._owned_submission(submission_id, account_id)
        if submission.status not in {"DRAFT", "REVISION_REQUIRED"}:
            raise ReportWorkflowError(409, "Only draft or revision-required reports can be edited")
        submission.title = title.strip()
        await self.db.commit()
        await self.db.refresh(submission)
        return submission

    async def add_version(
        self, submission_id: str, account_id: str, file_id: str, notes: str | None,
        presentation_file_id: str | None = None,
    ) -> ReportVersion:
        submission, placement = await self._owned_submission(submission_id, account_id)
        if submission.status not in {"DRAFT", "REVISION_REQUIRED"}:
            raise ReportWorkflowError(409, "Submitted versions are immutable; revisions require a revision-required status")
        await self._owned_file(file_id, account_id)
        if presentation_file_id is not None:
            await self._owned_file(presentation_file_id, account_id)
            if presentation_file_id == file_id:
                raise ReportWorkflowError(422, "The presentation must be a separate uploaded file")
        next_version = submission.latest_version_number + 1
        version = ReportVersion(
            id=str(uuid4()), submission_id=submission.id, version_number=next_version,
            file_id=file_id, presentation_file_id=presentation_file_id, submission_notes=notes,
        )
        submission.latest_version_number = next_version
        self.db.add(version)
        institution_id = await self._institution_for_student(placement.student_id)
        AuditService(self.db).record(account_id, institution_id, "report.version_added", "report_version", version.id, {"submission_id": submission.id, "version_number": next_version})
        await self.db.commit()
        await self.db.refresh(version)
        return version

    async def submit(self, submission_id: str, account_id: str) -> ReportSubmission:
        submission, placement = await self._owned_submission(submission_id, account_id)
        if submission.status not in {"DRAFT", "REVISION_REQUIRED"}:
            raise ReportWorkflowError(409, "Report cannot be submitted from its current state")
        result = await self.db.execute(select(ReportVersion.id).where(
            ReportVersion.submission_id == submission.id,
            ReportVersion.version_number == submission.latest_version_number,
        ))
        if result.scalar_one_or_none() is None:
            raise ReportWorkflowError(409, "A current report version is required before submission")
        if submission.status == "REVISION_REQUIRED":
            submission.review_feedback = None
            submission.reviewed_by_account_id = None
            submission.reviewed_at = None
        submission.status = "SUBMITTED"
        institution_id = await self._institution_for_student(placement.student_id)
        AuditService(self.db).record(account_id, institution_id, "report.submitted", "report_submission", submission.id, {"version_number": submission.latest_version_number})
        await self.db.commit()
        await self.db.refresh(submission)
        faculty = await self.db.get(FacultyProfile, placement.faculty_supervisor_id) if placement.faculty_supervisor_id else None
        if faculty is not None:
            await self._notify_account(faculty.account_id, "Kairos report submitted", f"A report has been submitted for review: {submission.title}.")
        return submission

    async def review(self, submission_id: str, account_id: str, target_status: str, feedback_comments: str | None = None) -> ReportSubmission:
        submission = await self.db.get(ReportSubmission, submission_id)
        if submission is None:
            raise ReportWorkflowError(404, "Report submission not found")
        faculty_result = await self.db.execute(select(FacultyProfile).where(FacultyProfile.account_id == account_id))
        faculty = faculty_result.scalar_one_or_none()
        if faculty is None:
            raise ReportWorkflowError(403, "Faculty account required")
        placement = await self._placement(submission.placement_id)
        if placement.faculty_supervisor_id != faculty.id:
            raise ReportWorkflowError(403, "Only the assigned faculty supervisor may review this report")
        allowed = {
            "SUBMITTED": {"UNDER_EVALUATION", "REVISION_REQUIRED", "APPROVED", "REJECTED"},
            "UNDER_EVALUATION": {"REVISION_REQUIRED", "APPROVED", "REJECTED"},
        }
        if target_status not in allowed.get(submission.status, set()):
            raise ReportWorkflowError(409, "Invalid report status transition")
        if target_status == "REVISION_REQUIRED" and not (feedback_comments and feedback_comments.strip()):
            raise ReportWorkflowError(422, "Feedback is required when returning a report for revision")
        old_status = submission.status
        submission.status = target_status
        submission.review_feedback = feedback_comments.strip() if feedback_comments else None
        submission.reviewed_by_account_id = account_id
        submission.reviewed_at = datetime.now(UTC).replace(tzinfo=None)
        institution_id = await self._institution_for_student(placement.student_id)
        AuditService(self.db).record(account_id, institution_id, "report.review_status_changed", "report_submission", submission.id, {"from": old_status, "to": target_status})
        await self.db.commit()
        await self.db.refresh(submission)
        student = await self.db.get(StudentProfile, placement.student_id)
        if student is not None:
            readable_status = target_status.lower().replace("_", " ")
            await self._notify_account(student.account_id, "Kairos report status updated", f"Your report status is now {readable_status}.")
        return submission


class ReportRequirementService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.institutions = InstitutionService(db)

    async def create(self, institution_id: str, actor_id: str, title: str, description: str | None,
                     due_date, is_required: bool) -> ReportRequirement:
        await self.institutions.require_admin(institution_id, actor_id)
        item = ReportRequirement(id=str(uuid4()), institution_id=institution_id, title=title.strip(),
            description=description, due_date=due_date, is_required=is_required, is_active=True,
            created_by_account_id=actor_id)
        self.db.add(item)
        AuditService(self.db).record(actor_id, institution_id, "report.requirement_created", "report_requirement", item.id, {"title": item.title, "due_date": str(due_date) if due_date else None})
        await self.db.commit()
        await self.db.refresh(item)
        return item

    async def list_for_institution(self, institution_id: str, actor_id: str) -> list[ReportRequirement]:
        await self.institutions.require_admin(institution_id, actor_id)
        result = await self.db.execute(select(ReportRequirement).where(
            ReportRequirement.institution_id == institution_id
        ).order_by(ReportRequirement.created_at.desc()))
        return list(result.scalars().all())

    async def set_active(self, institution_id: str, actor_id: str, requirement_id: str, is_active: bool) -> ReportRequirement:
        await self.institutions.require_admin(institution_id, actor_id)
        item = await self.db.get(ReportRequirement, requirement_id)
        if item is None or item.institution_id != institution_id:
            raise ReportWorkflowError(404, "Report requirement not found in this institution")
        item.is_active = is_active
        AuditService(self.db).record(actor_id, institution_id, "report.requirement_status_changed", "report_requirement", item.id, {"is_active": is_active})
        await self.db.commit()
        await self.db.refresh(item)
        return item

    async def list_for_student(self, account_id: str) -> list[dict]:
        student_result = await self.db.execute(select(StudentProfile).where(StudentProfile.account_id == account_id))
        student = student_result.scalar_one_or_none()
        if student is None:
            raise ReportWorkflowError(403, "Student account required")
        institution_id = await ReportService(self.db)._institution_for_student(student.id)
        if institution_id is None:
            return []
        result = await self.db.execute(select(ReportRequirement).where(
            ReportRequirement.institution_id == institution_id, ReportRequirement.is_active.is_(True)
        ).order_by(ReportRequirement.due_date, ReportRequirement.title))
        requirements = list(result.scalars().all())
        items = []
        for requirement in requirements:
            status = await self.db.scalar(select(ReportSubmission.status).join(
                InternshipPlacement, InternshipPlacement.id == ReportSubmission.placement_id
            ).where(ReportSubmission.requirement_id == requirement.id,
                    InternshipPlacement.student_id == student.id).order_by(ReportSubmission.updated_at.desc()).limit(1))
            if status is None and requirement.is_required and requirement.due_date is not None and requirement.due_date < date.today():
                status = "OVERDUE"
            items.append({"requirement": requirement, "submission_status": status})
        return items
