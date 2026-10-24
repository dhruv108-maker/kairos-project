from pydantic import BaseModel, Field


class CohortAssignment(BaseModel):
    cohort_id: str
    current_semester: int | None = Field(default=None, ge=1, le=20)


class VerificationUpdate(BaseModel):
    is_verified: bool


class FacultyUpdate(BaseModel):
    department_id: str | None = None
    designation: str | None = Field(default=None, min_length=1, max_length=100)
    is_active: bool | None = None


class MentorshipCreate(BaseModel):
    faculty_id: str
    student_id: str
