from datetime import date
from pydantic import BaseModel, Field


class ReportCreate(BaseModel):
    placement_id: str
    title: str = Field(min_length=2, max_length=255)
    file_id: str
    submission_notes: str | None = Field(default=None, max_length=5000)
    requirement_id: str | None = None


class ReportVersionCreate(BaseModel):
    file_id: str
    submission_notes: str | None = Field(default=None, max_length=5000)


class ReportTitleUpdate(BaseModel):
    title: str = Field(min_length=2, max_length=255)


class ReportReviewUpdate(BaseModel):
    status: str = Field(pattern=r"^(UNDER_EVALUATION|REVISION_REQUIRED|APPROVED|REJECTED)$")
    feedback_comments: str | None = Field(default=None, max_length=5000)


class ReportRequirementCreate(BaseModel):
    title: str = Field(min_length=2, max_length=255)
    description: str | None = Field(default=None, max_length=5000)
    due_date: date | None = None
    is_required: bool = True


class ReportRequirementActiveUpdate(BaseModel):
    is_active: bool
