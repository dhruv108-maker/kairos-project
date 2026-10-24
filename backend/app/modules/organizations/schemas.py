from datetime import date
from pydantic import BaseModel, Field


class TeamCreate(BaseModel):
    department_id: str
    name: str = Field(min_length=2, max_length=150)


class TeamMemberUpsert(BaseModel):
    account_id: str
    role_in_team: str = Field(default="MEMBER", pattern=r"^(LEAD|MEMBER)$")


class CampaignCreate(BaseModel):
    title: str = Field(min_length=2, max_length=255)
    description: str | None = Field(default=None, max_length=5000)
    start_date: date
    end_date: date


class CampaignStatusUpdate(BaseModel):
    is_active: bool


class FacultyAssignmentCreate(BaseModel):
    faculty_account_id: str
    reason: str = Field(default="MANUAL", min_length=1, max_length=100)


class FacultyAssignmentUpdate(BaseModel):
    status: str = Field(pattern=r"^(IN_PROGRESS|SUBMITTED|EXPIRED)$")
    score: float | None = Field(default=None, ge=0, le=100)
    feedback_comments: str | None = Field(default=None, max_length=5000)
