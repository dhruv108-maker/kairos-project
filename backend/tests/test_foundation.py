from pydantic import ValidationError
import pytest

from app.main import health_check
from app.models import Base
from app.models.storage import StorageFileCreate


@pytest.mark.asyncio
async def test_health_check():
    assert await health_check() == {"status": "ok", "service": "Kairos API"}


def test_model_metadata_contains_spec_tables():
    expected = {
        "schools", "departments", "programmes", "academic_years", "cohorts",
        "accounts", "roles", "account_roles", "student_profiles", "faculty",
        "storage_files", "internship_providers", "internship_opportunities",
        "internship_applications", "internship_placements", "recruitment_drives", "recruitment_drive_programme_targets",
        "recruitment_drive_cohort_targets", "recruitment_drive_graduation_year_targets", "recruitment_drive_participations",
        "recruitment_drive_opportunities", "report_submissions",
        "report_versions", "griffin_evaluations", "griffin_evaluation_attempts",
        "griffin_result_snapshots", "evaluation_workflows", "evaluation_stage_results",
        "final_evaluation_outcomes", "teams", "team_memberships", "assessment_campaigns",
        "assessment_assignments",
    }
    assert expected <= set(Base.metadata.tables)


def test_sha256_accepts_64_hex_chars():
    model = StorageFileCreate(
        original_name="report.pdf", file_path="reports/1/1/1/report.pdf",
        file_size_bytes=1, mime_type="application/pdf", sha256_hash="a" * 64,
        uploaded_by_account_id="account-id",
    )
    assert len(model.sha256_hash) == 64


def test_sha256_rejects_wrong_length():
    with pytest.raises(ValidationError):
        StorageFileCreate(
            original_name="report.pdf", file_path="reports/1/1/1/report.pdf",
            file_size_bytes=1, mime_type="application/pdf", sha256_hash="abc",
            uploaded_by_account_id="account-id",
        )
