"""Blind scoring service. Identity is omitted from evaluator packet payloads."""
from datetime import UTC, datetime
from uuid import uuid4
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.academic import Account, FacultyProfile, StudentProfile, Department, School
from app.models.curriculum import LearningOutcome
from app.models.evaluation import ReportSubmission, ReportVersion
from app.models.internship import InternshipPlacement
from app.models.institutions import InstitutionMembership
from app.models.curriculum import CurriculumMappingVersion
from app.models.assessment import AssessmentRubric, AssessmentRubricCriterion, BlindAssessmentAssignment, BlindAssessmentScore, BlindAssessmentScoreRevision
from app.modules.institutions.service import InstitutionService
from app.modules.audit.service import AuditService


class BlindAssessmentError(Exception):
    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        self.message = message
        super().__init__(message)


class BlindAssessmentService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_rubric(self, institution_id: str, actor_id: str, name: str, criteria: list[dict]):
        await InstitutionService(self.db).require_admin(institution_id, actor_id)
        latest = await self.db.scalar(select(AssessmentRubric.version_number).where(
            AssessmentRubric.institution_id == institution_id, AssessmentRubric.name == name.strip()
        ).order_by(AssessmentRubric.version_number.desc()))
        rubric = AssessmentRubric(id=str(uuid4()), institution_id=institution_id, name=name.strip(),
            version_number=(latest or 0) + 1, status="DRAFT", created_by_account_id=actor_id)
        self.db.add(rubric)
        seen = set()
        for item in criteria:
            if item["code"].strip() in seen:
                raise BlindAssessmentError(422, "Rubric criterion codes must be unique")
            seen.add(item["code"].strip())
            self.db.add(AssessmentRubricCriterion(id=str(uuid4()), rubric_id=rubric.id,
                code=item["code"].strip(), title=item["title"].strip(), description=item["description"].strip(),
                minimum_score=item["minimum_score"], maximum_score=item["maximum_score"],
                weight=item["weight"], position=item["position"]))
        AuditService(self.db).record(actor_id, institution_id, "assessment.rubric_created", "assessment_rubric",
            rubric.id, {"version_number": rubric.version_number, "criterion_count": len(criteria)})
        await self.db.commit()
        await self.db.refresh(rubric)
        return rubric

    async def approve_rubric(self, rubric_id: str, actor_id: str):
        rubric = await self.db.get(AssessmentRubric, rubric_id)
        if rubric is None:
            raise BlindAssessmentError(404, "Rubric not found")
        await InstitutionService(self.db).require_admin(rubric.institution_id, actor_id)
        if rubric.status != "DRAFT":
            raise BlindAssessmentError(409, "Only draft rubrics can be approved")
        criteria = list((await self.db.scalars(select(AssessmentRubricCriterion).where(
            AssessmentRubricCriterion.rubric_id == rubric.id))).all())
        if not criteria or sum((item.weight for item in criteria), start=0) <= 0:
            raise BlindAssessmentError(422, "An approved rubric needs weighted criteria")
        rubric.status = "APPROVED"
        rubric.approved_by_account_id = actor_id
        rubric.approved_at = datetime.now(UTC).replace(tzinfo=None)
        AuditService(self.db).record(actor_id, rubric.institution_id, "assessment.rubric_approved",
            "assessment_rubric", rubric.id, {"version_number": rubric.version_number})
        await self.db.commit()
        await self.db.refresh(rubric)
        return rubric

    async def _institution_for_student(self, student: StudentProfile):
        if student.department_id:
            value = await self.db.scalar(select(School.institution_id).join(
                Department, Department.school_id == School.id).where(Department.id == student.department_id))
            if value:
                return value
        if student.cohort_id:
            from app.models.academic import Cohort, Programme
            return await self.db.scalar(select(School.institution_id).join(
                Department, Department.school_id == School.id).join(Programme, Programme.department_id == Department.id)
                .join(Cohort, Cohort.programme_id == Programme.id).where(Cohort.id == student.cohort_id))
        return None

    async def assign(self, actor_id: str, report_version_id: str, rubric_id: str, evaluator_account_id: str):
        version = await self.db.get(ReportVersion, report_version_id)
        if version is None:
            raise BlindAssessmentError(404, "Submitted version not found")
        submission = await self.db.get(ReportSubmission, version.submission_id)
        placement = await self.db.get(InternshipPlacement, submission.placement_id) if submission else None
        student = await self.db.get(StudentProfile, placement.student_id) if placement else None
        rubric = await self.db.get(AssessmentRubric, rubric_id)
        if not submission or not placement or not student or not rubric:
            raise BlindAssessmentError(404, "Assessment resource not found")
        institution_id = await self._institution_for_student(student)
        if institution_id is None or institution_id != rubric.institution_id:
            raise BlindAssessmentError(422, "Rubric and submitted version must belong to the same institution")
        await InstitutionService(self.db).require_admin(institution_id, actor_id)
        if submission.status not in {"SUBMITTED", "UNDER_EVALUATION", "APPROVED"}:
            raise BlindAssessmentError(409, "Only a submitted report can be assigned for blind assessment")
        if rubric.status != "APPROVED":
            raise BlindAssessmentError(409, "Only an approved rubric can be assigned")
        faculty = await self.db.scalar(select(FacultyProfile).where(FacultyProfile.account_id == evaluator_account_id))
        account = await self.db.get(Account, evaluator_account_id)
        if faculty is None or account is None or not account.is_active or not account.is_verified or faculty.employment_status.lower() != "active":
            raise BlindAssessmentError(422, "Evaluator must be an active, verified faculty account")
        if placement.faculty_supervisor_id == faculty.id:
            raise BlindAssessmentError(422, "Placement supervisors cannot be assigned as independent blind evaluators")
        faculty_institution = await self.db.scalar(select(School.institution_id).join(
            Department, Department.school_id == School.id).where(Department.id == faculty.department_id))
        if faculty_institution != institution_id:
            raise BlindAssessmentError(422, "Evaluator must belong to the same institution")
        assignment = BlindAssessmentAssignment(id=str(uuid4()), report_version_id=version.id, rubric_id=rubric.id,
            evaluator_account_id=evaluator_account_id, assigned_by_account_id=actor_id, status="DRAFT")
        self.db.add(assignment)
        AuditService(self.db).record(actor_id, institution_id, "assessment.blind_evaluator_assigned",
            "blind_assessment_assignment", assignment.id, {"report_version_id": version.id, "rubric_id": rubric.id})
        await self.db.commit()
        await self.db.refresh(assignment)
        return assignment

    async def list_my_assignments(self, actor_id: str):
        rows = await self.db.scalars(select(BlindAssessmentAssignment).where(
            BlindAssessmentAssignment.evaluator_account_id == actor_id).order_by(BlindAssessmentAssignment.created_at.desc()))
        result = []
        for assignment in rows.all():
            version = await self.db.get(ReportVersion, assignment.report_version_id)
            rubric = await self.db.get(AssessmentRubric, assignment.rubric_id)
            criteria = list((await self.db.scalars(select(AssessmentRubricCriterion).where(
                AssessmentRubricCriterion.rubric_id == assignment.rubric_id).order_by(AssessmentRubricCriterion.position))).all())
            scores = list((await self.db.scalars(select(BlindAssessmentScore).where(
                BlindAssessmentScore.assignment_id == assignment.id))).all())
            result.append({"id": assignment.id, "status": assignment.status, "submitted_at": assignment.submitted_at,
                "report_version_id": version.id if version else None,
                "evidence": ({"report_file_id": version.file_id, "presentation_file_id": version.presentation_file_id} if version else None),
                "rubric": {"id": rubric.id, "name": rubric.name, "version_number": rubric.version_number} if rubric else None,
                "criteria": [{"id": c.id, "code": c.code, "title": c.title, "description": c.description,
                    "minimum_score": str(c.minimum_score), "maximum_score": str(c.maximum_score), "weight": str(c.weight),
                    "position": c.position} for c in criteria],
                "scores": [{"criterion_id": s.criterion_id, "score": str(s.score), "feedback": s.feedback} for s in scores]})
        return result


    async def _assignment_institution(self, assignment: BlindAssessmentAssignment):
        version = await self.db.get(ReportVersion, assignment.report_version_id)
        submission = await self.db.get(ReportSubmission, version.submission_id) if version else None
        placement = await self.db.get(InternshipPlacement, submission.placement_id) if submission else None
        student = await self.db.get(StudentProfile, placement.student_id) if placement else None
        if student is None:
            raise BlindAssessmentError(404, "Assessment assignment not found")
        institution_id = await self._institution_for_student(student)
        if institution_id is None:
            raise BlindAssessmentError(409, "Student institution could not be established")
        return institution_id

    async def reopen(self, assignment_id: str, actor_id: str):
        assignment = await self.db.get(BlindAssessmentAssignment, assignment_id)
        if assignment is None:
            raise BlindAssessmentError(404, "Assessment assignment not found")
        institution_id = await self._assignment_institution(assignment)
        await InstitutionService(self.db).require_admin(institution_id, actor_id)
        if assignment.status != "SUBMITTED":
            raise BlindAssessmentError(409, "Only a submitted assessment can be reopened")
        old_status = assignment.status
        assignment.status = "DRAFT"
        assignment.submitted_at = None
        assignment.released_at = None
        AuditService(self.db).record(actor_id, institution_id, "assessment.blind_assessment_reopened",
            "blind_assessment_assignment", assignment.id, {"previous_status": old_status})
        await self.db.commit()
        await self.db.refresh(assignment)
        return assignment

    async def release(self, assignment_id: str, actor_id: str):
        assignment = await self.db.get(BlindAssessmentAssignment, assignment_id)
        if assignment is None:
            raise BlindAssessmentError(404, "Assessment assignment not found")
        institution_id = await self._assignment_institution(assignment)
        await InstitutionService(self.db).require_admin(institution_id, actor_id)
        if assignment.status != "SUBMITTED":
            raise BlindAssessmentError(409, "Only a submitted assessment can be released")
        if assignment.released_at is not None:
            raise BlindAssessmentError(409, "Assessment scores have already been released")
        assignment.released_at = datetime.now(UTC).replace(tzinfo=None)
        AuditService(self.db).record(actor_id, institution_id, "assessment.blind_assessment_released",
            "blind_assessment_assignment", assignment.id, {"released_at": assignment.released_at.isoformat()})
        await self.db.commit()
        await self.db.refresh(assignment)
        return assignment

    async def save_scores(self, assignment_id: str, actor_id: str, scores: list[dict], submit: bool):
        assignment = await self.db.get(BlindAssessmentAssignment, assignment_id)
        if assignment is None or str(assignment.evaluator_account_id) != str(actor_id):
            raise BlindAssessmentError(404, "Assessment assignment not found")
        if assignment.status != "DRAFT":
            raise BlindAssessmentError(409, "Submitted assessment scores are immutable; an authorized administrator must reopen them")
        criteria = list((await self.db.scalars(select(AssessmentRubricCriterion).where(
            AssessmentRubricCriterion.rubric_id == assignment.rubric_id))).all())
        by_id = {c.id: c for c in criteria}
        if len({item["criterion_id"] for item in scores}) != len(scores):
            raise BlindAssessmentError(422, "Each rubric criterion may be scored once")
        for item in scores:
            criterion = by_id.get(item["criterion_id"])
            if criterion is None:
                raise BlindAssessmentError(422, "Score criterion must belong to the assigned rubric")
            if item["score"] < criterion.minimum_score or item["score"] > criterion.maximum_score:
                raise BlindAssessmentError(422, f"Score for {criterion.code} is outside the permitted range")
        existing = {s.criterion_id: s for s in (await self.db.scalars(select(BlindAssessmentScore).where(
            BlindAssessmentScore.assignment_id == assignment.id))).all()}
        for item in scores:
            score = existing.get(item["criterion_id"])
            if score is None:
                self.db.add(BlindAssessmentScore(id=str(uuid4()), assignment_id=assignment.id,
                    criterion_id=item["criterion_id"], score=item["score"], feedback=item.get("feedback")))
            else:
                if score.score != item["score"] or score.feedback != item.get("feedback"):
                    self.db.add(BlindAssessmentScoreRevision(id=str(uuid4()), assignment_id=assignment.id,
                        criterion_id=score.criterion_id, actor_account_id=actor_id, action="CORRECTED",
                        previous_score=score.score, new_score=item["score"],
                        previous_feedback=score.feedback, new_feedback=item.get("feedback")))
                    score.score = item["score"]
                    score.feedback = item.get("feedback")
        if submit:
            supplied = set(existing) | {item["criterion_id"] for item in scores}
            if supplied != set(by_id):
                raise BlindAssessmentError(422, "Every rubric criterion must be scored before submission")
            assignment.status = "SUBMITTED"
            assignment.submitted_at = datetime.now(UTC).replace(tzinfo=None)
        await self.db.commit()
        await self.db.refresh(assignment)
        return {"id": assignment.id, "status": assignment.status, "submitted_at": assignment.submitted_at}
