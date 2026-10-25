from datetime import date, datetime
from decimal import Decimal
from sqlalchemy import BigInteger, Boolean, Date, TIMESTAMP, ForeignKey, Integer, JSON, Numeric, String, Text, Enum, UniqueConstraint, Index, func
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.mysql import BIGINT as MYSQL_BIGINT
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
    # Context is snapshotted on new submissions so later cohort changes cannot
    # silently move an assessment into a different semester or curriculum.
    institution_id: Mapped[str | None] = mapped_column(ForeignKey("institutions.id", ondelete="RESTRICT"))
    programme_id: Mapped[str | None] = mapped_column(ForeignKey("programmes.id", ondelete="RESTRICT"))
    cohort_id: Mapped[str | None] = mapped_column(ForeignKey("cohorts.id", ondelete="RESTRICT"))
    academic_year_id: Mapped[str | None] = mapped_column(ForeignKey("academic_years.id", ondelete="RESTRICT"))
    academic_semester: Mapped[int | None] = mapped_column(Integer)
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



class InternshipAssessmentPolicy(Base):
    """Institution-owned, versioned rubric and grading policy for internship assessment."""
    __tablename__ = "internship_assessment_policies"
    __table_args__ = (
        UniqueConstraint("institution_id", "programme_id", "version", name="uq_internship_assessment_policy_version"),
        Index("ix_internship_assessment_policy_active", "institution_id", "programme_id", "is_active"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    institution_id: Mapped[str] = mapped_column(ForeignKey("institutions.id", ondelete="RESTRICT"), nullable=False)
    programme_id: Mapped[str] = mapped_column(ForeignKey("programmes.id", ondelete="RESTRICT"), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    criteria_json: Mapped[list] = mapped_column(JSON, nullable=False)
    component_weights_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    grade_bands_json: Mapped[list] = mapped_column(JSON, nullable=False)
    passing_score: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    final_approver_role: Mapped[str] = mapped_column(String(50), nullable=False)
    required_evaluator_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="1")
    show_curriculum_mapping_to_evaluator: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="0")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="1")
    created_by_account_id: Mapped[str] = mapped_column(ForeignKey("accounts.id", ondelete="RESTRICT"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, nullable=False, server_default=func.now())


class CurriculumOutcome(Base):
    """Actual institution-supplied curriculum outcomes; no default/fabricated outcomes are seeded."""
    __tablename__ = "curriculum_outcomes"
    __table_args__ = (
        UniqueConstraint("programme_id", "semester", "outcome_code", name="uq_curriculum_outcome_code"),
        Index("ix_curriculum_outcome_scope", "institution_id", "programme_id", "semester", "is_active"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    institution_id: Mapped[str] = mapped_column(ForeignKey("institutions.id", ondelete="RESTRICT"), nullable=False)
    programme_id: Mapped[str] = mapped_column(ForeignKey("programmes.id", ondelete="RESTRICT"), nullable=False)
    semester: Mapped[int] = mapped_column(Integer, nullable=False)
    outcome_code: Mapped[str] = mapped_column(String(80), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    expected_competency: Mapped[str] = mapped_column(Text, nullable=False)
    source_reference: Mapped[str] = mapped_column(String(500), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="1")
    created_by_account_id: Mapped[str] = mapped_column(ForeignKey("accounts.id", ondelete="RESTRICT"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, nullable=False, server_default=func.now())


class InternshipCurriculumMapping(Base):
    __tablename__ = "internship_curriculum_mappings"
    __table_args__ = (
        UniqueConstraint("report_version_id", "outcome_id", name="uq_internship_mapping_version_outcome"),
        Index("ix_internship_mapping_version_status", "report_version_id", "status"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    report_version_id: Mapped[str] = mapped_column(ForeignKey("report_versions.id", ondelete="RESTRICT"), nullable=False)
    outcome_id: Mapped[str] = mapped_column(ForeignKey("curriculum_outcomes.id", ondelete="RESTRICT"), nullable=False)
    status: Mapped[str] = mapped_column(Enum("MAPPED", "PARTIALLY_MAPPED", "NOT_EVIDENCED", "REVIEW_REQUIRED", name="internship_curriculum_mapping_status"), nullable=False, server_default="REVIEW_REQUIRED")
    evidence_reference: Mapped[str | None] = mapped_column(Text)
    confidence: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    reviewer_notes: Mapped[str | None] = mapped_column(Text)
    change_history_json: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    created_by_account_id: Mapped[str] = mapped_column(ForeignKey("accounts.id", ondelete="RESTRICT"), nullable=False)
    reviewed_by_account_id: Mapped[str | None] = mapped_column(ForeignKey("accounts.id", ondelete="SET NULL"))
    reviewed_at: Mapped[datetime | None] = mapped_column(TIMESTAMP)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP, nullable=False, server_default=func.now(), onupdate=func.now())


class BlindAssessmentAssignment(Base):
    """Per-submission independent assessor assignment, with an immutable rubric snapshot."""
    __tablename__ = "blind_assessment_assignments"
    __table_args__ = (
        UniqueConstraint("report_version_id", "evaluator_faculty_id", name="uq_blind_assignment_version_evaluator"),
        Index("ix_blind_assignment_evaluator_status", "evaluator_faculty_id", "status"),
        Index("ix_blind_assignment_version_status", "report_version_id", "status"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    packet_code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    report_version_id: Mapped[str] = mapped_column(ForeignKey("report_versions.id", ondelete="RESTRICT"), nullable=False)
    institution_id: Mapped[str] = mapped_column(ForeignKey("institutions.id", ondelete="RESTRICT"), nullable=False)
    evaluator_faculty_id: Mapped[int] = mapped_column(
        MYSQL_BIGINT(unsigned=True).with_variant(BigInteger, "sqlite"),
        ForeignKey("faculty.id", ondelete="RESTRICT"), nullable=False
    )
    policy_id: Mapped[str] = mapped_column(ForeignKey("internship_assessment_policies.id", ondelete="RESTRICT"), nullable=False)
    assigned_by_account_id: Mapped[str] = mapped_column(ForeignKey("accounts.id", ondelete="RESTRICT"), nullable=False)
    rubric_snapshot_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    scores_json: Mapped[dict | None] = mapped_column(JSON)
    total_score: Mapped[Decimal | None] = mapped_column(Numeric(7, 2))
    evaluator_comments: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Enum("ASSIGNED", "DRAFT", "SUBMITTED", name="blind_assessment_status"), nullable=False, server_default="ASSIGNED")
    assigned_at: Mapped[datetime] = mapped_column(TIMESTAMP, nullable=False, server_default=func.now())
    submitted_at: Mapped[datetime | None] = mapped_column(TIMESTAMP)


class InternshipAcademicResult(Base):
    """Immutable finalized/published result revisions; never writes into student CGPA."""
    __tablename__ = "internship_academic_results"
    __table_args__ = (
        UniqueConstraint("report_submission_id", "revision_number", name="uq_internship_result_revision"),
        Index("ix_internship_result_student_status", "student_profile_id", "status"),
        Index("ix_internship_result_semester", "institution_id", "academic_year_id", "academic_semester"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    report_submission_id: Mapped[str] = mapped_column(ForeignKey("report_submissions.id", ondelete="RESTRICT"), nullable=False)
    report_version_id: Mapped[str] = mapped_column(ForeignKey("report_versions.id", ondelete="RESTRICT"), nullable=False)
    student_profile_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("student_profiles.id", ondelete="RESTRICT"), nullable=False)
    institution_id: Mapped[str] = mapped_column(ForeignKey("institutions.id", ondelete="RESTRICT"), nullable=False)
    programme_id: Mapped[str] = mapped_column(ForeignKey("programmes.id", ondelete="RESTRICT"), nullable=False)
    cohort_id: Mapped[str | None] = mapped_column(ForeignKey("cohorts.id", ondelete="RESTRICT"))
    academic_year_id: Mapped[str | None] = mapped_column(ForeignKey("academic_years.id", ondelete="RESTRICT"))
    academic_semester: Mapped[int] = mapped_column(Integer, nullable=False)
    revision_number: Mapped[int] = mapped_column(Integer, nullable=False)
    previous_result_id: Mapped[str | None] = mapped_column(ForeignKey("internship_academic_results.id", ondelete="RESTRICT"))
    policy_id: Mapped[str] = mapped_column(ForeignKey("internship_assessment_policies.id", ondelete="RESTRICT"), nullable=False)
    component_breakdown_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    total_score: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    grade: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(Enum("FINALIZED", "PUBLISHED", "SUPERSEDED", name="internship_academic_result_status"), nullable=False, server_default="FINALIZED")
    correction_reason: Mapped[str | None] = mapped_column(Text)
    finalized_by_account_id: Mapped[str] = mapped_column(ForeignKey("accounts.id", ondelete="RESTRICT"), nullable=False)
    finalized_at: Mapped[datetime] = mapped_column(TIMESTAMP, nullable=False, server_default=func.now())
    published_by_account_id: Mapped[str | None] = mapped_column(ForeignKey("accounts.id", ondelete="SET NULL"))
    published_at: Mapped[datetime | None] = mapped_column(TIMESTAMP)
