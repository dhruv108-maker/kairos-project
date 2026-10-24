"""Kairos-side evaluation job tracking, idempotency, and attempt history."""
from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.academic import FacultyProfile
from app.models.evaluation import GriffinEvaluation, GriffinEvaluationAttempt, ReportSubmission, ReportVersion
from app.models.internship import InternshipPlacement
from app.modules.evaluations.adapter import GriffinAdapter, GriffinIntegrationUnavailable


class EvaluationWorkflowError(Exception):
    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        self.message = message
        super().__init__(message)


class EvaluationService:
    def __init__(self, db: AsyncSession, adapter: GriffinAdapter | None = None):
        self.db = db
        self.adapter = adapter or GriffinAdapter()

    async def _authorized_version(self, version_id: str, account_id: str) -> tuple[ReportVersion, ReportSubmission]:
        version = await self.db.get(ReportVersion, version_id)
        if version is None:
            raise EvaluationWorkflowError(404, "Report version not found")
        submission = await self.db.get(ReportSubmission, version.submission_id)
        if submission is None:
            raise EvaluationWorkflowError(404, "Report submission not found")
        placement = await self.db.get(InternshipPlacement, submission.placement_id)
        faculty_result = await self.db.execute(select(FacultyProfile).where(FacultyProfile.account_id == account_id))
        faculty = faculty_result.scalar_one_or_none()
        if faculty is None:
            raise EvaluationWorkflowError(403, "Faculty account required")
        if placement is None or placement.faculty_supervisor_id != faculty.id:
            raise EvaluationWorkflowError(403, "Only the assigned faculty supervisor may request evaluation")
        if submission.status not in {"SUBMITTED", "UNDER_EVALUATION"}:
            raise EvaluationWorkflowError(409, "Only submitted reports can be evaluated")
        return version, submission

    async def request_evaluation(self, version_id: str, account_id: str, project_id: str, report_id: str) -> GriffinEvaluation:
        version, _ = await self._authorized_version(version_id, account_id)
        existing_result = await self.db.execute(select(GriffinEvaluation).where(
            GriffinEvaluation.report_version_id == version.id
        ).order_by(GriffinEvaluation.created_at.desc()))
        existing = existing_result.scalars().first()
        if existing is not None:
            return existing

        evaluation = GriffinEvaluation(
            id=str(uuid4()), report_version_id=version.id, griffin_project_id=project_id.strip(),
            griffin_report_id=report_id.strip(), current_status="QUEUED",
        )
        attempt = GriffinEvaluationAttempt(
            id=str(uuid4()), griffin_evaluation_id=evaluation.id, attempt_number=1,
            request_payload={"project_id": project_id.strip(), "report_id": report_id.strip()},
            execution_status="QUEUED",
        )
        self.db.add_all([evaluation, attempt])
        await self.db.commit()
        await self.db.refresh(evaluation)

        # Network dispatch deliberately occurs after the database transaction.
        try:
            response = await self.adapter.dispatch(
                project_id=project_id.strip(), report_id=report_id.strip(),
                evaluation_id=evaluation.id, attempt_id=attempt.id,
            )
        except GriffinIntegrationUnavailable as exc:
            evaluation.current_status = "FAILED"
            attempt.execution_status = "FAILED"
            attempt.error_message = str(exc)
            attempt.completed_at = datetime.now(UTC).replace(tzinfo=None)
            await self.db.commit()
            raise EvaluationWorkflowError(503, str(exc)) from None
        except Exception:
            evaluation.current_status = "FAILED"
            attempt.execution_status = "FAILED"
            attempt.error_message = "Griffin dispatch failed; inspect integration logs."
            attempt.completed_at = datetime.now(UTC).replace(tzinfo=None)
            await self.db.commit()
            raise EvaluationWorkflowError(502, "Griffin dispatch failed") from None

        # A real adapter must return a validated job identifier. No response is accepted
        # as success unless the verified contract supplies that field.
        job_id = response.get("job_id") if isinstance(response, dict) else None
        if not isinstance(job_id, str) or not job_id.strip():
            evaluation.current_status = "FAILED"
            attempt.execution_status = "FAILED"
            attempt.error_message = "Griffin response did not contain a valid job_id."
            attempt.response_payload = response if isinstance(response, (dict, list)) else None
            attempt.completed_at = datetime.now(UTC).replace(tzinfo=None)
            await self.db.commit()
            raise EvaluationWorkflowError(502, "Griffin returned an invalid dispatch response")
        evaluation.griffin_job_id = job_id.strip()
        evaluation.current_status = "PROCESSING"
        attempt.execution_status = "DISPATCHED"
        attempt.response_payload = response
        attempt.completed_at = datetime.now(UTC).replace(tzinfo=None)
        await self.db.commit()
        await self.db.refresh(evaluation)
        return evaluation

    async def get_for_faculty(self, evaluation_id: str, account_id: str) -> GriffinEvaluation:
        evaluation = await self.db.get(GriffinEvaluation, evaluation_id)
        if evaluation is None:
            raise EvaluationWorkflowError(404, "Evaluation not found")
        await self._authorized_version(evaluation.report_version_id, account_id)
        return evaluation

    async def attempts_for_faculty(self, evaluation_id: str, account_id: str) -> list[GriffinEvaluationAttempt]:
        await self.get_for_faculty(evaluation_id, account_id)
        result = await self.db.execute(select(GriffinEvaluationAttempt).where(
            GriffinEvaluationAttempt.griffin_evaluation_id == evaluation_id
        ).order_by(GriffinEvaluationAttempt.attempt_number))
        return list(result.scalars().all())
