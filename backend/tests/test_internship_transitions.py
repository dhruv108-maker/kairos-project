from app.api.internships import APPLICATION_TRANSITIONS, ApplicationStatusUpdate
from pydantic import ValidationError
import pytest


def test_application_state_machine_matches_schema_statuses():
    assert APPLICATION_TRANSITIONS["SUBMITTED"] == {"UNDER_REVIEW", "SHORTLISTED", "REJECTED", "WITHDRAWN"}
    assert APPLICATION_TRANSITIONS["SHORTLISTED"] == {"ACCEPTED", "REJECTED", "WITHDRAWN"}
    assert APPLICATION_TRANSITIONS["ACCEPTED"] == set()
    assert APPLICATION_TRANSITIONS["WITHDRAWN"] == set()


def test_status_update_normalizes_case():
    assert ApplicationStatusUpdate(status=" shortlisted ").status == "SHORTLISTED"


def test_status_update_rejects_status_not_in_database_enum():
    # APPLIED is not part of the deployed database constraint.
    with pytest.raises(ValidationError):
        ApplicationStatusUpdate(status="APPLIED")
