from decimal import Decimal
from pydantic import BaseModel, Field, model_validator


class RubricCriterionInput(BaseModel):
    code: str = Field(min_length=1, max_length=80)
    title: str = Field(min_length=1, max_length=255)
    description: str = Field(min_length=1, max_length=4000)
    minimum_score: Decimal = Field(ge=0, le=10000)
    maximum_score: Decimal = Field(gt=0, le=10000)
    weight: Decimal = Field(gt=0, le=1000)
    position: int = Field(default=0, ge=0, le=1000)

    @model_validator(mode="after")
    def score_range(self):
        if self.maximum_score <= self.minimum_score:
            raise ValueError("maximum_score must be greater than minimum_score")
        return self


class RubricCreate(BaseModel):
    institution_id: str = Field(min_length=1, max_length=36)
    name: str = Field(min_length=1, max_length=255)
    criteria: list[RubricCriterionInput] = Field(min_length=1, max_length=50)


class BlindAssignmentCreate(BaseModel):
    report_version_id: str = Field(min_length=1, max_length=36)
    rubric_id: str = Field(min_length=1, max_length=36)
    evaluator_account_id: str = Field(min_length=1, max_length=36)


class BlindScoreInput(BaseModel):
    criterion_id: str = Field(min_length=1, max_length=36)
    score: Decimal = Field(ge=0, le=10000)
    feedback: str | None = Field(default=None, max_length=4000)


class BlindScoreSave(BaseModel):
    scores: list[BlindScoreInput] = Field(min_length=1, max_length=50)
    submit: bool = False
