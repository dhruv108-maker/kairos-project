from datetime import date, datetime
from decimal import Decimal
from sqlalchemy import BigInteger, Boolean, Date, TIMESTAMP, ForeignKey, Integer, JSON, Numeric, String, Text, Enum, UniqueConstraint, Index, func
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base


class ReportRequirement(Base):
    __tablename__ = "report_requirements"
    __table_args__ = (UniqueConstraint("institution_id", "title", name="uq_institution_report_requirement_title"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    institution_id: Mapped[str] = mapped_column(ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    due_date: Mapped[date | None] = mapped_column(Date)
    is_required: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="1")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="1")
    created_by_account_id: Mapped[str] = mapped_column(ForeignKey("accounts.id", ondelete="RESTRICT"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP, nullable=False, server_default=func.now(), onupdate=func.now())


class ReportSubmission(Base):
    __tablename__ = "report_submissions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    placement_id: Mapped[str] = mapped_column(ForeignKey("internship_placements.id", ondelete="RESTRICT"), nullable=False)
    requirement_id: Mapped[str | None] = mapped_column(ForeignKey("report_requirements.id", ondelete="SET NULL"))
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    latest_version_number: Mapped[int] = mapped_column(Integer, nullable=False, server_default="1")
    status: Mapped[str] = mapped_column(Enum("DRAFT", "SUBMITTED", "UNDER_EVALUATION", "REVISION_REQUIRED", "APPROVED", "REJECTED", name="report_submission_status"), nullable=False, server_default="DRAFT")
    review_feedback: Mapped[str | None] = mapped_column(Text)
    reviewed_by_account_id: Mapped[str | None] = mapped_column(ForeignKey("accounts.id", ondelete="SET NULL"))
    reviewed_at: Mapped[datetime | None] = mapped_column(TIMESTAMP)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP, nullable=False, server_default=func.now(), onupdate=func.now())


class ReportVersion(Base):
    __tablename__ = "report_versions"
    __table_args__ = (UniqueConstraint("submission_id", "version_number", name="uq_submission_version"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    submission_id: Mapped[str] = mapped_column(ForeignKey("report_submissions.id", ondelete="CASCADE"), nullable=False)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    file_id: Mapped[str] = mapped_column(ForeignKey("storage_files.id", ondelete="RESTRICT"), nullable=False)
    presentation_file_id: Mapped[str | None] = mapped_column(ForeignKey("storage_files.id", ondelete="RESTRICT"))
    submission_notes: Mapped[str | None] = mapped_column(Text)
    submitted_at: Mapped[datetime] = mapped_column(TIMESTAMP, nullable=False, server_default=func.now())


class GriffinEvaluation(Base):
    __tablename__ = "griffin_evaluations"
    __table_args__ = (Index("idx_ge_version", "report_version_id"), Index("idx_ge_job", "griffin_job_id"))
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    report_version_id: Mapped[str] = mapped_column(ForeignKey("report_versions.id", ondelete="CASCADE"), nullable=False)
    griffin_project_id: Mapped[str] = mapped_column(String(128), nullable=False)
    griffin_report_id: Mapped[str] = mapped_column(String(128), nullable=False)
    griffin_job_id: Mapped[str | None] = mapped_column(String(128))
    current_status: Mapped[str] = mapped_column(Enum("QUEUED", "PROCESSING", "COMPLETED", "FAILED", "RETRIED", name="griffin_status"), nullable=False, server_default="QUEUED")
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP, nullable=False, server_default=func.now(), onupdate=func.now())


class GriffinEvaluationAttempt(Base):
    __tablename__ = "griffin_evaluation_attempts"
    __table_args__ = (UniqueConstraint("griffin_evaluation_id", "attempt_number", name="uq_eval_attempt"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    griffin_evaluation_id: Mapped[str] = mapped_column(ForeignKey("griffin_evaluations.id", ondelete="CASCADE"), nullable=False)
    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False, server_default="1")
    request_payload: Mapped[dict | list | None] = mapped_column(JSON)
    response_payload: Mapped[dict | list | None] = mapped_column(JSON)
    error_message: Mapped[str | None] = mapped_column(Text)
    execution_status: Mapped[str] = mapped_column(String(50), nullable=False)
    started_at: Mapped[datetime] = mapped_column(TIMESTAMP, nullable=False, server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(TIMESTAMP)


class GriffinResultSnapshot(Base):
    __tablename__ = "griffin_result_snapshots"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    griffin_evaluation_id: Mapped[str] = mapped_column(ForeignKey("griffin_evaluations.id", ondelete="CASCADE"), unique=True, nullable=False)
    alignment_score: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    topic_match_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    extracted_evidence_summary: Mapped[dict | list] = mapped_column(JSON, nullable=False)
    raw_griffin_result: Mapped[dict | list] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, nullable=False, server_default=func.now())


class EvaluationWorkflow(Base):
    __tablename__ = "evaluation_workflows"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    report_submission_id: Mapped[str] = mapped_column(ForeignKey("report_submissions.id", ondelete="CASCADE"), nullable=False)
    current_stage_number: Mapped[int] = mapped_column(Integer, nullable=False, server_default="1")
    total_stages: Mapped[int] = mapped_column(Integer, nullable=False, server_default="2")
    is_completed: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="0")
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP, nullable=False, server_default=func.now(), onupdate=func.now())


class EvaluationStageResult(Base):
    __tablename__ = "evaluation_stage_results"
    __table_args__ = (UniqueConstraint("workflow_id", "stage_number", name="uq_workflow_stage"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    workflow_id: Mapped[str] = mapped_column(ForeignKey("evaluation_workflows.id", ondelete="CASCADE"), nullable=False)
    stage_number: Mapped[int] = mapped_column(Integer, nullable=False)
    stage_name: Mapped[str] = mapped_column(String(100), nullable=False)
    evaluator_account_id: Mapped[str | None] = mapped_column(ForeignKey("accounts.id", ondelete="SET NULL"))
    stage_status: Mapped[str] = mapped_column(Enum("PENDING", "PASSED", "REJECTED", "NEEDS_REVISION", name="evaluation_stage_status"), nullable=False, server_default="PENDING")
    score: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    feedback_comments: Mapped[str | None] = mapped_column(Text)
    evaluated_at: Mapped[datetime | None] = mapped_column(TIMESTAMP)


class FinalEvaluationOutcome(Base):
    __tablename__ = "final_evaluation_outcomes"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    report_submission_id: Mapped[str] = mapped_column(ForeignKey("report_submissions.id", ondelete="RESTRICT"), unique=True, nullable=False)
    final_grade: Mapped[str] = mapped_column(String(10), nullable=False)
    total_score: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    is_approved: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="1")
    signed_off_by_faculty_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("faculty.id", ondelete="RESTRICT"), nullable=False)
    signed_off_at: Mapped[datetime] = mapped_column(TIMESTAMP, nullable=False, server_default=func.now())
