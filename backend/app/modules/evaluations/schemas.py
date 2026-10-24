from pydantic import BaseModel, Field


class EvaluationRequest(BaseModel):
    griffin_project_id: str = Field(min_length=1, max_length=128)
    griffin_report_id: str = Field(min_length=1, max_length=128)
