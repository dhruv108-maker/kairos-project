from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator


class CriterionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    key: str = Field(pattern=r"^[a-z0-9][a-z0-9_-]{0,49}$")
    label: str = Field(min_length=2, max_length=120)
    description: str = Field(min_length=2, max_length=2000)
    max_score: float = Field(gt=0, le=100)
    require_comment: bool = False


class GradeBand(BaseModel):
    model_config = ConfigDict(extra="forbid")
    grade: str = Field(min_length=1, max_length=20)
    min_score: float = Field(ge=0, le=100)
    max_score: float = Field(ge=0, le=100)

    @model_validator(mode="after")
    def validate_range(self):
        if self.min_score > self.max_score:
            raise ValueError("min_score must be less than or equal to max_score")
        return self


class PolicyCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    institution_id: str = Field(min_length=1, max_length=36)
    programme_id: str = Field(min_length=1, max_length=36)
    name: str = Field(min_length=2, max_length=255)
    criteria: list[CriterionCreate] = Field(min_length=1, max_length=30)
    component_weights: dict[str, float]
    # These values explicitly define how raw Griffin scores and mapping statuses are normalized.
    griffin_score_max: float = Field(gt=0, le=100000)
    curriculum_status_scores: dict[str, float]
    grade_bands: list[GradeBand] = Field(min_length=1, max_length=20)
    passing_score: float = Field(ge=0, le=100)
    final_approver_role: Literal["INSTITUTION_ADMIN", "DEAN", "DEPT_HEAD"]
    required_evaluator_count: int = Field(default=1, ge=1, le=5)
    show_curriculum_mapping_to_evaluator: bool = False

    @model_validator(mode="after")
    def validate_policy(self):
        expected = {"griffin", "curriculum", "faculty"}
        if set(self.component_weights) != expected:
            raise ValueError("component_weights must explicitly define griffin, curriculum, and faculty")
        if any(value <= 0 or value > 100 for value in self.component_weights.values()):
            raise ValueError("each component weight must be greater than 0 and no more than 100")
        if abs(sum(self.component_weights.values()) - 100.0) > 0.01:
            raise ValueError("component weights must sum to 100")
        keys = [item.key for item in self.criteria]
        if len(keys) != len(set(keys)):
            raise ValueError("rubric criterion keys must be unique")
        expected_mapping_statuses = {"MAPPED", "PARTIALLY_MAPPED", "NOT_EVIDENCED"}
        if set(self.curriculum_status_scores) != expected_mapping_statuses:
            raise ValueError("curriculum_status_scores must explicitly define MAPPED, PARTIALLY_MAPPED, and NOT_EVIDENCED")
        if any(value < 0 or value > 100 for value in self.curriculum_status_scores.values()):
            raise ValueError("curriculum status scores must be between 0 and 100")
        if not (
            self.curriculum_status_scores["MAPPED"] >= self.curriculum_status_scores["PARTIALLY_MAPPED"]
            >= self.curriculum_status_scores["NOT_EVIDENCED"]
        ):
            raise ValueError("curriculum status scores must be ordered from MAPPED to PARTIALLY_MAPPED to NOT_EVIDENCED")
        bands = sorted(self.grade_bands, key=lambda item: item.min_score)
        if bands[0].min_score != 0 or bands[-1].max_score != 100:
            raise ValueError("grade bands must explicitly cover scores from 0 to 100")
        for previous, current in zip(bands, bands[1:]):
            if current.min_score <= previous.max_score:
                raise ValueError("grade bands must not overlap")
            if current.min_score - previous.max_score > 0.02:
                raise ValueError("grade bands must not leave score gaps")
        return self


class CurriculumOutcomeCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    institution_id: str = Field(min_length=1, max_length=36)
    programme_id: str = Field(min_length=1, max_length=36)
    semester: int = Field(ge=1, le=12)
    outcome_code: str = Field(min_length=1, max_length=80)
    title: str = Field(min_length=2, max_length=255)
    expected_competency: str = Field(min_length=2, max_length=5000)
    source_reference: str = Field(min_length=2, max_length=500)


class CurriculumMappingItem(BaseModel):
    model_config = ConfigDict(extra="forbid")
    outcome_id: str = Field(min_length=1, max_length=36)
    status: Literal["MAPPED", "PARTIALLY_MAPPED", "NOT_EVIDENCED", "REVIEW_REQUIRED"]
    evidence_reference: str | None = Field(default=None, max_length=5000)
    confidence: float | None = Field(default=None, ge=0, le=100)
    reviewer_notes: str | None = Field(default=None, max_length=5000)

    @model_validator(mode="after")
    def require_evidence_for_mapping(self):
        if self.status in {"MAPPED", "PARTIALLY_MAPPED"} and not (self.evidence_reference or "").strip():
            raise ValueError("evidence_reference is required for mapped or partially mapped outcomes")
        return self


class CurriculumMappingBatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    items: list[CurriculumMappingItem] = Field(min_length=1, max_length=200)

    @model_validator(mode="after")
    def unique_outcomes(self):
        ids = [item.outcome_id for item in self.items]
        if len(ids) != len(set(ids)):
            raise ValueError("Each outcome may appear only once in a mapping update")
        return self


class AssessmentAssignmentCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    report_version_id: str = Field(min_length=1, max_length=36)
    evaluator_faculty_id: int = Field(gt=0)
    policy_id: str = Field(min_length=1, max_length=36)


class CriterionScore(BaseModel):
    model_config = ConfigDict(extra="forbid")
    score: float = Field(ge=0, le=100)
    comment: str | None = Field(default=None, max_length=5000)


class ScoresUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    scores: dict[str, CriterionScore]
    evaluator_comments: str | None = Field(default=None, max_length=10000)
