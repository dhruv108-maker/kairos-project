from app.api.internships import APPLICATION_TRANSITIONS, ApplicationStatusUpdate
from pydantic import ValidationError
import pytest


def test_application_state_machine_matches_schema_statuses():
    assert APPLICATION_TRANSITIONS["APPLIED"] == {"SHORTLISTED", "REJECTED", "WITHDRAWN"}
    assert APPLICATION_TRANSITIONS["SHORTLISTED"] == {"OFFERED", "REJECTED", "WITHDRAWN"}
    assert APPLICATION_TRANSITIONS["OFFERED"] == {"REJECTED"}
    assert APPLICATION_TRANSITIONS["WITHDRAWN"] == set()


def test_status_update_normalizes_case():
    assert ApplicationStatusUpdate(status=" shortlisted ").status == "SHORTLISTED"


def test_status_update_rejects_status_not_in_database_enum():
    # The supplied schema has no ACCEPTED application status, so the API must not invent one.
    with pytest.raises(ValidationError):
        ApplicationStatusUpdate(status="ACCEPTED")
