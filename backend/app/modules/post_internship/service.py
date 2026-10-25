"""Policy-driven post-internship assessment use cases.

No default curriculum outcomes or grading weights are seeded. Institution administrators
must supply authoritative curriculum entries and an explicit, versioned grading policy.
"""
from __future__ import annotations

import secrets
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.academic import (
    Account, AccountRole, AcademicYear, Cohort, Department, FacultyProfile,
    Programme, Role, School, StudentProfile,
)
from app.models.evaluation import (
    BlindAssessmentAssignment, CurriculumOutcome, GriffinEvaluation, GriffinResultSnapshot,
    InternshipAcademicResult, InternshipAssessmentPolicy, InternshipCurriculumMapping,
    ReportSubmission, ReportVersion,
)
from app.models.institutions import InstitutionMembership
from app.models.internship import InternshipPlacement
from app.models.storage import StorageFile
from app.modules.audit.service import AuditService
from app.modules.institutions.service import InstitutionAccessError, InstitutionService
from app.modules.storage.service import StorageService


class PostInternshipError(Exception):
    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        self.message = message
        super().__init__(message)


def _now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


async def _student(db: AsyncSession, account_id: str) -> StudentProfile:
    item = await db.scalar(select(StudentProfile).where(StudentProfile.account_id == account_id))
    if item is None:
        raise PostInternshipError(403, "Student profile required")
    return item


async def _faculty(db: AsyncSession, account_id: str) -> FacultyProfile:
    item = await db.scalar(select(FacultyProfile).where(FacultyProfile.account_id == account_id))
    if item is None:
        raise PostInternshipError(403, "Faculty profile required")
    account = await db.get(Account, item.account_id)
    if account is None or not account.is_active or not account.is_verified:
        raise PostInternshipError(403, "An active, verified faculty account is required")
    return item


async def _programme_in_institution(db: AsyncSession, programme_id: str, institution_id: str) -> Programme:
    item = await db.scalar(
        select(Programme).join(Department, Department.id == Programme.department_id)
        .join(School, School.id == Department.school_id)
        .where(Programme.id == programme_id, School.institution_id == institution_id)
    )
    if item is None:
        raise PostInternshipError(422, "The programme does not belong to the specified institution")
    return item


async def _require_institution_admin(db: AsyncSession, institution_id: str, account_id: str) -> None:
    try:
        await InstitutionService(db).require_admin(institution_id, account_id)
    except InstitutionAccessError as exc:
        raise PostInternshipError(exc.status_code, exc.message) from None


async def _require_policy_role(
    db: AsyncSession, institution_id: str, account_id: str, role_name: str
) -> None:
    if role_name == "INSTITUTION_ADMIN":
        await _require_institution_admin(db, institution_id, account_id)
        return
    has_role = await db.scalar(
        select(AccountRole.account_id).join(Role, Role.id == AccountRole.role_id)
        .where(
            AccountRole.account_id == account_id,
            AccountRole.institution_id == institution_id,
            Role.name == role_name,
        )
    )
    if has_role is None:
        raise PostInternshipError(403, f"Institution-scoped {role_name} approval permission is required")


async def _submission_version(db: AsyncSession, submission_id: str, version_id: str | None = None):
    submission = await db.get(ReportSubmission, submission_id)
    if submission is None:
        raise PostInternshipError(404, "Report submission not found")
    if version_id is not None:
        version = await db.get(ReportVersion, version_id)
        if version is None or version.submission_id != submission.id:
            raise PostInternshipError(404, "Report version not found")
    else:
        version = await db.scalar(select(ReportVersion).where(
            ReportVersion.submission_id == submission.id,
            ReportVersion.version_number == submission.latest_version_number,
        ))
    if version is None:
        raise PostInternshipError(409, "A persisted report version is required")
    return submission, version


async def _placement_for_submission(db: AsyncSession, submission: ReportSubmission) -> InternshipPlacement:
    placement = await db.get(InternshipPlacement, submission.placement_id)
    if placement is None:
        raise PostInternshipError(404, "Internship placement not found")
    return placement


async def _submission_context(submission: ReportSubmission) -> tuple[str, str, int]:
    if not submission.institution_id or not submission.programme_id or not submission.academic_semester:
        raise PostInternshipError(
            409,
            "This legacy submission has no immutable academic-context snapshot. Create a new submission to use curriculum mapping and final results.",
        )
    return submission.institution_id, submission.programme_id, submission.academic_semester


async def _is_institution_admin(db: AsyncSession, institution_id: str, account_id: str) -> bool:
    member = await db.scalar(select(InstitutionMembership.id).where(
        InstitutionMembership.institution_id == institution_id,
        InstitutionMembership.account_id == account_id,
        InstitutionMembership.role == "INSTITUTION_ADMIN",
        InstitutionMembership.status == "ACTIVE",
    ))
    return member is not None


async def _can_read_submission(db: AsyncSession, submission: ReportSubmission, account_id: str) -> bool:
    student_id = await db.scalar(select(StudentProfile.id).where(StudentProfile.account_id == account_id))
    if student_id is not None:
        placement = await _placement_for_submission(db, submission)
        if placement.student_id == student_id:
            return True
    faculty_id = await db.scalar(select(FacultyProfile.id).where(FacultyProfile.account_id == account_id))
    if faculty_id is not None:
        placement = await _placement_for_submission(db, submission)
        if placement.faculty_supervisor_id == faculty_id:
            return True
    if submission.institution_id:
        return await _is_institution_admin(db, submission.institution_id, account_id)
    return False


async def _require_supervisor_or_admin(db: AsyncSession, submission: ReportSubmission, account_id: str) -> None:
    placement = await _placement_for_submission(db, submission)
    faculty_id = await db.scalar(select(FacultyProfile.id).where(FacultyProfile.account_id == account_id))
    if faculty_id is not None and placement.faculty_supervisor_id == faculty_id:
        return
    if submission.institution_id and await _is_institution_admin(db, submission.institution_id, account_id):
        await _require_institution_admin(db, submission.institution_id, account_id)
        return
    raise PostInternshipError(403, "Only the assigned supervisor or an active institution administrator may manage this workflow")


def _policy_snapshot(policy: InternshipAssessmentPolicy) -> dict:
    return {
        "policy_id": policy.id,
        "policy_version": policy.version,
        "criteria": policy.criteria_json,
        "component_weights": policy.component_weights_json,
        "grade_bands": policy.grade_bands_json,
        "passing_score": float(policy.passing_score),
        "final_approver_role": policy.final_approver_role,
        "required_evaluator_count": policy.required_evaluator_count,
        "show_curriculum_mapping_to_evaluator": policy.show_curriculum_mapping_to_evaluator,
    }


def _policy_json(policy: InternshipAssessmentPolicy) -> dict:
    return {
        "id": policy.id, "institution_id": policy.institution_id, "programme_id": policy.programme_id,
        "version": policy.version, "name": policy.name, "criteria": policy.criteria_json,
        "component_weights": policy.component_weights_json, "grade_bands": policy.grade_bands_json,
        "passing_score": float(policy.passing_score), "final_approver_role": policy.final_approver_role,
        "required_evaluator_count": policy.required_evaluator_count,
        "show_curriculum_mapping_to_evaluator": policy.show_curriculum_mapping_to_evaluator,
        "is_active": policy.is_active, "created_at": policy.created_at,
    }


def _outcome_json(outcome: CurriculumOutcome) -> dict:
    return {
        "id": outcome.id, "institution_id": outcome.institution_id, "programme_id": outcome.programme_id,
        "semester": outcome.semester, "outcome_code": outcome.outcome_code, "title": outcome.title,
        "expected_competency": outcome.expected_competency, "source_reference": outcome.source_reference,
        "is_active": outcome.is_active,
    }


def _mapping_json(mapping: InternshipCurriculumMapping, outcome: CurriculumOutcome) -> dict:
    return {
        "id": mapping.id, "outcome_id": outcome.id, "outcome_code": outcome.outcome_code,
        "title": outcome.title, "expected_competency": outcome.expected_competency,
        "source_reference": outcome.source_reference, "status": mapping.status,
        "evidence_reference": mapping.evidence_reference, "confidence": float(mapping.confidence) if mapping.confidence is not None else None,
        "reviewer_notes": mapping.reviewer_notes, "reviewed_at": mapping.reviewed_at,
    }


class PostInternshipService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_policy(self, actor_id: str, data: dict) -> InternshipAssessmentPolicy:
        institution_id = data["institution_id"]
        programme_id = data["programme_id"]
        await _require_institution_admin(self.db, institution_id, actor_id)
        await _programme_in_institution(self.db, programme_id, institution_id)
        version = (await self.db.scalar(select(func.max(InternshipAssessmentPolicy.version).where(
            InternshipAssessmentPolicy.institution_id == institution_id,
            InternshipAssessmentPolicy.programme_id == programme_id,
        ))) or 0) + 1
        active = (await self.db.scalars(select(InternshipAssessmentPolicy).where(
            InternshipAssessmentPolicy.institution_id == institution_id,
            InternshipAssessmentPolicy.programme_id == programme_id,
            InternshipAssessmentPolicy.is_active.is_(True),
        ))).all()
        for old in active:
            old.is_active = False
        policy = InternshipAssessmentPolicy(
            id=str(uuid4()), institution_id=institution_id, programme_id=programme_id, version=version,
            name=data["name"].strip(), criteria_json=[item.model_dump() if hasattr(item, "model_dump") else item for item in data["criteria"]],
            component_weights_json=data["component_weights"],
            grade_bands_json=[item.model_dump() if hasattr(item, "model_dump") else item for item in data["grade_bands"]],
            passing_score=Decimal(str(data["passing_score"])), final_approver_role=data["final_approver_role"],
            required_evaluator_count=data["required_evaluator_count"],
            show_curriculum_mapping_to_evaluator=data["show_curriculum_mapping_to_evaluator"],
            is_active=True, created_by_account_id=actor_id,
        )
        self.db.add(policy)
        AuditService(self.db).record(actor_id, institution_id, "internship_assessment.policy_created",
            "internship_assessment_policy", policy.id, {"version": version, "programme_id": programme_id})
        try:
            await self.db.commit()
        except Exception:
            await self.db.rollback()
            raise
        await self.db.refresh(policy)
        return policy

    async def list_policies(self, institution_id: str, programme_id: str, actor_id: str) -> list[InternshipAssessmentPolicy]:
        await _require_institution_admin(self.db, institution_id, actor_id)
        await _programme_in_institution(self.db, programme_id, institution_id)
        result = await self.db.scalars(select(InternshipAssessmentPolicy).where(
            InternshipAssessmentPolicy.institution_id == institution_id,
            InternshipAssessmentPolicy.programme_id == programme_id,
        ).order_by(InternshipAssessmentPolicy.version.desc()))
        return list(result.all())

    async def create_outcome(self, actor_id: str, data: dict) -> CurriculumOutcome:
        await _require_institution_admin(self.db, data["institution_id"], actor_id)
        await _programme_in_institution(self.db, data["programme_id"], data["institution_id"])
        item = CurriculumOutcome(
            id=str(uuid4()), institution_id=data["institution_id"], programme_id=data["programme_id"],
            semester=data["semester"], outcome_code=data["outcome_code"].strip(),
            title=data["title"].strip(), expected_competency=data["expected_competency"].strip(),
            source_reference=data["source_reference"].strip(), created_by_account_id=actor_id, is_active=True,
        )
        self.db.add(item)
        AuditService(self.db).record(actor_id, data["institution_id"], "curriculum_outcome.created",
            "curriculum_outcome", item.id, {"programme_id": item.programme_id, "semester": item.semester, "outcome_code": item.outcome_code})
        try:
            await self.db.commit()
        except IntegrityError:
            await self.db.rollback()
            raise PostInternshipError(409, "This curriculum outcome code already exists for the programme and semester") from None
        await self.db.refresh(item)
        return item

    async def list_mappings(self, submission_id: str, account_id: str) -> dict:
        submission, version = await _submission_version(self.db, submission_id)
        if not await _can_read_submission(self.db, submission, account_id):
            raise PostInternshipError(404, "Report submission not found")
        if not submission.institution_id or not submission.programme_id or not submission.academic_semester:
            return {"items": [], "catalogue_available": False, "message": "Academic context is not snapshotted for this legacy submission."}
        outcomes = list((await self.db.scalars(select(CurriculumOutcome).where(
            CurriculumOutcome.institution_id == submission.institution_id,
            CurriculumOutcome.programme_id == submission.programme_id,
            CurriculumOutcome.semester == submission.academic_semester,
            CurriculumOutcome.is_active.is_(True),
        ).order_by(CurriculumOutcome.outcome_code))).all())
        mappings = (await self.db.scalars(select(InternshipCurriculumMapping).where(
            InternshipCurriculumMapping.report_version_id == version.id,
        ))).all()
        by_outcome = {item.outcome_id: item for item in mappings}
        return {
            "items": [
                {"outcome": _outcome_json(outcome),
                 "mapping": _mapping_json(by_outcome[outcome.id], outcome) if outcome.id in by_outcome else None}
                for outcome in outcomes
            ],
            "catalogue_available": bool(outcomes),
            "message": None if outcomes else "No curriculum outcomes are configured for this programme and semester. An institution administrator must load the approved curriculum first.",
            "report_version_id": version.id,
        }

    async def save_mappings(self, submission_id: str, actor_id: str, items: list[dict]) -> dict:
        submission, version = await _submission_version(self.db, submission_id)
        await _require_supervisor_or_admin(self.db, submission, actor_id)
        institution_id, programme_id, semester = await _submission_context(submission)
        allowed_outcomes = set((await self.db.scalars(select(CurriculumOutcome.id).where(
            CurriculumOutcome.institution_id == institution_id,
            CurriculumOutcome.programme_id == programme_id,
            CurriculumOutcome.semester == semester,
            CurriculumOutcome.is_active.is_(True),
        ))).all())
        for item in items:
            if item["outcome_id"] not in allowed_outcomes:
                raise PostInternshipError(422, "Every mapped outcome must belong to the submission's persisted programme and semester")
            if item["status"] in {"MAPPED", "PARTIALLY_MAPPED"} and not (item.get("evidence_reference") or "").strip():
                raise PostInternshipError(422, "Evidence reference is required for mapped or partially mapped outcomes")
        existing = (await self.db.scalars(select(InternshipCurriculumMapping).where(
            InternshipCurriculumMapping.report_version_id == version.id,
        ))).all()
        by_outcome = {item.outcome_id: item for item in existing}
        now = _now()
        for item in items:
            mapping = by_outcome.get(item["outcome_id"])
            if mapping is None:
                mapping = InternshipCurriculumMapping(
                    id=str(uuid4()), report_version_id=version.id, outcome_id=item["outcome_id"],
                    created_by_account_id=actor_id, change_history_json=[],
                )
                self.db.add(mapping)
            else:
                mapping.change_history_json = list(mapping.change_history_json or []) + [{
                    "status": mapping.status, "evidence_reference": mapping.evidence_reference,
                    "confidence": float(mapping.confidence) if mapping.confidence is not None else None,
                    "reviewer_notes": mapping.reviewer_notes,
                    "reviewed_by_account_id": mapping.reviewed_by_account_id,
                    "reviewed_at": mapping.reviewed_at.isoformat() if mapping.reviewed_at else None,
                    "changed_at": now.isoformat(),
                }]
            mapping.status = item["status"]
            mapping.evidence_reference = (item.get("evidence_reference") or "").strip() or None
            mapping.confidence = Decimal(str(item["confidence"])) if item.get("confidence") is not None else None
            mapping.reviewer_notes = (item.get("reviewer_notes") or "").strip() or None
            mapping.reviewed_by_account_id = actor_id
            mapping.reviewed_at = now
            mapping.updated_at = now
        AuditService(self.db).record(actor_id, institution_id, "internship_curriculum.mapping_reviewed",
            "report_version", version.id, {"updated_outcome_count": len(items)})
        await self.db.commit()
        return await self.list_mappings(submission_id, actor_id)

    async def assign_assessment(self, actor_id: str, data: dict) -> BlindAssessmentAssignment:
        version = await self.db.get(ReportVersion, data["report_version_id"])
        if version is None:
            raise PostInternshipError(404, "Report version not found")
        submission = await self.db.get(ReportSubmission, version.submission_id)
        if submission is None:
            raise PostInternshipError(404, "Report submission not found")
        institution_id, programme_id, _semester = await _submission_context(submission)
        if not version.presentation_file_id:
            raise PostInternshipError(409, "A report PDF and presentation PPTX are both required before blind assessment")
        report_file = await self.db.get(StorageFile, version.file_id)
        presentation_file = await self.db.get(StorageFile, version.presentation_file_id)
        if report_file is None or report_file.mime_type != "application/pdf":
            raise PostInternshipError(415, "The blind assessment report must be a PDF file")
        if presentation_file is None or presentation_file.mime_type != "application/vnd.openxmlformats-officedocument.presentationml.presentation":
            raise PostInternshipError(415, "The blind assessment presentation must be a PowerPoint PPTX file")
        placement = await _placement_for_submission(self.db, submission)
        faculty_actor = await self.db.scalar(select(FacultyProfile).where(FacultyProfile.account_id == actor_id))
        supervisor_authorized = faculty_actor is not None and placement.faculty_supervisor_id == faculty_actor.id
        admin_authorized = await _is_institution_admin(self.db, institution_id, actor_id)
        if not supervisor_authorized and not admin_authorized:
            raise PostInternshipError(403, "Only the assigned placement supervisor or an institution administrator may assign a blind evaluator")
        if admin_authorized:
            await _require_institution_admin(self.db, institution_id, actor_id)
        if submission.status not in {"SUBMITTED", "UNDER_EVALUATION", "APPROVED"}:
            raise PostInternshipError(409, "Only a submitted report can be assigned for blind assessment")
        policy = await self.db.get(InternshipAssessmentPolicy, data["policy_id"])
        if policy is None or not policy.is_active or policy.institution_id != institution_id or policy.programme_id != programme_id:
            raise PostInternshipError(422, "The policy must be active and match the submission's institution and programme")
        evaluator = await self.db.get(FacultyProfile, data["evaluator_faculty_id"])
        if evaluator is None:
            raise PostInternshipError(422, "The selected evaluator is not a faculty member")
        if placement.faculty_supervisor_id == evaluator.id:
            raise PostInternshipError(422, "The placement supervisor cannot be assigned as the blind evaluator")
        evaluator_account = await self.db.get(Account, evaluator.account_id)
        if evaluator_account is None or not evaluator_account.is_active or not evaluator_account.is_verified:
            raise PostInternshipError(422, "The selected evaluator account must be active and verified")
        existing = await self.db.scalar(select(BlindAssessmentAssignment.id).where(
            BlindAssessmentAssignment.report_version_id == version.id,
            BlindAssessmentAssignment.evaluator_faculty_id == evaluator.id,
        ))
        if existing:
            raise PostInternshipError(409, "This faculty evaluator is already assigned to the report version")
        if await self.db.scalar(select(BlindAssessmentAssignment.id).where(
            BlindAssessmentAssignment.report_version_id == version.id,
            BlindAssessmentAssignment.status == "SUBMITTED",
            BlindAssessmentAssignment.policy_id != policy.id,
        )):
            raise PostInternshipError(409, "All independent assessments for a report version must use the same policy version")
        assignment = BlindAssessmentAssignment(
            id=str(uuid4()), packet_code=secrets.token_hex(5).upper(), report_version_id=version.id,
            institution_id=institution_id, evaluator_faculty_id=evaluator.id, policy_id=policy.id,
            assigned_by_account_id=actor_id, rubric_snapshot_json=_policy_snapshot(policy), status="ASSIGNED",
        )
        self.db.add(assignment)
        AuditService(self.db).record(actor_id, institution_id, "internship_assessment.blind_assignment_created",
            "blind_assessment_assignment", assignment.id, {"report_version_id": version.id, "policy_version": policy.version})
        try:
            await self.db.commit()
        except IntegrityError:
            await self.db.rollback()
            raise PostInternshipError(409, "An equivalent evaluator assignment already exists") from None
        await self.db.refresh(assignment)
        return assignment

    async def list_assessments_for_faculty(self, account_id: str) -> list[BlindAssessmentAssignment]:
        faculty = await _faculty(self.db, account_id)
        result = await self.db.scalars(select(BlindAssessmentAssignment).where(
            BlindAssessmentAssignment.evaluator_faculty_id == faculty.id,
        ).order_by(BlindAssessmentAssignment.assigned_at.desc()))
        return list(result.all())

    async def _owned_assignment(self, assignment_id: str, account_id: str) -> tuple[BlindAssessmentAssignment, ReportVersion, ReportSubmission]:
        faculty = await _faculty(self.db, account_id)
        assignment = await self.db.get(BlindAssessmentAssignment, assignment_id)
        if assignment is None or assignment.evaluator_faculty_id != faculty.id:
            raise PostInternshipError(404, "Blind assessment assignment not found")
        version = await self.db.get(ReportVersion, assignment.report_version_id)
        submission = await self.db.get(ReportSubmission, version.submission_id) if version else None
        if version is None or submission is None:
            raise PostInternshipError(404, "Assessment packet not found")
        return assignment, version, submission

    async def assessment_packet(self, assignment_id: str, account_id: str) -> dict:
        assignment, version, _submission = await self._owned_assignment(assignment_id, account_id)
        packet = {
            "id": assignment.id, "packet_code": assignment.packet_code, "status": assignment.status,
            "version_number": version.version_number, "assigned_at": assignment.assigned_at,
            "rubric": assignment.rubric_snapshot_json.get("criteria", []),
            "scores": assignment.scores_json or {}, "evaluator_comments": assignment.evaluator_comments,
            "report_download_url": f"/internship-assessments/assignments/{assignment.id}/files/report",
            "presentation_download_url": f"/internship-assessments/assignments/{assignment.id}/files/presentation" if version.presentation_file_id else None,
            "curriculum_mapping": [],
            "blinding_notice": "Direct account/profile identifiers are omitted. Submitted documents can still identify their author through content or metadata.",
        }
        if assignment.rubric_snapshot_json.get("show_curriculum_mapping_to_evaluator"):
            mappings = (await self.db.scalars(select(InternshipCurriculumMapping).where(
                InternshipCurriculumMapping.report_version_id == version.id,
                InternshipCurriculumMapping.reviewed_at.is_not(None),
            ))).all()
            for mapping in mappings:
                outcome = await self.db.get(CurriculumOutcome, mapping.outcome_id)
                if outcome is not None:
                    packet["curriculum_mapping"].append({
                        "outcome_code": outcome.outcome_code, "title": outcome.title,
                        "expected_competency": outcome.expected_competency, "status": mapping.status,
                        "evidence_reference": mapping.evidence_reference,
                    })
        return packet

    async def assessment_file(self, assignment_id: str, account_id: str, kind: str):
        assignment, version, _submission = await self._owned_assignment(assignment_id, account_id)
        if kind == "report":
            file_id = version.file_id
            generic_name = "assessment-report"
        elif kind == "presentation" and version.presentation_file_id:
            file_id = version.presentation_file_id
            generic_name = "assessment-presentation"
        else:
            raise PostInternshipError(404, "Assessment file not found")
        item = await self.db.get(StorageFile, file_id)
        expected_mime = "application/pdf" if kind == "report" else "application/vnd.openxmlformats-officedocument.presentationml.presentation"
        if item is None or item.mime_type != expected_mime:
            raise PostInternshipError(404, "Assessment file not found")
        path = (StorageService(self.db).root / item.file_path).resolve()
        root = StorageService(self.db).root
        if root not in path.parents or not path.is_file():
            raise PostInternshipError(404, "Assessment file not found")
        AuditService(self.db).record(account_id, assignment.institution_id, "internship_assessment.blind_file_downloaded",
            "blind_assessment_assignment", assignment.id, {"file_kind": kind})
        await self.db.commit()
        suffix = ".pdf" if kind == "report" else ".pptx"
        return item, path, generic_name + suffix

    async def save_scores(self, assignment_id: str, account_id: str, data: dict, submit: bool) -> BlindAssessmentAssignment:
        assignment, _version, _submission = await self._owned_assignment(assignment_id, account_id)
        if assignment.status == "SUBMITTED":
            raise PostInternshipError(409, "A submitted blind assessment is immutable")
        rubric = assignment.rubric_snapshot_json.get("criteria", [])
        rubric_by_key = {item["key"]: item for item in rubric}
        scores = data["scores"]
        if any(key not in rubric_by_key for key in scores):
            raise PostInternshipError(422, "Scores may contain only criteria in the assigned rubric snapshot")
        for key, score in scores.items():
            spec = rubric_by_key[key]
            numeric = float(score["score"])
            if numeric < 0 or numeric > float(spec["max_score"]):
                raise PostInternshipError(422, f"Score for {spec['label']} must be between 0 and {spec['max_score']}")
            if submit and spec.get("require_comment") and not (score.get("comment") or "").strip():
                raise PostInternshipError(422, f"A comment is required for {spec['label']}")
        if submit and set(scores) != set(rubric_by_key):
            missing = sorted(set(rubric_by_key) - set(scores))
            raise PostInternshipError(422, "Every rubric criterion must be scored before submission: " + ", ".join(missing))
        assignment.scores_json = {
            key: {"score": float(value["score"]), "comment": (value.get("comment") or "").strip() or None}
            for key, value in scores.items()
        }
        assignment.evaluator_comments = (data.get("evaluator_comments") or "").strip() or None
        assignment.total_score = sum((Decimal(str(v["score"])) for v in assignment.scores_json.values()), Decimal("0"))
        if submit:
            assignment.status = "SUBMITTED"
            assignment.submitted_at = _now()
        else:
            assignment.status = "DRAFT"
        AuditService(self.db).record(account_id, assignment.institution_id,
            "internship_assessment.blind_score_submitted" if submit else "internship_assessment.blind_score_drafted",
            "blind_assessment_assignment", assignment.id,
            {"status": assignment.status, "criterion_count": len(assignment.scores_json)})
        await self.db.commit()
        await self.db.refresh(assignment)
        return assignment

    async def _preview(self, submission_id: str, actor_id: str) -> dict:
        submission, version = await _submission_version(self.db, submission_id)
        await _require_supervisor_or_admin(self.db, submission, actor_id)
        blockers: list[str] = []
        if not version.presentation_file_id:
            blockers.append("A PowerPoint presentation must be attached to this report version.")
        if not version.presentation_file_id:
            blockers.append("A PowerPoint presentation must be attached to this report version.")
        if submission.status != "APPROVED":
            blockers.append("The placement supervisor must approve the report submission.")
        if not submission.institution_id or not submission.programme_id or not submission.academic_semester:
            blockers.append("The submission does not have a complete immutable academic-context snapshot.")
            return {"ready": False, "blockers": blockers, "submission_id": submission.id, "report_version_id": version.id, "components": {}}
        policy_result = await self.db.scalars(select(InternshipAssessmentPolicy).where(
            InternshipAssessmentPolicy.institution_id == submission.institution_id,
            InternshipAssessmentPolicy.programme_id == submission.programme_id,
        ).order_by(InternshipAssessmentPolicy.version.desc()))
        all_policies = list(policy_result.all())
        assignments = list((await self.db.scalars(select(BlindAssessmentAssignment).where(
            BlindAssessmentAssignment.report_version_id == version.id,
        ).order_by(BlindAssessmentAssignment.assigned_at))).all())
        policy_id = assignments[0].policy_id if assignments else (all_policies[0].id if all_policies else None)
        policy = await self.db.get(InternshipAssessmentPolicy, policy_id) if policy_id else None
        if policy is None:
            blockers.append("No institution-approved grading policy exists for this programme.")
            return {"ready": False, "blockers": blockers, "submission_id": submission.id, "report_version_id": version.id, "components": {}}
        if any(item.policy_id != policy.id for item in assignments):
            blockers.append("Independent assessments use different policy versions.")
        required = int(policy.required_evaluator_count)
        submitted = [item for item in assignments if item.status == "SUBMITTED" and item.policy_id == policy.id]
        if len(submitted) != required:
            blockers.append(f"Exactly {required} submitted blind assessment(s) are required; {len(submitted)} are available.")
        faculty_percent = None
        if len(submitted) == required:
            maximum = sum(Decimal(str(item["max_score"])) for item in policy.criteria_json)
            if maximum <= 0:
                blockers.append("The configured rubric has no positive maximum score.")
            else:
                percentages = []
                for item in submitted:
                    score_total = sum((Decimal(str(v["score"])) for v in (item.scores_json or {}).values()), Decimal("0"))
                    percentages.append(float((score_total / maximum) * Decimal("100")))
                faculty_percent = sum(percentages) / len(percentages)

        outcomes = list((await self.db.scalars(select(CurriculumOutcome).where(
            CurriculumOutcome.institution_id == submission.institution_id,
            CurriculumOutcome.programme_id == submission.programme_id,
            CurriculumOutcome.semester == submission.academic_semester,
            CurriculumOutcome.is_active.is_(True),
        ))).all())
        curriculum_percent = None
        if not outcomes:
            blockers.append("No approved curriculum outcomes are configured for the submission's programme and semester.")
        else:
            mappings = list((await self.db.scalars(select(InternshipCurriculumMapping).where(
                InternshipCurriculumMapping.report_version_id == version.id,
            ))).all())
            mapping_by_outcome = {item.outcome_id: item for item in mappings}
            missing = [item for item in outcomes if item.id not in mapping_by_outcome]
            if missing:
                blockers.append(f"{len(missing)} curriculum outcome(s) have not been mapped or reviewed.")
            present = [mapping_by_outcome[item.id] for item in outcomes if item.id in mapping_by_outcome]
            if any(item.status == "REVIEW_REQUIRED" for item in present):
                blockers.append("One or more curriculum mappings still require review.")
            if len(missing) == 0 and not any(item.status == "REVIEW_REQUIRED" for item in present):
                score_sum = sum(
                    1.0 if item.status == "MAPPED" else 0.5 if item.status == "PARTIALLY_MAPPED" else 0.0
                    for item in present
                )
                curriculum_percent = (score_sum / len(outcomes)) * 100.0

        evaluations = list((await self.db.scalars(select(GriffinEvaluation).where(
            GriffinEvaluation.report_version_id == version.id,
            GriffinEvaluation.current_status == "COMPLETED",
        ).order_by(GriffinEvaluation.created_at.desc()))).all())
        griffin_percent = None
        if not evaluations:
            blockers.append("A validated, completed Griffin result for this exact report version is required.")
        else:
            snapshot = await self.db.scalar(select(GriffinResultSnapshot).where(
                GriffinResultSnapshot.griffin_evaluation_id == evaluations[0].id,
            ))
            if snapshot is None:
                blockers.append("Griffin has no validated result snapshot for this report version.")
            else:
                score = float(snapshot.alignment_score)
                if not 0 <= score <= 100:
                    blockers.append("The stored Griffin alignment score is outside the expected 0–100 range.")
                else:
                    griffin_percent = score

        components = {"griffin": griffin_percent, "curriculum": curriculum_percent, "faculty": faculty_percent}
        weighted_total = None
        grade = None
        if all(value is not None for value in components.values()):
            weights = policy.component_weights_json
            weighted_total = round(sum(components[name] * float(weights[name]) / 100.0 for name in components), 2)
            matching = [band for band in policy.grade_bands_json if float(band["min_score"]) <= weighted_total <= float(band["max_score"])]
            if not matching:
                blockers.append("The result score is not covered by any configured grade band.")
            else:
                grade = matching[0]["grade"]
        else:
            blockers.append("The final score cannot be calculated until every required component is validated.")
        return {
            "ready": not blockers, "blockers": blockers, "submission_id": submission.id,
            "report_version_id": version.id, "policy_id": policy.id, "policy_version": policy.version,
            "components": components, "component_weights": policy.component_weights_json,
            "weighted_total": weighted_total, "grade": grade,
            "passing_score": float(policy.passing_score),
            "proposed_outcome": "PASS" if weighted_total is not None and weighted_total >= float(policy.passing_score) else "NOT_PASS" if weighted_total is not None else None,
        }

    async def result_preview(self, submission_id: str, actor_id: str) -> dict:
        return await self._preview(submission_id, actor_id)

    async def finalize_result(self, submission_id: str, actor_id: str) -> InternshipAcademicResult:
        preview = await self._preview(submission_id, actor_id)
        if not preview["ready"]:
            raise PostInternshipError(409, "Result cannot be finalized: " + " ".join(preview["blockers"]))
        submission, version = await _submission_version(self.db, submission_id, preview["report_version_id"])
        policy = await self.db.get(InternshipAssessmentPolicy, preview["policy_id"])
        if policy is None:
            raise PostInternshipError(409, "Assessment policy is unavailable")
        await _require_policy_role(self.db, policy.institution_id, actor_id, policy.final_approver_role)
        existing = await self.db.scalar(select(InternshipAcademicResult).where(
            InternshipAcademicResult.report_submission_id == submission.id,
            InternshipAcademicResult.report_version_id == version.id,
            InternshipAcademicResult.status.in_(("FINALIZED", "PUBLISHED")),
        ).order_by(InternshipAcademicResult.revision_number.desc()))
        if existing is not None:
            return existing
        placement = await _placement_for_submission(self.db, submission)
        student_profile = await self.db.get(StudentProfile, placement.student_id)
        if student_profile is None:
            raise PostInternshipError(409, "Canonical student profile is unavailable")
        if not submission.programme_id or not submission.academic_semester or not submission.institution_id:
            raise PostInternshipError(409, "Academic context snapshot is incomplete")
        latest = await self.db.scalar(select(InternshipAcademicResult).where(
            InternshipAcademicResult.report_submission_id == submission.id,
        ).order_by(InternshipAcademicResult.revision_number.desc()))
        revision = (latest.revision_number if latest else 0) + 1
        result = InternshipAcademicResult(
            id=str(uuid4()), report_submission_id=submission.id, report_version_id=version.id,
            student_profile_id=student_profile.id, institution_id=submission.institution_id,
            programme_id=submission.programme_id, cohort_id=submission.cohort_id,
            academic_year_id=submission.academic_year_id, academic_semester=submission.academic_semester,
            revision_number=revision, previous_result_id=latest.id if latest else None, policy_id=policy.id,
            component_breakdown_json={
                "components": preview["components"], "weights": preview["component_weights"],
                "policy_version": preview["policy_version"], "passing_score": preview["passing_score"],
                "outcome": preview["proposed_outcome"],
            },
            total_score=Decimal(str(preview["weighted_total"])), grade=preview["grade"], status="FINALIZED",
            finalized_by_account_id=actor_id, finalized_at=_now(),
        )
        self.db.add(result)
        AuditService(self.db).record(actor_id, submission.institution_id, "internship_assessment.result_finalized",
            "internship_academic_result", result.id, {"revision_number": revision, "report_version_id": version.id, "policy_version": policy.version})
        try:
            await self.db.commit()
        except IntegrityError:
            await self.db.rollback()
            existing = await self.db.scalar(select(InternshipAcademicResult).where(
                InternshipAcademicResult.report_submission_id == submission.id,
                InternshipAcademicResult.report_version_id == version.id,
                InternshipAcademicResult.status.in_(("FINALIZED", "PUBLISHED")),
            ).order_by(InternshipAcademicResult.revision_number.desc()))
            if existing is not None:
                return existing
            raise PostInternshipError(409, "Concurrent result finalization conflict; reload the result preview") from None
        await self.db.refresh(result)
        return result

    async def publish_result(self, result_id: str, actor_id: str) -> InternshipAcademicResult:
        result = await self.db.get(InternshipAcademicResult, result_id)
        if result is None:
            raise PostInternshipError(404, "Academic result not found")
        policy = await self.db.get(InternshipAssessmentPolicy, result.policy_id)
        if policy is None:
            raise PostInternshipError(409, "The result's grading policy is unavailable")
        await _require_policy_role(self.db, result.institution_id, actor_id, policy.final_approver_role)
        if result.status == "PUBLISHED":
            return result
        if result.status != "FINALIZED":
            raise PostInternshipError(409, "Only finalized results may be published")
        result.status = "PUBLISHED"
        result.published_by_account_id = actor_id
        result.published_at = _now()
        AuditService(self.db).record(actor_id, result.institution_id, "internship_assessment.result_published",
            "internship_academic_result", result.id, {"revision_number": result.revision_number})
        await self.db.commit()
        await self.db.refresh(result)
        return result

    def _result_json(self, result: InternshipAcademicResult, title: str | None = None) -> dict:
        return {
            "id": result.id, "report_submission_id": result.report_submission_id, "report_version_id": result.report_version_id,
            "title": title, "semester": result.academic_semester, "academic_year_id": result.academic_year_id,
            "revision_number": result.revision_number, "component_breakdown": result.component_breakdown_json,
            "total_score": float(result.total_score), "grade": result.grade, "status": result.status,
            "finalized_at": result.finalized_at, "published_at": result.published_at,
        }

    async def student_results(self, account_id: str) -> list[dict]:
        student = await _student(self.db, account_id)
        result_rows = (await self.db.execute(
            select(InternshipAcademicResult, ReportSubmission.title)
            .join(ReportSubmission, ReportSubmission.id == InternshipAcademicResult.report_submission_id)
            .where(InternshipAcademicResult.student_profile_id == student.id, InternshipAcademicResult.status == "PUBLISHED")
            .order_by(InternshipAcademicResult.academic_semester, InternshipAcademicResult.published_at)
        )).all()
        return [self._result_json(result, title) for result, title in result_rows]

    async def supervised_students(self, account_id: str) -> list[dict]:
        """Expose identity only for students with a persisted placement supervised by this faculty member."""
        faculty = await _faculty(self.db, account_id)
        rows = (await self.db.execute(
            select(StudentProfile, Account)
            .join(InternshipPlacement, InternshipPlacement.student_id == StudentProfile.id)
            .join(Account, Account.id == StudentProfile.account_id)
            .where(InternshipPlacement.faculty_supervisor_id == faculty.id)
            .order_by(Account.full_name, StudentProfile.enrollment_number)
        )).all()
        by_id: dict[int, dict] = {}
        for student, account in rows:
            item = by_id.setdefault(student.id, {
                "student_profile_id": student.id,
                "full_name": account.full_name,
                "enrollment_number": student.enrollment_number,
                "current_semester": student.current_semester,
                "programme_id": student.programme_id,
            })
            del item
        return list(by_id.values())

    async def faculty_student_results(self, student_profile_id: int, account_id: str) -> list[dict]:
        faculty = await _faculty(self.db, account_id)
        supervised = await self.db.scalar(select(InternshipPlacement.id).where(
            InternshipPlacement.student_id == student_profile_id,
            InternshipPlacement.faculty_supervisor_id == faculty.id,
        ))
        if supervised is None:
            raise PostInternshipError(404, "Student result history not found")
        supervised_submission_ids = select(ReportSubmission.id).join(
            InternshipPlacement, InternshipPlacement.id == ReportSubmission.placement_id
        ).where(
            InternshipPlacement.student_id == student_profile_id,
            InternshipPlacement.faculty_supervisor_id == faculty.id,
        )
        rows = (await self.db.execute(
            select(InternshipAcademicResult, ReportSubmission.title)
            .join(ReportSubmission, ReportSubmission.id == InternshipAcademicResult.report_submission_id)
            .where(
                InternshipAcademicResult.student_profile_id == student_profile_id,
                InternshipAcademicResult.status == "PUBLISHED",
                InternshipAcademicResult.report_submission_id.in_(supervised_submission_ids),
            )
            .order_by(InternshipAcademicResult.academic_semester, InternshipAcademicResult.published_at)
        )).all()
        return [self._result_json(result, title) for result, title in rows]

    async def student_progress(self, submission_id: str, account_id: str) -> dict:
        submission, version = await _submission_version(self.db, submission_id)
        if not await _can_read_submission(self.db, submission, account_id):
            raise PostInternshipError(404, "Report submission not found")
        latest_eval = await self.db.scalar(select(GriffinEvaluation).where(
            GriffinEvaluation.report_version_id == version.id,
        ).order_by(GriffinEvaluation.created_at.desc()))
        outcomes = list((await self.db.scalars(select(CurriculumOutcome.id).where(
            CurriculumOutcome.institution_id == submission.institution_id,
            CurriculumOutcome.programme_id == submission.programme_id,
            CurriculumOutcome.semester == submission.academic_semester,
            CurriculumOutcome.is_active.is_(True),
        ))).all()) if submission.institution_id and submission.programme_id and submission.academic_semester else []
        mappings = list((await self.db.scalars(select(InternshipCurriculumMapping).where(
            InternshipCurriculumMapping.report_version_id == version.id,
        ))).all())
        mapping_ready = bool(outcomes) and len({item.outcome_id for item in mappings}) >= len(outcomes) and all(item.status != "REVIEW_REQUIRED" for item in mappings)
        assignments = list((await self.db.scalars(select(BlindAssessmentAssignment).where(
            BlindAssessmentAssignment.report_version_id == version.id,
        ))).all())
        published = await self.db.scalar(select(InternshipAcademicResult.id).where(
            InternshipAcademicResult.report_submission_id == submission.id,
            InternshipAcademicResult.report_version_id == version.id,
            InternshipAcademicResult.status == "PUBLISHED",
        ))
        return {
            "submission_id": submission.id, "version_number": version.version_number,
            "stages": [
                {"key": "submission", "label": "Report and presentation", "status": "COMPLETE" if submission.status != "DRAFT" and version.presentation_file_id else "INCOMPLETE", "detail": "Both files are attached to this version." if version.presentation_file_id else "A presentation file is required."},
                {"key": "griffin", "label": "Griffin evaluation", "status": latest_eval.current_status if latest_eval else "NOT_STARTED", "detail": "Evaluation status only; no result is treated as a final academic grade."},
                {"key": "curriculum", "label": "Curriculum mapping", "status": "COMPLETE" if mapping_ready else "BLOCKED", "detail": "Mapping is based on configured curriculum outcomes." if mapping_ready else "Approved outcomes and reviewed evidence are still required."},
                {"key": "faculty", "label": "Blind faculty assessment", "status": "COMPLETE" if assignments and all(item.status == "SUBMITTED" for item in assignments) else "PENDING", "detail": f"{sum(item.status == 'SUBMITTED' for item in assignments)} of {len(assignments)} assigned assessments submitted."},
                {"key": "result", "label": "Academic result", "status": "PUBLISHED" if published else "AWAITING_APPROVAL", "detail": "Only published results appear in academic history." if published else "Finalization requires all stages and an explicit grading policy."},
            ],
        }
