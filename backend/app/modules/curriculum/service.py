"""Versioned curriculum mapping with ownership and supervisor authorization."""
from __future__ import annotations
from datetime import UTC, datetime
from uuid import uuid4
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.academic import StudentProfile, FacultyProfile, Programme, Department, School
from app.models.curriculum import LearningOutcome, CurriculumMappingVersion, CurriculumMappingItem
from app.models.evaluation import ReportSubmission, ReportVersion
from app.models.internship import InternshipPlacement
from app.modules.institutions.service import InstitutionService
from app.modules.audit.service import AuditService


class CurriculumWorkflowError(Exception):
    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        self.message = message
        super().__init__(message)


class CurriculumService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_outcome(self, institution_id: str, actor_id: str, programme_id: str | None,
                             code: str, title: str, description: str | None):
        await InstitutionService(self.db).require_admin(institution_id, actor_id)
        if programme_id:
            scope = await self.db.scalar(select(School.id).join(Department, Department.school_id == School.id)
                .join(Programme, Programme.department_id == Department.id)
                .where(Programme.id == programme_id, School.institution_id == institution_id))
            if scope is None:
                raise CurriculumWorkflowError(422, "Programme must belong to the selected institution")
        item = LearningOutcome(id=str(uuid4()), institution_id=institution_id, programme_id=programme_id,
            code=code.strip(), title=title.strip(), description=description.strip() if description else None,
            created_by_account_id=actor_id, is_active=True)
        self.db.add(item)
        AuditService(self.db).record(actor_id, institution_id, "curriculum.outcome_created", "learning_outcome", item.id,
            {"programme_id": programme_id, "code": item.code})
        await self.db.commit()
        await self.db.refresh(item)
        return item

    async def list_outcomes(self, institution_id: str, actor_id: str):
        await InstitutionService(self.db).require_admin(institution_id, actor_id)
        rows = await self.db.execute(select(LearningOutcome).where(
            LearningOutcome.institution_id == institution_id, LearningOutcome.is_active.is_(True)
        ).order_by(LearningOutcome.code))
        return list(rows.scalars().all())

    async def _scope(self, submission_id: str, actor_id: str):
        submission = await self.db.get(ReportSubmission, submission_id)
        if submission is None:
            raise CurriculumWorkflowError(404, "Report submission not found")
        placement = await self.db.get(InternshipPlacement, submission.placement_id)
        student = await self.db.get(StudentProfile, placement.student_id) if placement else None
        if placement is None or student is None:
            raise CurriculumWorkflowError(404, "Report submission not found")
        student_owner = str(student.account_id) == str(actor_id)
        faculty = await self.db.scalar(select(FacultyProfile).where(FacultyProfile.account_id == actor_id))
        supervisor = faculty is not None and placement.faculty_supervisor_id == faculty.id
        if not student_owner and not supervisor:
            raise CurriculumWorkflowError(404, "Report submission not found")
        institution_id = await self.db.scalar(select(School.institution_id).join(
            Department, Department.school_id == School.id).where(Department.id == student.department_id))
        if institution_id is None and student.cohort_id:
            institution_id = await self.db.scalar(select(School.institution_id).join(
                Department, Department.school_id == School.id).join(Programme, Programme.department_id == Department.id)
                .join(__import__("app.models.academic", fromlist=["Cohort"]).Cohort,
                      __import__("app.models.academic", fromlist=["Cohort"]).Cohort.programme_id == Programme.id)
                .where(__import__("app.models.academic", fromlist=["Cohort"]).Cohort.id == student.cohort_id))
        return submission, placement, student, institution_id, student_owner, supervisor

    async def create_mapping(self, submission_id: str, actor_id: str, items: list[dict]):
        submission, placement, student, institution_id, student_owner, supervisor = await self._scope(submission_id, actor_id)
        if not student_owner:
            raise CurriculumWorkflowError(403, "Only the student can submit a curriculum mapping")
        if submission.status not in {"SUBMITTED", "UNDER_EVALUATION", "REVISION_REQUIRED", "APPROVED"}:
            raise CurriculumWorkflowError(409, "Submit the report before mapping its curriculum outcomes")
        version = await self.db.scalar(select(ReportVersion).where(
            ReportVersion.submission_id == submission_id,
            ReportVersion.version_number == submission.latest_version_number))
        if version is None:
            raise CurriculumWorkflowError(409, "Current report version is unavailable")
        prior = await self.db.scalar(select(func.max(CurriculumMappingVersion.version_number)).where(
            CurriculumMappingVersion.report_version_id == version.id))
        mapping = CurriculumMappingVersion(id=str(uuid4()), report_version_id=version.id,
            version_number=(prior or 0) + 1, status="SUBMITTED", created_by_account_id=actor_id)
        self.db.add(mapping)
        allowed_files = {"REPORT": version.file_id, "PRESENTATION": version.presentation_file_id}
        for entry in items:
            outcome = await self.db.get(LearningOutcome, entry["learning_outcome_id"])
            if outcome is None or not outcome.is_active or outcome.institution_id != institution_id:
                raise CurriculumWorkflowError(422, "Each outcome must be active and belong to the student's institution")
            if outcome.programme_id and outcome.programme_id != student.programme_id:
                raise CurriculumWorkflowError(422, "Outcome is outside the student's programme")
            evidence_type = entry["evidence_type"]
            file_id = allowed_files.get(evidence_type)
            if not file_id:
                raise CurriculumWorkflowError(422, f"No {evidence_type.lower()} evidence exists in this report version")
            self.db.add(CurriculumMappingItem(id=str(uuid4()), mapping_version_id=mapping.id,
                learning_outcome_id=outcome.id, evidence_type=evidence_type, evidence_file_id=file_id,
                evidence_status="UNREVIEWED", provenance="STUDENT_SUBMISSION"))
        AuditService(self.db).record(actor_id, institution_id, "curriculum.mapping_submitted",
            "curriculum_mapping_version", mapping.id, {"report_submission_id": submission_id, "version_number": mapping.version_number})
        await self.db.commit()
        return await self.get_mapping(submission_id, actor_id)

    async def review_mapping(self, submission_id: str, mapping_id: str, actor_id: str, notes: str | None, items: list[dict]):
        submission, placement, student, institution_id, student_owner, supervisor = await self._scope(submission_id, actor_id)
        if not supervisor:
            raise CurriculumWorkflowError(403, "Only the assigned placement supervisor can review this mapping")
        old = await self.db.get(CurriculumMappingVersion, mapping_id)
        if old is None or old.report_version_id not in (await self.db.scalars(
            select(ReportVersion.id).where(ReportVersion.submission_id == submission_id))).all():
            raise CurriculumWorkflowError(404, "Curriculum mapping version not found")
        old_items = await self.db.scalars(select(CurriculumMappingItem).where(CurriculumMappingItem.mapping_version_id == old.id))
        old_by_outcome = {item.learning_outcome_id: item for item in old_items.all()}
        requested = {item["learning_outcome_id"]: item for item in items}
        if set(requested) != set(old_by_outcome):
            raise CurriculumWorkflowError(422, "Review must address every mapped outcome exactly once")
        new = CurriculumMappingVersion(id=str(uuid4()), report_version_id=old.report_version_id,
            version_number=old.version_number + 1, status="REVIEWED", reviewer_notes=notes,
            created_by_account_id=actor_id, reviewed_by_account_id=actor_id,
            reviewed_at=datetime.now(UTC).replace(tzinfo=None))
        self.db.add(new)
        for outcome_id, prior_item in old_by_outcome.items():
            review = requested[outcome_id]
            self.db.add(CurriculumMappingItem(id=str(uuid4()), mapping_version_id=new.id,
                learning_outcome_id=outcome_id, evidence_type=prior_item.evidence_type,
                evidence_file_id=prior_item.evidence_file_id, evidence_status=review["evidence_status"],
                reviewer_notes=review.get("reviewer_notes"), provenance="FACULTY_REVIEW"))
        AuditService(self.db).record(actor_id, institution_id, "curriculum.mapping_reviewed",
            "curriculum_mapping_version", new.id, {"prior_mapping_id": old.id, "report_submission_id": submission_id})
        await self.db.commit()
        return await self.get_mapping(submission_id, actor_id)

    async def get_mapping(self, submission_id: str, actor_id: str):
        submission, *_ = await self._scope(submission_id, actor_id)
        versions = list((await self.db.scalars(select(CurriculumMappingVersion).join(
            ReportVersion, ReportVersion.id == CurriculumMappingVersion.report_version_id)
            .where(ReportVersion.submission_id == submission_id)
            .order_by(CurriculumMappingVersion.version_number.desc()))).all())
        output = []
        for version in versions:
            rows = await self.db.execute(select(CurriculumMappingItem, LearningOutcome).join(
                LearningOutcome, LearningOutcome.id == CurriculumMappingItem.learning_outcome_id)
                .where(CurriculumMappingItem.mapping_version_id == version.id))
            output.append({"id": version.id, "report_version_id": version.report_version_id,
                "version_number": version.version_number, "status": version.status,
                "reviewer_notes": version.reviewer_notes, "created_by_account_id": version.created_by_account_id,
                "reviewed_by_account_id": version.reviewed_by_account_id, "reviewed_at": version.reviewed_at,
                "items": [{"id": item.id, "learning_outcome_id": outcome.id, "code": outcome.code,
                    "title": outcome.title, "description": outcome.description, "evidence_type": item.evidence_type,
                    "evidence_status": item.evidence_status, "reviewer_notes": item.reviewer_notes,
                    "provenance": item.provenance} for item, outcome in rows.all()]})
        return {"items": output}
