from decimal import Decimal
from pydantic import BaseModel, Field, model_validator


class GradeBand(BaseModel):
    minimum_score: Decimal = Field(ge=0, le=100)
    grade: str = Field(min_length=1, max_length=20)


class GradingPolicyCreate(BaseModel):
    institution_id: str = Field(min_length=1, max_length=36)
    rounding_places: int = Field(default=2, ge=0, le=4)
    minimum_evaluators: int = Field(default=1, ge=1, le=5)
    require_curriculum_review: bool = False
    require_griffin: bool = False
    grade_bands: list[GradeBand] = Field(default_factory=list, max_length=20)

    @model_validator(mode="after")
    def validate_bands(self):
        values = [band.minimum_score for band in self.grade_bands]
        if len(values) != len(set(values)):
            raise ValueError("Grade-band thresholds must be unique")
        return self


class ResultPrepare(BaseModel):
    grading_policy_id: str = Field(min_length=1, max_length=36)
