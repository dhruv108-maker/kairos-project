from pydantic import BaseModel, Field
from typing import Literal


class LearningOutcomeCreate(BaseModel):
    programme_id: str | None = None
    code: str = Field(min_length=1, max_length=80)
    title: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=4000)


class MappingItemInput(BaseModel):
    learning_outcome_id: str = Field(min_length=1, max_length=36)
    evidence_type: Literal["REPORT", "PRESENTATION"]


class CurriculumMappingCreate(BaseModel):
    items: list[MappingItemInput] = Field(min_length=1, max_length=50)


class MappingReviewItem(BaseModel):
    learning_outcome_id: str = Field(min_length=1, max_length=36)
    evidence_status: Literal["PARTIAL", "EVIDENCED", "MISSING"]
    reviewer_notes: str | None = Field(default=None, max_length=4000)


class CurriculumMappingReview(BaseModel):
    reviewer_notes: str | None = Field(default=None, max_length=4000)
    items: list[MappingReviewItem] = Field(min_length=1, max_length=50)
