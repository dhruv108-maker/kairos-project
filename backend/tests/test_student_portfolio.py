from datetime import date

import pytest
from pydantic import ValidationError

from app.api.students import AcademicPayload, PortfolioPayload


def test_academic_payload_does_not_calculate_or_require_gpa():
    record = AcademicPayload(
        institution_name="Example Institute",
        qualification="BSc",
        grade_value=8.2,
        grading_scale="10-point CGPA",
    )
    assert record.grade_value == 8.2
    assert record.grade_max is None


def test_academic_grade_bounds_are_validated():
    with pytest.raises(ValidationError):
        AcademicPayload(institution_name="Example", qualification="BSc", grade_value=9, grade_max=8)


def test_portfolio_dates_are_chronological():
    with pytest.raises(ValidationError):
        PortfolioPayload(title="Internship", start_date=date(2025, 5, 1), end_date=date(2025, 4, 1))


def test_student_owned_tables_are_registered():
    from app.models import Base, StudentAcademicRecord, StudentPortfolioEntry, StudentResume

    assert {"student_academic_records", "student_portfolio_entries", "student_resumes"} <= set(Base.metadata.tables)
