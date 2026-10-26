"""Policy-driven result assembly and separated approval/publication."""
from datetime import UTC, datetime
from decimal import Decimal, ROUND_HALF_UP
from uuid import uuid4
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.academic import StudentProfile, FacultyProfile, Department, School, Programme, Cohort
from app.models.assessment import AssessmentRubric, AssessmentRubricCriterion, BlindAssessmentAssignment, BlindAssessmentScore
from app.models.curriculum import CurriculumMappingVersion, CurriculumMappingItem
from app.models.evaluation import ReportSubmission, ReportVersion, GriffinEvaluation, GriffinResultSnapshot
from app.models.internship import InternshipPlacement
from app.models.academic_result import InternshipGradingPolicy, OfficialInternshipResult, OfficialInternshipResultHistory
from app.modules.institutions.service import InstitutionService
from app.modules.audit.service import AuditService


class OfficialResultError(Exception):
    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        self.message = message
        super().__init__(message)


class OfficialResultService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def _institution_for_student(self, student: StudentProfile):
        if student.department_id:
            value = await self.db.scalar(select(School.institution_id).join(Department, Department.school_id == School.id).where(Department.id == student.department_id))
            if value:
                return value
        if student.cohort_id:
            return await self.db.scalar(select(School.institution_id).join(Department, Department.school_id == School.id)
                .join(Programme, Programme.department_id == Department.id).join(Cohort, Cohort.programme_id == Programme.id)
                .where(Cohort.id == student.cohort_id))
        return None

    async def create_policy(self, institution_id: str, actor_id: str, config: dict):
        await InstitutionService(self.db).require_admin(institution_id, actor_id)
        latest = await self.db.scalar(select(func.max(InternshipGradingPolicy.version_number)).where(InternshipGradingPolicy.institution_id == institution_id))
        item = InternshipGradingPolicy(id=str(uuid4()), institution_id=institution_id, version_number=(latest or 0) + 1,
            status="DRAFT", policy_json=config, created_by_account_id=actor_id)
        self.db.add(item)
        AuditService(self.db).record(actor_id, institution_id, "grading_policy.created", "internship_grading_policy", item.id,
            {"version_number": item.version_number, "require_griffin": config["require_griffin"], "require_curriculum_review": config["require_curriculum_review"]})
        await self.db.commit()
        await self.db.refresh(item)
        return item

    async def approve_policy(self, policy_id: str, actor_id: str):
        item = await self.db.get(InternshipGradingPolicy, policy_id)
        if item is None:
            raise OfficialResultError(404, "Grading policy not found")
        await InstitutionService(self.db).require_admin(item.institution_id, actor_id)
        if item.status != "DRAFT":
            raise OfficialResultError(409, "Only draft grading policies can be approved")
        item.status = "APPROVED"
        item.approved_by_account_id = actor_id
        item.approved_at = datetime.now(UTC).replace(tzinfo=None)
        AuditService(self.db).record(actor_id, item.institution_id, "grading_policy.approved", "internship_grading_policy", item.id,
            {"version_number": item.version_number})
        await self.db.commit()
        await self.db.refresh(item)
        return item

    async def _calculate(self, submission_id: str, policy_id: str, actor_id: str):
        submission = await self.db.get(ReportSubmission, submission_id)
        if submission is None:
            raise OfficialResultError(404, "Report submission not found")
        placement = await self.db.get(InternshipPlacement, submission.placement_id)
        student = await self.db.get(StudentProfile, placement.student_id) if placement else None
        if not placement or not student:
            raise OfficialResultError(404, "Report submission not found")
        institution_id = await self._institution_for_student(student)
        if institution_id is None:
            raise OfficialResultError(409, "Student institution could not be established from the academic hierarchy")
        await InstitutionService(self.db).require_admin(institution_id, actor_id)
        policy = await self.db.get(InternshipGradingPolicy, policy_id)
        if policy is None or policy.institution_id != institution_id:
            raise OfficialResultError(422, "Grading policy must belong to the student's institution")
        if policy.status != "APPROVED":
            raise OfficialResultError(409, "Official result is blocked until an institutional grading policy is approved")
        if submission.status != "APPROVED":
            raise OfficialResultError(409, "Report must be approved before official result calculation")
        version = await self.db.scalar(select(ReportVersion).where(ReportVersion.submission_id == submission_id,
            ReportVersion.version_number == submission.latest_version_number))
        if version is None:
            raise OfficialResultError(409, "Current submitted version is unavailable")
        config = policy.policy_json
        if config.get("require_griffin"):
            griffin = await self.db.scalar(select(GriffinResultSnapshot.id).join(
                GriffinEvaluation, GriffinEvaluation.id == GriffinResultSnapshot.griffin_evaluation_id)
                .where(GriffinEvaluation.report_version_id == version.id))
            if griffin is None:
                raise OfficialResultError(409, "Approved policy requires a validated Griffin result; Griffin is currently blocked by its missing external contract")
        mapping = await self.db.scalar(select(CurriculumMappingVersion).join(
            ReportVersion, ReportVersion.id == CurriculumMappingVersion.report_version_id)
            .where(ReportVersion.submission_id == submission_id, CurriculumMappingVersion.status == "REVIEWED")
            .order_by(CurriculumMappingVersion.version_number.desc()))
        if config.get("require_curriculum_review") and mapping is None:
            raise OfficialResultError(409, "Approved policy requires a reviewed curriculum mapping")
        assignments = list((await self.db.scalars(select(BlindAssessmentAssignment).where(
            BlindAssessmentAssignment.report_version_id == version.id,
            BlindAssessmentAssignment.status == "SUBMITTED"))).all())
        minimum_evaluators = int(config.get("minimum_evaluators", 1))
        if len(assignments) < minimum_evaluators:
            raise OfficialResultError(409, "Required independent faculty assessments are incomplete")
        rubric_ids = {assignment.rubric_id for assignment in assignments}
        if len(rubric_ids) != 1:
            raise OfficialResultError(409, "All submitted evaluators must use the same approved rubric version")
        rubric_id = next(iter(rubric_ids))
        rubric = await self.db.get(AssessmentRubric, rubric_id)
        if rubric is None or rubric.status != "APPROVED" or rubric.institution_id != institution_id:
            raise OfficialResultError(409, "Assessment rubric must be approved and institution-scoped")
        criteria = list((await self.db.scalars(select(AssessmentRubricCriterion).where(
            AssessmentRubricCriterion.rubric_id == rubric_id))).all())
        if not criteria or any(c.weight <= 0 for c in criteria):
            raise OfficialResultError(409, "Rubric must define a positive weight for every criterion")
        scores_by_criterion = {c.id: [] for c in criteria}
        for assignment in assignments:
            rows = list((await self.db.scalars(select(BlindAssessmentScore).where(
                BlindAssessmentScore.assignment_id == assignment.id))).all())
            if {row.criterion_id for row in rows} != set(scores_by_criterion):
                raise OfficialResultError(409, "Every evaluator must submit every rubric criterion")
            for row in rows:
                scores_by_criterion[row.criterion_id].append(row.score)
        weighted = Decimal("0")
        total_weight = sum((criterion.weight for criterion in criteria), Decimal("0"))
        for criterion in criteria:
            average = sum(scores_by_criterion[criterion.id], Decimal("0")) / Decimal(len(assignments))
            normalized = ((average - criterion.minimum_score) / (criterion.maximum_score - criterion.minimum_score)) * Decimal("100")
            weighted += normalized * criterion.weight
        raw = weighted / total_weight
        quantum = Decimal("1").scaleb(-int(config.get("rounding_places", 2)))
        score = raw.quantize(quantum, rounding=ROUND_HALF_UP)
        grade = None
        for band in sorted(config.get("grade_bands", []), key=lambda item: Decimal(str(item["minimum_score"])), reverse=True):
            if score >= Decimal(str(band["minimum_score"])):
                grade = str(band["grade"])
                break
        academic_year_id = await self.db.scalar(select(Cohort.academic_year_id).where(Cohort.id == student.cohort_id)) if student.cohort_id else None
        return {"submission": submission, "placement": placement, "student": student, "institution_id": institution_id,
            "policy": policy, "version": version, "mapping": mapping, "score": score, "grade": grade,
            "academic_year_id": academic_year_id}

    async def preview(self, submission_id: str, policy_id: str, actor_id: str):
        calculated = await self._calculate(submission_id, policy_id, actor_id)
        return {"status": "READY_FOR_APPROVAL", "report_submission_id": submission_id,
            "report_version_id": calculated["version"].id, "grading_policy_id": calculated["policy"].id,
            "grading_policy_version": calculated["policy"].version_number, "curriculum_mapping_version_id": calculated["mapping"].id if calculated["mapping"] else None,
            "total_score": str(calculated["score"]), "final_grade": calculated["grade"],
            "student_profile_id": calculated["student"].id, "institution_id": calculated["institution_id"],
            "academic_year_id": calculated["academic_year_id"], "semester_number": calculated["student"].current_semester}

    async def prepare(self, submission_id: str, policy_id: str, actor_id: str):
        existing = await self.db.scalar(select(OfficialInternshipResult).where(OfficialInternshipResult.report_submission_id == submission_id))
        if existing is not None:
            raise OfficialResultError(409, "An official result already exists for this report submission")
        data = await self._calculate(submission_id, policy_id, actor_id)
        item = OfficialInternshipResult(id=str(uuid4()), report_submission_id=submission_id, report_version_id=data["version"].id,
            placement_id=data["placement"].id, student_profile_id=data["student"].id, institution_id=data["institution_id"],
            academic_year_id=data["academic_year_id"], semester_number=data["student"].current_semester,
            curriculum_mapping_version_id=data["mapping"].id if data["mapping"] else None, grading_policy_id=data["policy"].id,
            status="AWAITING_APPROVAL", total_score=data["score"], final_grade=data["grade"], created_by_account_id=actor_id)
        self.db.add(item)
        await self.db.flush()
        self.db.add(OfficialInternshipResultHistory(id=str(uuid4()), result_id=item.id, actor_account_id=actor_id,
            action="PREPARED", previous_values=None, new_values={"status": item.status, "total_score": str(item.total_score), "final_grade": item.final_grade, "policy_id": item.grading_policy_id}))
        AuditService(self.db).record(actor_id, data["institution_id"], "academic_result.prepared", "official_internship_result", item.id,
            {"report_submission_id": submission_id, "policy_version": data["policy"].version_number})
        await self.db.commit()
        await self.db.refresh(item)
        return item

    async def approve(self, result_id: str, actor_id: str):
        item = await self.db.get(OfficialInternshipResult, result_id)
        if item is None:
            raise OfficialResultError(404, "Official result not found")
        await InstitutionService(self.db).require_admin(item.institution_id, actor_id)
        if item.status != "AWAITING_APPROVAL":
            raise OfficialResultError(409, "Only results awaiting approval can be approved")
        if str(item.created_by_account_id) == str(actor_id):
            raise OfficialResultError(403, "The result preparer cannot approve the same result")
        old = {"status": item.status, "total_score": str(item.total_score), "final_grade": item.final_grade}
        item.status = "APPROVED"
        item.approved_by_account_id = actor_id
        item.approved_at = datetime.now(UTC).replace(tzinfo=None)
        self.db.add(OfficialInternshipResultHistory(id=str(uuid4()), result_id=item.id, actor_account_id=actor_id,
            action="APPROVED", previous_values=old, new_values={"status": item.status, "total_score": str(item.total_score), "final_grade": item.final_grade}))
        AuditService(self.db).record(actor_id, item.institution_id, "academic_result.approved", "official_internship_result", item.id, {"status": item.status})
        await self.db.commit()
        await self.db.refresh(item)
        return item

    async def publish(self, result_id: str, actor_id: str):
        item = await self.db.get(OfficialInternshipResult, result_id)
        if item is None:
            raise OfficialResultError(404, "Official result not found")
        await InstitutionService(self.db).require_admin(item.institution_id, actor_id)
        if item.status != "APPROVED":
            raise OfficialResultError(409, "Only approved results can be published")
        if str(item.approved_by_account_id) == str(actor_id):
            raise OfficialResultError(403, "The approver cannot publish the same result")
        old = {"status": item.status, "published_at": item.published_at}
        item.status = "PUBLISHED"
        item.published_by_account_id = actor_id
        item.published_at = datetime.now(UTC).replace(tzinfo=None)
        self.db.add(OfficialInternshipResultHistory(id=str(uuid4()), result_id=item.id, actor_account_id=actor_id,
            action="PUBLISHED", previous_values=old, new_values={"status": item.status, "published_at": item.published_at.isoformat(), "total_score": str(item.total_score), "final_grade": item.final_grade}))
        AuditService(self.db).record(actor_id, item.institution_id, "academic_result.published", "official_internship_result", item.id, {"status": item.status})
        await self.db.commit()
        await self.db.refresh(item)
        return item

    async def list_mine(self, account_id: str):
        student = await self.db.scalar(select(StudentProfile).where(StudentProfile.account_id == account_id))
        if student is None:
            raise OfficialResultError(403, "Student account required")
        rows = await self.db.scalars(select(OfficialInternshipResult).where(
            OfficialInternshipResult.student_profile_id == student.id,
            OfficialInternshipResult.status == "PUBLISHED").order_by(OfficialInternshipResult.published_at.desc()))
        return list(rows.all())
