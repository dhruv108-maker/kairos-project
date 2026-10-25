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
    selection_key: str | None = Field(default=None, max_length=200)


class FacultyAssignmentUpdate(BaseModel):
    status: str = Field(pattern=r"^(started|submitted)$")
